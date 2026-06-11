"""CRUD de conversas persistidas em Redis (histórico estilo Claude.ai)."""

from fastapi import APIRouter, HTTPException

from services import storage

router = APIRouter()


@router.get("/api/conversations")
async def list_conversations():
    try:
        return await storage.list_conversations()
    except Exception:
        # Redis fora do ar: app continua usável sem histórico
        return []


@router.get("/api/conversations/{conv_id}")
async def get_conversation(conv_id: str):
    conv = await storage.get_conversation(conv_id)
    if conv is None:
        raise HTTPException(404, "Conversa não encontrada")
    return conv


@router.delete("/api/conversations/{conv_id}")
async def delete_conversation(conv_id: str):
    await storage.delete_conversation(conv_id)
    return {"ok": True}
