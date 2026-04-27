import asyncio
import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from config import TELEGRAM_BOT_TOKEN
from bot.handlers import (
    callback_handler,
    help_handler,
    message_handler,
    start_handler,
)


async def error_handler(update: object, context) -> None:
    logger.error("Exceção ao processar update:", exc_info=context.error)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── Telegram Application ──────────────────────────────────────────────────────

ptb: Application = (
    Application.builder()
    .token(TELEGRAM_BOT_TOKEN)
    .build()
)

ptb.add_handler(CommandHandler("start",  start_handler))
ptb.add_handler(CommandHandler("ajuda",  help_handler))
ptb.add_handler(CommandHandler("help",   help_handler))
ptb.add_handler(CallbackQueryHandler(callback_handler))
ptb.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
ptb.add_error_handler(error_handler)


# ── FastAPI lifespan ──────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando bot Telegram (polling)...")
    await ptb.initialize()
    await ptb.start()
    await ptb.updater.start_polling(drop_pending_updates=True)
    logger.info("Bot ativo e aguardando mensagens.")
    yield
    logger.info("Encerrando bot...")
    await ptb.updater.stop()
    await ptb.stop()
    await ptb.shutdown()


app = FastAPI(title="Gestor Financeiro API", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "bot": "running"}


# ── entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
