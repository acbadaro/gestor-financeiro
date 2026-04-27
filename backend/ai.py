import json
import logging
from datetime import date

import google.generativeai as genai

from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

genai.configure(api_key=GEMINI_API_KEY)
_model = genai.GenerativeModel("gemini-2.0-flash")


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
        if c.get("parent_id")  # apenas subcategorias (folhas)
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

    response = _model.generate_content(prompt)
    raw = _clean_json(response.text)

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("Gemini returned invalid JSON: %s\nRaw: %s", e, raw)
        raise ValueError("Não consegui interpretar a transação. Tente descrever de forma diferente.") from e
