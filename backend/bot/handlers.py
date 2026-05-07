import logging

from telegram import Update
from telegram.ext import ContextTypes

from database import get_db

logger = logging.getLogger(__name__)


def _fmt_amount(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


async def _get_user(telegram_id: int) -> dict | None:
    db = get_db()
    res = db.table("users").select("*").eq("telegram_id", telegram_id).execute()
    return res.data[0] if res.data else None


async def _is_authorized(telegram_id: int) -> bool:
    user = await _get_user(telegram_id)
    return bool(user and user.get("is_active"))


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    logger.info("TELEGRAM_ID recebido: %s", telegram_id)
    user = await _get_user(telegram_id)
    if not user:
        await update.message.reply_text(
            f"⛔ Você não está cadastrado no sistema.\n"
            f"Solicite acesso ao administrador.\n\n"
            f"_Seu ID: `{telegram_id}`_",
            parse_mode="Markdown"
        )
        return

    role_pt = "administrador" if user["role"] == "admin" else "contribuidor"
    await update.message.reply_text(
        f"👋 Olá, *{user['name']}*! Bem-vindo ao Gestor Financeiro.\n\n"
        f"Perfil: *{role_pt}*\n\n"
        f"Use /ajuda para ver as consultas disponíveis.",
        parse_mode="Markdown",
    )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "*Consultas disponíveis:*\n\n"
        "📌 _Em breve: /relatorio, /saldo, /meta, /patrimonio_",
        parse_mode="Markdown",
    )
