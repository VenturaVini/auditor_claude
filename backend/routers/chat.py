"""POST /api/chat — streaming SSE com failover entre provedores.

Fluxo normal: Claude responde (streaming) → GPT audita.
Failover 1: Anthropic falha → evento "failover" + GPT assume a resposta → Claude audita (se possível).
Failover 2: OpenAI falha na auditoria → Claude audita a própria categoria de resposta.

MODO DE RODADAS (debate): `rounds` = 2 (padrão), 4, 6, 8 ou 10.
  2x: Claude responde → GPT julga (final). 4x+: a crítica do GPT volta ao Claude,
  que a julga e refina a resposta; o GPT julga de novo; sempre termina no GPT.
  Parada antecipada: se o GPT der OK numa rodada intermediária, o debate encerra.

Protocolo SSE enviado ao frontend:
  data: {"type": "meta", "conversation_id": ...}  -> id da conversa (criada se necessário)
  data: {"type": "chunk", "text": "..."}          -> pedaço da resposta
  data: {"type": "debate", "round": k, "total": N, "audit": {...}} -> crítica intermediária do GPT
  data: {"type": "revision_start", "round": k, "total": N} -> Claude vai re-streamar a resposta refinada
  data: {"type": "model_info", ...}               -> métricas somadas de todas as rodadas Claude
  data: {"type": "failover", "provider": "anthropic"|"openai", "message": ..., "took_over": ...}
  data: {"type": "error", "message": ...}         -> erro fatal (ambas APIs falharam)
  data: [AUDIT]{json}                              -> veredito final (round/total/early_stop)
  data: [DONE]                                     -> fim do stream
"""

import asyncio
import json
import re
import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services import storage
from services import claude as claude_svc
from services import gpt as gpt_svc
from services import executor
from services.file_processor import load_file_meta
from services.pricing import estimate_cost_usd

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    files: list[str] = []
    conversation_id: str | None = None
    main_model: str | None = None      # modelo Claude da resposta principal
    auditor_model: str | None = None   # modelo GPT do auditor
    rounds: int = 2                    # rodadas do debate: 2/4/6/8/10
    booster: bool = False              # opinião final dos MELHORES modelos


def _clamp_rounds(n: int) -> int:
    n = max(2, min(10, n))
    return n if n % 2 == 0 else n + 1  # sempre par (termina no GPT)


# Preferência do booster (custo/benefício p/ veredito curto; fable custa 2x o opus)
_BOOSTER_CLAUDE_PREF = ["claude-opus-4-8", "claude-fable-5"]


async def _pick_booster_models() -> tuple[str, str]:
    """Escolhe o melhor modelo disponível de cada provedor para o booster."""
    try:
        claude_models = await claude_svc.list_anthropic_models()
    except Exception:
        claude_models = claude_svc.AVAILABLE_MODELS
    try:
        gpt_models = await gpt_svc.list_openai_models()
    except Exception:
        gpt_models = gpt_svc.AVAILABLE_MODELS

    best_claude = next(
        (m for pref in _BOOSTER_CLAUDE_PREF for m in claude_models if m.startswith(pref)),
        claude_svc.DEFAULT_MODEL,
    )
    # melhor gpt-5.x "puro" (sem pro/codex — podem ser lentos/incompatíveis c/ chat)
    gpt5 = sorted(
        m for m in gpt_models
        if re.fullmatch(r"gpt-5(\.\d+)?", m)
    )
    best_gpt = gpt5[-1] if gpt5 else ("gpt-4o" if "gpt-4o" in gpt_models else gpt_svc.DEFAULT_MODEL)
    return best_claude, best_gpt


