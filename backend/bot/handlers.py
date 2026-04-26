import logging
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from ai import parse_transaction
from database import get_db
from bot.keyboards import (
    accounts_keyboard,
    classification_keyboard,
    confirm_keyboard,
    edit_field_keyboard,
    recurring_keyboard,
)

logger = logging.getLogger(__name__)

_CLS_PT = {
    "essential":    "🔴 Essencial",
    "controllable": "🟡 Controlável",
    "avoidable":    "🟢 Evitável",
}

_EDIT_PROMPTS = {
    "amount":      "💰 Digite o novo *valor* (ex: 150.50 ou 150,50):",
    "description": "📝 Digite a nova *descrição*:",
    "category":    "📂 Digite o nome (ou parte) da *categoria* desejada:",
    "date":        "📅 Digite a nova *data* no formato *DD/MM/AAAA*:",
}


# ── helpers ──────────────────────────────────────────────────────────────────

def _fmt_amount(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_preview(tx: dict) -> str:
    tx_type  = "📈 Receita" if tx["type"] == "income" else "📉 Despesa"
    date_str = datetime.strptime(tx["transaction_date"], "%Y-%m-%d").strftime("%d/%m/%Y")
    cls_str  = _CLS_PT.get(tx.get("classification", ""), tx.get("classification", "—"))
    acc_str  = tx.get("account_name") or "Não informada"
    rec_str  = "✅ Sim" if tx.get("is_recurring") else "Não"
    cat_str  = tx.get("category_name") or "Não identificada"

    return (
        f"📋 *Transação identificada:*\n\n"
        f"*Tipo:* {tx_type}\n"
        f"*Valor:* {_fmt_amount(tx['amount'])}\n"
        f"*Descrição:* {tx['description']}\n"
        f"*Categoria:* {cat_str}\n"
        f"*Classificação:* {cls_str}\n"
        f"*Data:* {date_str}\n"
        f"*Conta:* {acc_str}\n"
        f"*Fixo/Recorrente:* {rec_str}\n\n"
        f"_Confirmar ou editar?_"
    )


async def _get_user(telegram_id: int) -> dict | None:
    db = get_db()
    res = db.table("users").select("*").eq("telegram_id", telegram_id).execute()
    return res.data[0] if res.data else None


async def _is_authorized(telegram_id: int) -> bool:
    user = await _get_user(telegram_id)
    return bool(user and user.get("is_active"))


async def _categories_flat(db) -> list[dict]:
    res = db.table("categories").select("id, name, parent_id, type, classification").eq("is_active", True).execute()
    cats = res.data
    cat_map = {c["id"]: c for c in cats}

    def full_path(cat_id: str) -> str:
        c = cat_map.get(cat_id)
        if not c:
            return ""
        if c["parent_id"]:
            return f"{full_path(c['parent_id'])} > {c['name']}"
        return c["name"]

    for c in cats:
        c["full_path"] = full_path(c["id"])
    return cats


async def _save_state(telegram_id: int, state: str, context: dict):
    get_db().table("conversation_states").upsert({
        "telegram_id": telegram_id,
        "state": state,
        "context": context,
        "updated_at": datetime.utcnow().isoformat(),
    }).execute()


async def _load_state(telegram_id: int) -> dict | None:
    res = get_db().table("conversation_states").select("*").eq("telegram_id", telegram_id).execute()
    return res.data[0] if res.data else None


async def _clear_state(telegram_id: int):
    get_db().table("conversation_states").delete().eq("telegram_id", telegram_id).execute()


# ── command handlers ──────────────────────────────────────────────────────────

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await _get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text(
            "⛔ Você não está cadastrado no sistema.\n"
            "Solicite acesso ao administrador."
        )
        return

    role_pt = "administrador" if user["role"] == "admin" else "contribuidor"
    await update.message.reply_text(
        f"👋 Olá, *{user['name']}*! Bem-vindo ao Gestor Financeiro.\n\n"
        f"Perfil: *{role_pt}*\n\n"
        f"Para registrar uma transação, envie uma mensagem em texto livre:\n"
        f"• _Gastei 150 reais no supermercado hoje_\n"
        f"• _Recebi salário de 5000_\n"
        f"• _Paguei conta de luz 89,50 ontem_\n\n"
        f"Use /ajuda para ver os comandos disponíveis.",
        parse_mode="Markdown",
    )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "*Comandos disponíveis:*\n\n"
        "Envie qualquer texto descrevendo receita ou despesa — "
        "o bot classifica automaticamente e pede confirmação.\n\n"
        "📌 _Em breve: /relatorio, /meta, /patrimonio_",
        parse_mode="Markdown",
    )


# ── main message handler ──────────────────────────────────────────────────────

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id

    if not await _is_authorized(telegram_id):
        await update.message.reply_text("⛔ Você não tem permissão para usar este bot.")
        return

    state = await _load_state(telegram_id)
    if state and state["state"].startswith("editing_"):
        await _handle_edit_value(update, state)
        return

    processing_msg = await update.message.reply_text("⏳ Analisando sua mensagem...")

    try:
        db = get_db()
        categories = await _categories_flat(db)
        accounts   = db.table("accounts").select("id, name, type").eq("is_active", True).execute().data

        tx = parse_transaction(update.message.text, categories, accounts)

        await _save_state(telegram_id, "confirming", tx)
        await processing_msg.delete()
        await update.message.reply_text(
            _fmt_preview(tx),
            parse_mode="Markdown",
            reply_markup=confirm_keyboard(),
        )

    except Exception as exc:
        logger.error("Error processing message from %s: %s", telegram_id, exc)
        await processing_msg.edit_text(
            f"❌ {exc}\n\nTente descrever a transação de outra forma."
        )


