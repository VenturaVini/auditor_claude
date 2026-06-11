"""Persistência de conversas em Redis.

Modelo de dados:
  conv:{id}        -> string JSON {id, title, created_at, updated_at, messages, audits}
  conversations    -> zset (score = updated_at) para listagem ordenada por atividade

Se o Redis estiver indisponível, as funções falham silenciosamente (o chat
continua funcionando sem persistência) — exceto as rotas explícitas de
listagem/leitura, que propagam o erro.
"""

import json
import os
import time
import uuid

import redis.asyncio as aioredis

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")

_client: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _client
    if _client is None:
        _client = aioredis.from_url(REDIS_URL, decode_responses=True)
    return _client


def _key(conv_id: str) -> str:
    return f"conv:{conv_id}"


async def create_conversation(title: str) -> dict:
    now = time.time()
    conv = {
        "id": str(uuid.uuid4()),
        "title": title[:60] or "Nova conversa",
        "created_at": now,
        "updated_at": now,
        "messages": [],
        "audits": [],
    }
    r = get_redis()
    await r.set(_key(conv["id"]), json.dumps(conv, ensure_ascii=False))
    await r.zadd("conversations", {conv["id"]: now})
    return conv


async def get_conversation(conv_id: str) -> dict | None:
    raw = await get_redis().get(_key(conv_id))
    return json.loads(raw) if raw else None


async def list_conversations(limit: int = 50) -> list[dict]:
    r = get_redis()
    ids = await r.zrevrange("conversations", 0, limit - 1)
    summaries = []
    for conv_id in ids:
        raw = await r.get(_key(conv_id))
        if not raw:
            await r.zrem("conversations", conv_id)
            continue
        conv = json.loads(raw)
        summaries.append({
            "id": conv["id"],
            "title": conv["title"],
            "updated_at": conv["updated_at"],
            "message_count": len(conv["messages"]),
        })
    return summaries


async def delete_conversation(conv_id: str) -> None:
    r = get_redis()
    await r.delete(_key(conv_id))
    await r.zrem("conversations", conv_id)


async def append_exchange(
    conv_id: str,
    user_content: str,
    assistant_content: str,
    audit: dict | None,
    artifacts: dict | None = None,
    metrics: dict | None = None,
    debate: list | None = None,
    booster: dict | None = None,
) -> None:
    """Salva um turno completo (pergunta, resposta, auditoria, artefatos, métricas, debate, booster)."""
    r = get_redis()
    conv = await get_conversation(conv_id)
    if conv is None:
        return
    now = time.time()
    conv["messages"].append({"role": "user", "content": user_content})
    assistant_msg = {"role": "assistant", "content": assistant_content}
    if artifacts:
        assistant_msg["artifacts"] = artifacts
    if metrics:
        assistant_msg["metrics"] = metrics
    if debate:
        assistant_msg["debate"] = debate
    if booster:
        assistant_msg["booster"] = booster
    conv["messages"].append(assistant_msg)
    conv["audits"].append(audit or {"status": "ERROR", "comment": "Auditoria indisponível"})
    conv["updated_at"] = now
    await r.set(_key(conv_id), json.dumps(conv, ensure_ascii=False))
    await r.zadd("conversations", {conv_id: now})
