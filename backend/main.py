import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request, Response
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def error_handler(update: object, context) -> None:
    logger.error("Exceção ao processar update:", exc_info=context.error)


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
    webhook_url = os.environ.get("WEBHOOK_URL", "").rstrip("/")
    await ptb.initialize()
    await ptb.start()
    if webhook_url:
        await ptb.bot.set_webhook(
            url=f"{webhook_url}/webhook",
            drop_pending_updates=True,
        )
        logger.info("Bot iniciado em modo webhook: %s/webhook", webhook_url)
    else:
        logger.warning("WEBHOOK_URL não definido — bot sem webhook.")
    yield
    await ptb.stop()
    await ptb.shutdown()


app = FastAPI(title="Gestor Financeiro API", lifespan=lifespan)


@app.post("/webhook")
async def webhook_handler(request: Request):
    data = await request.json()
    update = Update.de_json(data, ptb.bot)
    await ptb.process_update(update)
    return Response(status_code=200)


@app.api_route("/", methods=["GET", "HEAD"])
async def root():
    return {"status": "ok"}

@app.api_route("/health", methods=["GET", "HEAD"])
async def health():
    return {"status": "ok", "bot": "webhook"}


# ── entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
