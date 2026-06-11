"""Integração com a OpenAI.

- audit_response(): auditor padrão (modelo selecionável). Exceções de API propagam
  para o chamador decidir o fallback (auditar com Claude).
- stream_gpt_answer(): resposta principal em streaming, usada como FAILOVER quando
  a API da Anthropic está indisponível.
"""

import json
import re

from openai import AsyncOpenAI

DEFAULT_MODEL = "gpt-4o-mini"
AVAILABLE_MODELS = ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini"]

AUDITOR_SYSTEM = """Você é um auditor de respostas de IA. Analise a resposta do Claude à pergunta do usuário.

CONTEXTO DA INTERFACE: quando o usuário pede um arquivo (XLSX, DOCX, PDF, gráfico etc.), o sistema
EXECUTA AUTOMATICAMENTE os blocos de código Python da resposta e entrega os arquivos gerados ao
usuário — o código fica oculto na interface. Portanto, responder com código Python que salva o
arquivo É a entrega correta do arquivo — NÃO marque isso como falha. Avalie, em vez disso, se o
código está correto e se os dados usados são precisos.

IMAGENS: você não tem acesso a imagens anexadas (apenas o modelo principal as vê). NÃO marque como
erro afirmações sobre imagens só porque não pode verificá-las — avalie o restante da resposta.

Se a resposta estiver correta e completa, responda APENAS com:
{"status": "OK", "comment": "frase breve confirmando"}

Se houver erro, imprecisão ou algo relevante a acrescentar, responda com:
{"status": "REVIEW", "comment": "o que está errado ou faltando", "response": "sua resposta completa"}

Quando a resposta auditada contiver CÓDIGO com erros (dados errados, bug, arquivo que não atende ao
pedido), seu "response" deve: explicar a correção em TEXTO primeiro e incluir o código Python
COMPLETO e CORRIGIDO num ÚNICO bloco ```python ao final — a interface executa o SEU código e
entrega os arquivos ao usuário (o código fica recolhido na tela; o texto é o que o usuário lê).
Salve arquivos no diretório de trabalho ATUAL com caminho relativo (ex.: wb.save("arquivo.xlsx"))
— NUNCA use /mnt/data ou caminhos absolutos. Corrija os dados, não apenas aponte o erro.

Responda APENAS com JSON válido."""

MAIN_SYSTEM = (
    "Você é um assistente de IA avançado. Responda com clareza, precisão e profundidade. "
    "Use markdown quando enriquecer a resposta. Seja direto e objetivo.\n"
    "GERAÇÃO DE ARQUIVOS: quando o usuário pedir um arquivo (XLSX, PDF, DOCX, CSV, gráfico), "
    "escreva um bloco ```python autossuficiente com a primeira linha `# gerar-arquivo` que salve "
    "o arquivo no diretório atual — ele é executado automaticamente e o usuário recebe o arquivo. "
    "Não explique o código nem mencione execução. Bibliotecas: openpyxl, python-docx, reportlab, "
    "pandas, matplotlib (Agg). Sem internet.\n"
    "QUALIDADE: documentos sempre bonitos e estruturados. PDF: SEMPRE reportlab.platypus "
    "(SimpleDocTemplate/Paragraph/Table/Spacer/KeepTogether, A4, margens 2cm) — NUNCA "
    "canvas.drawString para texto corrido (corta na borda); tabelas com cabeçalho de fundo "
    "escuro/texto branco, GRID, zebra e repeatRows=1; seções em KeepTogether p/ não cortar na "
    "quebra de página; PROIBIDO emoji em PDF (vira quadrado ■ — use texto/cor/negrito; acentos do "
    "português são suportados, escreva normalmente). "
    "DOCX: add_heading + tabelas com estilo. XLSX: cabeçalho com PatternFill + Font branca, "
    "larguras ajustadas, number_format."
)

_client = AsyncOpenAI()  # lê OPENAI_API_KEY do ambiente

