"""POST /api/execute — execução manual de código (fallback e painel do auditor).
GET /api/files/{id} — download de artefatos gerados.

A execução principal acontece automaticamente no fluxo do chat (ver chat.py);
este endpoint atende o botão "Executar código" do painel de auditoria e o
fallback do chat.
"""

import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from services.executor import run_code, run_with_autofix
from services.file_processor import UPLOAD_DIR, load_file_meta

import asyncio

router = APIRouter()


class ExecuteRequest(BaseModel):
    code: str
    auto_fix: bool = True  # se falhar, tenta UMA correção automática via Claude


@router.post("/api/execute")
async def execute(req: ExecuteRequest):
    if not req.code.strip():
        raise HTTPException(400, "Código vazio")
    if req.auto_fix:
        return await run_with_autofix(req.code)
    return await asyncio.to_thread(run_code, req.code)


@router.get("/api/files/{file_id}")
async def download_file(file_id: str):
    meta = load_file_meta(file_id)
    path = os.path.join(UPLOAD_DIR, file_id)
    if meta is None or not os.path.exists(path):
        raise HTTPException(404, "Arquivo expirou ou não foi encontrado")
    return FileResponse(
        path,
        media_type=meta.get("media_type", "application/octet-stream"),
        filename=meta.get("name", file_id),
    )