@router.get("/api/models")
async def list_models():
    """Lista dinâmica: consulta as APIs dos provedores (o que a chave realmente
    tem acesso); se a consulta falhar, usa a lista fixa de fallback."""
    try:
        main = await claude_svc.list_anthropic_models()
    except Exception:
        main = claude_svc.AVAILABLE_MODELS
    try:
        auditor = await gpt_svc.list_openai_models()
    except Exception:
        auditor = gpt_svc.AVAILABLE_MODELS
    return {
        "main": main,
        "auditor": auditor,
        "default_main": claude_svc.DEFAULT_MODEL,
        "default_auditor": gpt_svc.DEFAULT_MODEL,
    }


# Poda do histórico ENVIADO à API (o Redis guarda a conversa completa).
# Evita custo crescente e estouro da janela de contexto em conversas longas.
MAX_HISTORY_MESSAGES = 40

# Contexto de conversa repassado ao auditor/booster (turnos recentes, truncados)
AUDIT_HISTORY_TURNS = 6
AUDIT_HISTORY_CHARS = 800


def _history_for_audit(req: ChatRequest) -> str:
    """Resumo dos turnos anteriores p/ o auditor não julgar às cegas em multi-turno."""
    prev = req.messages[:-1]
    if not prev:
        return ""
    lines = []
    for m in prev[-AUDIT_HISTORY_TURNS:]:
        who = "Usuário" if m.role == "user" else "Assistente"
        text = m.content
        if len(text) > AUDIT_HISTORY_CHARS:
            text = text[:AUDIT_HISTORY_CHARS] + " [...]"
        lines.append(f"[{who}]: {text}")
    return "\n".join(lines)


def _build_anthropic_messages(req: ChatRequest) -> tuple[list[dict], str, str]:
    """Monta as mensagens para a Messages API, injetando arquivos na última mensagem.

    Retorna (messages, pergunta_curta_p_titulo, pergunta_com_contexto_p_auditor).
    O auditor recebe a versão com o conteúdo dos documentos E os turnos recentes
    da conversa, para poder verificar fatos sem julgar às cegas.
    """
    prev = req.messages[:-1]
    if len(prev) > MAX_HISTORY_MESSAGES:
        prev = prev[-MAX_HISTORY_MESSAGES:]
        # a Messages API exige que a primeira mensagem seja do usuário
        while prev and prev[0].role != "user":
            prev = prev[1:]
    messages: list[dict] = [{"role": m.role, "content": m.content} for m in prev]
    last = req.messages[-1]

    blocks: list[dict] = []
    doc_context = ""

    for file_id in req.files:
        meta = load_file_meta(file_id)
        if meta is None:
            doc_context += f"\n\n[Arquivo {file_id} expirou ou não foi encontrado]"
            continue
        if meta["kind"] == "image":
            blocks.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": meta["media_type"],
                    "data": meta["base64"],
                },
            })
        elif meta["kind"] == "document":
            doc_context += f"\n\n--- Conteúdo do arquivo: {meta['name']} ---\n{meta['text']}"

    text = last.content
    if doc_context:
        text = f"{doc_context.strip()}\n\n{text}"
    blocks.append({"type": "text", "text": text})

    messages.append({"role": last.role, "content": blocks})

    # Pergunta enriquecida p/ auditor e booster: turnos recentes + docs + pergunta
    audit_question = text
    history = _history_for_audit(req)
    if history:
        audit_question = (
            f"## Contexto da conversa (turnos anteriores)\n{history}\n\n"
            f"## Pergunta atual\n{text}"
        )
    return messages, last.content, audit_question


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