# ── callback handler ──────────────────────────────────────────────────────────

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    telegram_id = query.from_user.id
    data = query.data

    if not await _is_authorized(telegram_id):
        await query.edit_message_text("⛔ Sem permissão.")
        return

    state = await _load_state(telegram_id)

    # ── confirm ──
    if data == "confirm":
        if not state:
            await query.edit_message_text("❌ Sessão expirada. Envie a transação novamente.")
            return

        tx   = state["context"]
        user = await _get_user(telegram_id)

        get_db().table("transactions").insert({
            "user_id":          user["id"],
            "account_id":       tx.get("account_id"),
            "category_id":      tx.get("category_id"),
            "description":      tx["description"],
            "amount":           tx["amount"],
            "type":             tx["type"],
            "classification":   tx.get("classification"),
            "transaction_date": tx["transaction_date"],
            "is_recurring":     tx.get("is_recurring", False),
            "source":           "telegram",
            "is_confirmed":     True,
        }).execute()

        await _clear_state(telegram_id)
        await query.edit_message_text(
            f"✅ *Registrado!*\n_{tx['description']} — {_fmt_amount(tx['amount'])}_",
            parse_mode="Markdown",
        )

    # ── cancel ──
    elif data == "cancel":
        await _clear_state(telegram_id)
        await query.edit_message_text("❌ Lançamento cancelado.")

    # ── open edit menu ──
    elif data == "edit":
        await query.edit_message_reply_markup(reply_markup=edit_field_keyboard())

    # ── back to preview ──
    elif data == "back_to_confirm":
        if state:
            await query.edit_message_text(
                _fmt_preview(state["context"]),
                parse_mode="Markdown",
                reply_markup=confirm_keyboard(),
            )

    # ── edit specific field ──
    elif data.startswith("edit_"):
        field = data[5:]

        if field == "classification":
            await query.edit_message_reply_markup(reply_markup=classification_keyboard())

        elif field == "account":
            accounts = get_db().table("accounts").select("id, name, type").eq("is_active", True).execute().data
            await query.edit_message_reply_markup(reply_markup=accounts_keyboard(accounts))

        elif field == "recurring":
            await query.edit_message_reply_markup(reply_markup=recurring_keyboard())

        else:
            prompt = _EDIT_PROMPTS.get(field, "Digite o novo valor:")
            await _save_state(telegram_id, f"editing_{field}", state["context"] if state else {})
            await query.edit_message_text(prompt, parse_mode="Markdown")

    # ── classification chosen ──
    elif data.startswith("cls_"):
        cls_map = {"cls_essential": "essential", "cls_controllable": "controllable", "cls_avoidable": "avoidable"}
        new_cls = cls_map.get(data)
        if state and new_cls:
            tx = state["context"]
            tx["classification"] = new_cls
            await _save_state(telegram_id, "confirming", tx)
            await query.edit_message_text(_fmt_preview(tx), parse_mode="Markdown", reply_markup=confirm_keyboard())

    # ── account chosen ──
    elif data.startswith("acc_"):
        acc_id = data[4:]
        if state:
            tx  = state["context"]
            acc = get_db().table("accounts").select("id, name").eq("id", acc_id).execute().data
            if acc:
                tx["account_id"]   = acc[0]["id"]
                tx["account_name"] = acc[0]["name"]
            await _save_state(telegram_id, "confirming", tx)
            await query.edit_message_text(_fmt_preview(tx), parse_mode="Markdown", reply_markup=confirm_keyboard())

    # ── recurring chosen ──
    elif data.startswith("rec_"):
        if state:
            tx = state["context"]
            tx["is_recurring"] = data == "rec_true"
            await _save_state(telegram_id, "confirming", tx)
            await query.edit_message_text(_fmt_preview(tx), parse_mode="Markdown", reply_markup=confirm_keyboard())


# ── edit value received via text ─────────────────────────────────────────────

async def _handle_edit_value(update: Update, conv_state: dict):
    telegram_id = update.effective_user.id
    field       = conv_state["state"][len("editing_"):]
    tx          = conv_state["context"]
    new_value   = update.message.text.strip()

    try:
        if field == "amount":
            tx["amount"] = float(new_value.replace(",", ".").replace("R$", "").strip())

        elif field == "description":
            tx["description"] = new_value

        elif field == "date":
            parsed = datetime.strptime(new_value, "%d/%m/%Y")
            tx["transaction_date"] = parsed.strftime("%Y-%m-%d")

        elif field == "category":
            db   = get_db()
            cats = await _categories_flat(db)
            match = next(
                (c for c in cats if c.get("parent_id") and new_value.lower() in c["name"].lower()),
                None,
            )
            if match:
                tx["category_id"]   = match["id"]
                tx["category_name"] = match["full_path"]
            else:
                await update.message.reply_text(
                    f"⚠️ Categoria '{new_value}' não encontrada. "
                    f"Tente outro nome ou cancele o lançamento."
                )
                return

        await _save_state(telegram_id, "confirming", tx)
        await update.message.reply_text(
            _fmt_preview(tx),
            parse_mode="Markdown",
            reply_markup=confirm_keyboard(),
        )

    except ValueError as exc:
        await update.message.reply_text(f"❌ Valor inválido: {exc}\nTente novamente.")
