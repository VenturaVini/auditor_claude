"""Execução isolada de código Python e captura de artefatos.

Usado pelo endpoint /api/execute (botão manual / painel do auditor) e pela
auto-execução do chat (quando o usuário pede um arquivo, o código do modelo
é executado automaticamente e só os arquivos aparecem na resposta).
"""

import json
import mimetypes
import os
import re
import subprocess
import sys
import tempfile
import time
import uuid

from services.file_processor import UPLOAD_DIR

EXEC_TIMEOUT_SECONDS = 30
MAX_OUTPUT_CHARS = 10_000
MAX_ARTIFACT_MB = 25

# Marcador que o modelo coloca na 1ª linha de blocos destinados a GERAR ARQUIVO
FILE_MARKER = "# gerar-arquivo"

_FILE_KEYWORDS = (
    "xlsx", "pdf", "docx", "csv", ".png", "planilha", "arquivo",
    "gráfico", "grafico", "relatório em", "relatorio em", "documento",
)


def extract_python_blocks(markdown: str) -> list[str]:
    return re.findall(r"```python\n(.*?)```", markdown, re.S)


def wants_file(user_question: str) -> bool:
    q = user_question.lower()
    return any(k in q for k in _FILE_KEYWORDS)


def asked_for_code(user_question: str) -> bool:
    q = user_question.lower()
    return any(k in q for k in ("código", "codigo", "script", "code", "função", "funcao"))


def should_auto_run(user_question: str, answer: str) -> str | None:
    """Decide se a resposta deve ser auto-executada. Retorna o código ou None.

    Regras: roda blocos com o marcador `# gerar-arquivo`; sem marcador, roda
    todos os blocos se o usuário pediu um arquivo E não pediu código explicitamente.
    """
    blocks = extract_python_blocks(answer)
    if not blocks:
        return None
    marked = [b for b in blocks if b.lstrip().startswith(FILE_MARKER)]
    if marked:
        return "\n\n".join(marked)
    if wants_file(user_question) and not asked_for_code(user_question):
        return "\n\n".join(blocks)
    return None


def run_code(code: str) -> dict:
    """Roda o código num diretório temporário isolado e captura artefatos."""
    with tempfile.TemporaryDirectory(prefix="exec_") as workdir:
        script = os.path.join(workdir, "_script.py")
        with open(script, "w", encoding="utf-8") as f:
            f.write(code)

        try:
            proc = subprocess.run(
                [sys.executable, "-I", script],  # -I: modo isolado
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=EXEC_TIMEOUT_SECONDS,
            )
            stdout, stderr, returncode = proc.stdout, proc.stderr, proc.returncode
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "stdout": "",
                "stderr": f"Tempo limite de {EXEC_TIMEOUT_SECONDS}s excedido.",
                "files": [],
            }

        artifacts = []
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        for root, _, names in os.walk(workdir):
            for name in names:
                path = os.path.join(root, name)
                if path == script:
                    continue
                size = os.path.getsize(path)
                if size > MAX_ARTIFACT_MB * 1024 * 1024:
                    stderr += f"\n[Arquivo {name} ignorado: maior que {MAX_ARTIFACT_MB}MB]"
                    continue
                file_id = str(uuid.uuid4())
                with open(path, "rb") as src, open(os.path.join(UPLOAD_DIR, file_id), "wb") as dst:
                    dst.write(src.read())
                meta = {
                    "file_id": file_id,
                    "kind": "artifact",
                    "name": name,
                    "media_type": mimetypes.guess_type(name)[0] or "application/octet-stream",
                    "created_at": time.time(),
                }
                with open(os.path.join(UPLOAD_DIR, f"{file_id}.json"), "w", encoding="utf-8") as f:
                    json.dump(meta, f, ensure_ascii=False)
                artifacts.append({"file_id": file_id, "name": name, "size": size})

        return {
            "ok": returncode == 0,
            "stdout": stdout[:MAX_OUTPUT_CHARS],
            "stderr": stderr[:MAX_OUTPUT_CHARS],
            "files": artifacts,
        }


async def run_with_autofix(code: str, model: str | None = None) -> dict:
    """Executa; se falhar, pede 1 correção ao Claude (mesmo modelo da conversa) e re-executa."""
    import asyncio

    result = await asyncio.to_thread(run_code, code)
    if result["ok"] or not result["stderr"]:
        return result
    try:
        from services.claude import fix_code

        fixed = await fix_code(code, result["stderr"], model)
        if fixed.strip():
            retry = await asyncio.to_thread(run_code, fixed)
            if retry["ok"]:
                retry["auto_fixed"] = True
                return retry
            # expõe o erro da retentativa (ajuda a diagnosticar autofix que falhou)
            result["stderr"] += f"\n\n[auto-fix tentado e também falhou: {retry['stderr'][:300]}]"
    except Exception:
        pass
    return result
