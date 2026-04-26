from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirmar", callback_data="confirm"),
            InlineKeyboardButton("✏️ Editar", callback_data="edit"),
        ],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancel")],
    ])


def edit_field_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Valor",          callback_data="edit_amount")],
        [InlineKeyboardButton("📝 Descrição",       callback_data="edit_description")],
        [InlineKeyboardButton("📂 Categoria",       callback_data="edit_category")],
        [InlineKeyboardButton("📅 Data",            callback_data="edit_date")],
        [InlineKeyboardButton("🏦 Conta",           callback_data="edit_account")],
        [InlineKeyboardButton("🏷️ Classificação",  callback_data="edit_classification")],
        [InlineKeyboardButton("🔄 Fixo/Recorrente", callback_data="edit_recurring")],
        [InlineKeyboardButton("↩️ Voltar",          callback_data="back_to_confirm")],
    ])


def classification_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔴 Essencial",   callback_data="cls_essential")],
        [InlineKeyboardButton("🟡 Controlável", callback_data="cls_controllable")],
        [InlineKeyboardButton("🟢 Evitável",    callback_data="cls_avoidable")],
        [InlineKeyboardButton("↩️ Voltar",       callback_data="edit")],
    ])


def accounts_keyboard(accounts: list[dict]) -> InlineKeyboardMarkup:
    icons = {"checking": "🏦", "credit_card": "💳", "other": "💼"}
    buttons = [
        [InlineKeyboardButton(
            f"{icons.get(a['type'], '💰')} {a['name']}",
            callback_data=f"acc_{a['id']}"
        )]
        for a in accounts
    ]
    buttons.append([InlineKeyboardButton("↩️ Voltar", callback_data="edit")])
    return InlineKeyboardMarkup(buttons)


def recurring_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Sim, é fixo/recorrente", callback_data="rec_true")],
        [InlineKeyboardButton("1️⃣ Não, é avulso",          callback_data="rec_false")],
        [InlineKeyboardButton("↩️ Voltar",                  callback_data="edit")],
    ])