# Prefixos de modelos de chat (a lista da OpenAI mistura tts, whisper, embeddings...)
_CHAT_PREFIXES = ("gpt-", "chatgpt-", "o1", "o3", "o4")
_EXCLUDE_FRAGMENTS = (
    "instruct", "audio", "realtime", "transcribe", "tts", "search",
    "image", "embedding", "moderation", "davinci", "babbage",
    "codex", "chat-latest",  # codex: não é p/ chat; chat-latest: duplica o alias base
)
# Variantes datadas duplicam o alias da família (gpt-4o-2024-05-13, gpt-4-0613...)
_DATED = re.compile(r"-\d{4}(-\d{2}-\d{2})?$")


async def list_openai_models() -> list[str]:
    """Lista os modelos de chat disponíveis para a chave (Models API).

    Mantém um item por família (antigos e novos), sem snapshots datados.
    Exceções propagam — o chamador usa AVAILABLE_MODELS como fallback.
    """
    models = []
    page = await _client.models.list()
    for m in page.data:
        mid = m.id
        if not mid.startswith(_CHAT_PREFIXES):
            continue
        if any(frag in mid for frag in _EXCLUDE_FRAGMENTS):
            continue
        if _DATED.search(mid):
            continue
        models.append(mid)
    return sorted(models)


async def audit_response(question: str, claude_answer: str, model: str | None = None) -> dict:
    """Roda a auditoria. Erros de PARSING são tolerados; erros de API propagam.

    Modelos antigos (gpt-4, gpt-3.5) não suportam response_format json_object —
    nesse caso refaz a chamada sem o parâmetro e parseia o JSON manualmente.
    """
    messages = [
        {"role": "system", "content": AUDITOR_SYSTEM},
        {
            "role": "user",
            "content": (
                f"## Pergunta do usuário\n{question}\n\n"
                f"## Resposta do Claude\n{claude_answer}"
            ),
        },
    ]
    try:
        completion = await _client.chat.completions.create(
            model=model or DEFAULT_MODEL,
            response_format={"type": "json_object"},
            messages=messages,
        )
    except Exception as e:
        if "response_format" not in str(e):
            raise
        completion = await _client.chat.completions.create(
            model=model or DEFAULT_MODEL,
            messages=messages,
        )
    raw = (completion.choices[0].message.content or "{}").strip()
    if raw.startswith("```"):  # modelos sem json mode podem cercar o JSON
        raw = raw.strip("`").lstrip("json").strip()
    try:
        data = json.loads(raw)
        if "status" not in data:
            data = {"status": "REVIEW", "comment": raw}
    except json.JSONDecodeError:
        data = {"status": "REVIEW", "comment": raw}
    if completion.usage:
        data["usage"] = {
            "input_tokens": completion.usage.prompt_tokens,
            "output_tokens": completion.usage.completion_tokens,
        }
    return data


def _to_openai_messages(anthropic_messages: list[dict]) -> list[dict]:
    """Converte mensagens do formato Anthropic p/ OpenAI (texto apenas).

    No failover, imagens são descartadas (formatos de visão incompatíveis);
    o texto extraído de documentos já está embutido no texto da mensagem.
    """
    out = [{"role": "system", "content": MAIN_SYSTEM}]
    for m in anthropic_messages:
        content = m["content"]
        if isinstance(content, list):
            content = "\n".join(b.get("text", "") for b in content if b.get("type") == "text")
        out.append({"role": m["role"], "content": content})
    return out


async def stream_gpt_answer(
    anthropic_messages: list[dict], model: str | None = None, info: dict | None = None
):
    """Resposta principal via GPT em streaming (failover da Anthropic)."""
    stream = await _client.chat.completions.create(
        model=model or DEFAULT_MODEL,
        messages=_to_openai_messages(anthropic_messages),
        stream=True,
        stream_options={"include_usage": True},
    )
    async for chunk in stream:
        if info is not None and chunk.model:
            info["model"] = chunk.model  # modelo REAL reportado pela API
        if info is not None and chunk.usage:
            info["input_tokens"] = chunk.usage.prompt_tokens
            info["output_tokens"] = chunk.usage.completion_tokens
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            yield delta