@router.post("/api/chat")
async def chat(req: ChatRequest):
    if not req.messages or req.messages[-1].role != "user":
        raise HTTPException(400, "A última mensagem deve ser do usuário")
    anthropic_messages, user_question, audit_question = _build_anthropic_messages(req)
    main_model = req.main_model or claude_svc.DEFAULT_MODEL
    auditor_model = req.auditor_model or gpt_svc.DEFAULT_MODEL
    rounds = _clamp_rounds(req.rounds)

    async def event_generator():
        # Conversa no Redis (best-effort)
        conv_id = req.conversation_id
        try:
            if conv_id is None:
                conv = await storage.create_conversation(user_question)
                conv_id = conv["id"]
        except Exception:
            conv_id = None
        if conv_id:
            yield _sse({"type": "meta", "conversation_id": conv_id})

        # ===== Resposta principal: Claude → failover GPT =====
        chunks: list[str] = []
        answered_by = "claude"
        model_info: dict = {}
        t_start = time.monotonic()
        t_first: float | None = None
        try:
            async for text in claude_svc.stream_claude(anthropic_messages, main_model, model_info):
                if t_first is None:
                    t_first = time.monotonic()
                chunks.append(text)
                yield _sse({"type": "chunk", "text": text})
        except Exception as e:
            chunks = []
            answered_by = "gpt"
            model_info = {}
            t_start = time.monotonic()
            t_first = None
            yield _sse({
                "type": "failover",
                "provider": "anthropic",
                "message": f"Problema na API da Anthropic ({main_model}): {e}",
                "took_over": auditor_model,
            })
            try:
                async for text in gpt_svc.stream_gpt_answer(anthropic_messages, auditor_model, model_info):
                    if t_first is None:
                        t_first = time.monotonic()
                    chunks.append(text)
                    yield _sse({"type": "chunk", "text": text})
            except Exception as e2:
                yield _sse({
                    "type": "error",
                    "message": (
                        "As duas APIs falharam. "
                        f"Anthropic: {e} | OpenAI: {e2}"
                    ),
                })
                yield "data: [DONE]\n\n"
                return

        answer = "".join(chunks)
        question_content = anthropic_messages[-1]["content"]
        round_infos: list[dict] = [model_info] if model_info.get("model") else []

        # ===== Debate em rodadas: GPT julga ↔ Claude refina (sempre termina no GPT) =====
        debate: list[dict] = []
        audit: dict = {}
        k = 2
        if answered_by == "claude":
            while True:
                is_last = k >= rounds
                try:
                    audit = await gpt_svc.audit_response(audit_question, answer, auditor_model)
                    audit["via"] = auditor_model
                except Exception as e:
                    try:
                        audit = await claude_svc.audit_with_claude(audit_question, answer, main_model)
                        audit["via"] = f"{main_model} (failover — problema na API da OpenAI: {e})"
                    except Exception as e2:
                        audit = {
                            "status": "ERROR",
                            "comment": f"Auditoria indisponível. OpenAI: {e} | Anthropic: {e2}",
                        }
                    is_last = True  # sem GPT não há debate

                audit["round"] = k
                audit["total"] = rounds

                if is_last:
                    break
                if audit.get("status") == "OK":
                    audit["early_stop"] = True  # aprovado: nada a refinar
                    break
                if audit.get("status") == "ERROR":
                    break

                # crítica intermediária → frontend (timeline do auditor)
                debate.append({"round": k, "audit": audit})
                yield _sse({"type": "debate", "round": k, "total": rounds, "audit": audit})

                # Claude julga a crítica e refina a resposta (rodada k+1)
                yield _sse({"type": "revision_start", "round": k + 1, "total": rounds})
                critique = audit.get("comment", "")
                if audit.get("response"):
                    critique += f"\n\nResposta sugerida pelo auditor:\n{audit['response']}"
                r_info: dict = {}
                r_chunks: list[str] = []
                try:
                    async for text in claude_svc.refine_claude(
                        question_content, answer, critique, main_model, r_info
                    ):
                        r_chunks.append(text)
                        yield _sse({"type": "chunk", "text": text})
                except Exception as e:
                    # refinamento falhou: mantém a resposta anterior e fecha o debate
                    yield _sse({
                        "type": "failover",
                        "provider": "anthropic",
                        "message": f"Refinamento falhou ({e}) — mantendo a resposta anterior.",
                        "took_over": "resposta anterior",
                    })
                    break
                if r_chunks:
                    answer = "".join(r_chunks)
                if r_info.get("model"):
                    round_infos.append(r_info)
                k += 2
        else:
            # GPT respondeu (Anthropic caiu) — sem debate. Auditoria: tenta Claude;
            # se a Anthropic seguir fora, SEGUNDA OPINIÃO com OUTRO modelo da OpenAI
            # (o app continua auditado mesmo 100% sem Anthropic, ex.: limite mensal).
            try:
                audit = await claude_svc.audit_with_claude(audit_question, answer, main_model)
                audit["via"] = f"{main_model} (auditando resposta do GPT)"
            except Exception as e:
                second = next(
                    (m for m in ("gpt-5.4", "gpt-4o", "gpt-5-mini", "gpt-4o-mini") if m != auditor_model),
                    "gpt-4o",
                )
                try:
                    audit = await gpt_svc.audit_response(audit_question, answer, second)
                    audit["via"] = f"{second} (segunda opinião OpenAI — Anthropic indisponível)"
                except Exception as e2:
                    audit = {
                        "status": "ERROR",
                        "comment": (
                            f"Sem auditoria: Anthropic indisponível ({e}) e a segunda "
                            f"opinião OpenAI também falhou ({e2})"
                        ),
                    }
            audit["round"] = 2
            audit["total"] = 2  # no failover o debate colapsa — não exibir "2/8"

        # ===== Métricas somadas de todas as rodadas (modelo, tokens, tempo, custo) =====
        t_end = time.monotonic()
        metrics = None
        if round_infos:
            total_in = sum(i.get("input_tokens") or 0 for i in round_infos)
            total_out = sum(i.get("output_tokens") or 0 for i in round_infos)
            duration = round(t_end - t_start, 2)
            used_model = round_infos[0]["model"]
            metrics = {
                "requested": main_model if answered_by == "claude" else auditor_model,
                "used": used_model,
                "input_tokens": total_in,
                "output_tokens": total_out,
                "duration_s": duration,
                "ttft_s": round(t_first - t_start, 2) if t_first else None,
                "tokens_per_s": round(total_out / duration, 1) if total_out and duration > 0 else None,
                "cost_usd": estimate_cost_usd(used_model, total_in, total_out),
                "rounds_executed": audit.get("round", 2),
                "rounds_total": rounds,
            }
            yield _sse({"type": "model_info", **metrics})

        # ===== Auto-execução: roda UMA vez, sobre a resposta FINAL =====
        artifacts = None
        code_to_run = executor.should_auto_run(user_question, answer)
        if code_to_run:
            result = await executor.run_with_autofix(code_to_run, main_model)
            artifacts = {
                "ok": result["ok"],
                "files": result["files"],
                "auto_fixed": result.get("auto_fixed", False),
                "error": None if result["ok"] else result["stderr"][:600],
            }
            yield _sse({"type": "artifacts", **artifacts})

        yield f"data: [AUDIT]{json.dumps(audit, ensure_ascii=False)}\n\n"

        # ===== Booster (opcional): opinião final dos MELHORES modelos =====
        booster = None
        if req.booster:
            best_claude, best_gpt = await _pick_booster_models()

            async def _safe(coro, via):
                try:
                    result = await coro
                    result["via"] = via
                    return result
                except Exception as e:
                    return {"status": "ERROR", "comment": f"Booster indisponível: {e}", "via": via}

            claude_op, gpt_op = await asyncio.gather(
                _safe(claude_svc.audit_with_claude(audit_question, answer, best_claude), best_claude),
                _safe(gpt_svc.audit_response(audit_question, answer, best_gpt), best_gpt),
            )
            booster = {"claude": claude_op, "gpt": gpt_op}
            yield _sse({"type": "booster", **booster})

        if conv_id:
            try:
                await storage.append_exchange(
                    conv_id, user_question, answer, audit, artifacts, metrics,
                    debate or None, booster,
                )
            except Exception:
                pass

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
