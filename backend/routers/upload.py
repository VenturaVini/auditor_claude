"""POST /api/upload — recebe multipart/form-data e processa por tipo."""

import os

from fastapi import APIRouter, HTTPException, UploadFile

from services.file_processor import process_upload, cleanup_expired_uploads

router = APIRouter()

MAX_FILE_SIZE_MB = int(os.environ.get("MAX_FILE_SIZE_MB", "10"))


@router.post("/api/upload")
async def upload(file: UploadFile):
    cleanup_expired_uploads()  # limpeza preguiçosa a cada upload

    data = await file.read()
    if len(data) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(413, f"Arquivo excede o limite de {MAX_FILE_SIZE_MB}MB")
    if not data:
        raise HTTPException(400, "Arquivo vazio")

    try:
        return process_upload(file.filename or "arquivo", data)
    except ValueError as e:
        raise HTTPException(415, str(e))
    except Exception as e:
        raise HTTPException(500, f"Falha ao processar arquivo: {e}")
