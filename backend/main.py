import asyncio
import contextlib
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import chat, upload, download, conversations, execute
from services.file_processor import cleanup_expired_uploads


async def _cleanup_loop():
    while True:
        cleanup_expired_uploads()
        await asyncio.sleep(300)  # a cada 5 minutos


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_cleanup_loop())
    yield
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


app = FastAPI(title="Claude + GPT Auditor", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(upload.router)
app.include_router(download.router)
app.include_router(conversations.router)
app.include_router(execute.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
