"""
Parser para fatura do cartão Itaú (XLSX).

Formato esperado: planilha com 3 colunas — data | lançamento | valor
Algumas células de valor podem ter formatação de data aplicada por engano;
essas linhas são ignoradas com aviso.
"""

import io
import logging
from datetime import date, datetime

import openpyxl

logger = logging.getLogger(__name__)


def _parse_valor(val) -> float | None:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, datetime):
        # Célula numérica com formato de data aplicado por engano — ignorar
        logger.debug("Valor ignorado (formatado como data): %s", val)
        return None
    if isinstance(val, str):
        clean = val.strip().replace("R$", "").replace(" ", "")
        if "," in clean:
            # Brazilian format: 1.234,56 → remove thousands dot, use comma as decimal
            clean = clean.replace(".", "").replace(",", ".")
        # else: already uses dot as decimal (e.g. "8.93") — keep as-is
        try:
            return float(clean)
        except ValueError:
            return None
    return None


def _parse_date(val) -> date | None:
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y"):
            try:
                return datetime.strptime(val.strip(), fmt).date()
            except ValueError:
                continue
    return None


def parse_xlsx_fatura(content: bytes) -> list[dict]:
    transactions: list[dict] = []

    wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
    ws = wb.active

    header_found = False
    for row in ws.iter_rows(values_only=True):
        if not any(v is not None for v in row):
            continue

        # Detectar linha de cabeçalho
        if not header_found:
            first = str(row[0]).lower().strip() if row[0] else ""
            if first in ("data", "date"):
                header_found = True
            continue

        data_val, lancamento, valor_val = row[0], row[1], row[2]

        tx_date = _parse_date(data_val)
        if tx_date is None:
            continue

        amount = _parse_valor(valor_val)
        if amount is None:
            continue

        desc = str(lancamento).strip() if lancamento else ""
        if not desc:
            continue

        # Fatura de cartão: valores positivos = despesa, negativos = estorno/crédito
        transactions.append({
            "transaction_date": tx_date.isoformat(),
            "description":      desc,
            "amount":           abs(amount),
            "type":             "expense" if amount >= 0 else "income",
            "source":           "drive_xlsx",
        })

    logger.info("XLSX fatura: %d transações extraídas", len(transactions))
    return transactions
