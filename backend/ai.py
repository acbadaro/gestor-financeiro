import json
import logging
from datetime import date

from groq import Groq

from config import GROQ_API_KEY

logger = logging.getLogger(__name__)

_client = Groq(api_key=GROQ_API_KEY)
_MODEL = "llama-3.3-70b-versatile"


def _clean_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


def parse_transaction(text: str, categories: list[dict], accounts: list[dict]) -> dict:
    today = date.today().strftime("%d/%m/%Y")

    cats_lines = "\n".join(
        f"  id:{c['id']} | {c['full_path']} | {c['type']} | {c['classification']}"
        for c in categories
        if c.get("parent_id")
    )
    accs_lines = "\n".join(
        f"  id:{a['id']} | {a['name']} | {a['type']}"
        for a in accounts
    )

    prompt = f"""Você é um assistente financeiro pessoal brasileiro. Analise o texto e extraia a transação.

Texto do usuário: "{text}"
Data de hoje: {today}

Categorias disponíveis:
{cats_lines}

Contas disponíveis:
{accs_lines}

Responda SOMENTE com JSON válido, sem explicações:
{{
  "amount": <decimal positivo>,
  "type": "<income|expense>",
  "description": "<descrição curta e clara em português>",
  "transaction_date": "<YYYY-MM-DD>",
  "category_id": "<id da categoria mais adequada ou null>",
  "category_name": "<nome completo da categoria ou null>",
  "account_id": "<id da conta mencionada ou null>",
  "account_name": "<nome da conta mencionada ou null>",
  "classification": "<essential|controllable|avoidable>",
  "is_recurring": <true|false>,
  "confidence": <0.0 a 1.0>
}}

Regras:
- Se a data não for mencionada, use hoje ({today}) no formato YYYY-MM-DD
- Se a conta não for mencionada, deixe null em account_id e account_name
- is_recurring: true somente se o texto mencionar "todo mês", "mensalmente", "fixo" etc.
- classification: use a classificação da categoria, mas ajuste ao contexto se necessário
"""

    response = _client.chat.completions.create(
        model=_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    raw = _clean_json(response.choices[0].message.content)

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("Groq retornou JSON inválido: %s\nRaw: %s", e, raw)
        raise ValueError("Não consegui interpretar a transação. Tente descrever de forma diferente.") from e


def categorize_transaction(description: str, tx_type: str, categories: list[dict]) -> dict:
    """Categorize a transaction from Drive import using only description and type."""
    cat_map = {c["id"]: c for c in categories}

    def full_path(c: dict) -> str:
        if c.get("parent_id") and c["parent_id"] in cat_map:
            return f"{cat_map[c['parent_id']]['name']} > {c['name']}"
        return c["name"]

    leaves = [c for c in categories if c.get("parent_id") and c.get("type") == tx_type]
    type_label = "despesa" if tx_type == "expense" else "receita"

    cats_lines = "\n".join(
        f"  {c['id']} | {full_path(c)} | {c.get('classification','controllable')}"
        for c in leaves
    )

    # IDs de fallback "Outros" para cada tipo
    fallback_id = (
        "d0000000-0000-0000-0012-000000000013" if tx_type == "expense"
        else "ee000000-0000-0000-0000-000000000015"
    )

    prompt = f"""Classifique a transação financeira abaixo na subcategoria mais específica.

Descrição: "{description}"
Tipo: {type_label}

Subcategorias disponíveis (formato: id | Categoria > Subcategoria | classificação):
{cats_lines}

Responda SOMENTE com JSON válido:
{{
  "category_id": "<uuid exato da subcategoria mais adequada>",
  "classification": "<essential|controllable|avoidable>"
}}

Regras:
- Use o uuid exato, sem prefixos
- Prefira a subcategoria mais específica (ex: "Alimentação > Supermercado" em vez de só "Alimentação")
- Se não souber classificar, use o id "{fallback_id}" (Outros/Geral)
- Nunca retorne null em category_id"""

    response = _client.chat.completions.create(
        model=_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    raw = _clean_json(response.choices[0].message.content)

    try:
        result = json.loads(raw)
        cat_id = result.get("category_id") or fallback_id
        if isinstance(cat_id, str) and cat_id.startswith("id:"):
            cat_id = cat_id[3:]
        valid_ids = {c["id"] for c in leaves}
        if cat_id not in valid_ids:
            cat_id = fallback_id
        return {
            "category_id":    cat_id,
            "classification": result.get("classification", "controllable"),
        }
    except json.JSONDecodeError:
        logger.warning("Groq retornou JSON inválido para categorização: %s", raw)
        return {"category_id": fallback_id, "classification": "controllable"}
