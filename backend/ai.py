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
    leaves = [c for c in categories if c.get("parent_id")]
    type_label = "despesa" if tx_type == "expense" else "receita"

    cats_lines = "\n".join(
        f"  id:{c['id']} | {c['name']} | {c['classification']}"
        for c in leaves
        if c.get("type") == tx_type
    )

    prompt = f"""Classifique a transação financeira abaixo.

Descrição: "{description}"
Tipo: {type_label}

Categorias disponíveis ({type_label}):
{cats_lines}

Responda SOMENTE com JSON válido:
{{
  "category_id": "<id da categoria mais adequada ou null>",
  "classification": "<essential|controllable|avoidable>"
}}

Para receitas use classification "essential". Use null em category_id apenas se nenhuma categoria for adequada."""

    response = _client.chat.completions.create(
        model=_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    raw = _clean_json(response.choices[0].message.content)

    try:
        result = json.loads(raw)
        cat_id = result.get("category_id")
        if isinstance(cat_id, str) and cat_id.startswith("id:"):
            cat_id = cat_id[3:]
        return {
            "category_id":    cat_id,
            "classification": result.get("classification", "controllable"),
        }
    except json.JSONDecodeError:
        logger.warning("Groq retornou JSON inválido para categorização: %s", raw)
        return {"category_id": None, "classification": "controllable"}
