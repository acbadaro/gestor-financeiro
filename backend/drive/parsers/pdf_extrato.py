"""
Parser para extrato mensal da conta corrente Itaú (PDF).

Formato esperado: texto extraído pelo pdfplumber com linhas no padrão:
  DD/MM  descrição  [valor_entrada]  [valor_saída]  [saldo]
Valores no formato brasileiro: 1.234,56 (débito: 1.234,56-)
"""

import io
import logging
import re
from datetime import datetime

import pdfplumber

logger = logging.getLogger(__name__)

_SECTION_START = re.compile(r"conta corrente.*movimenta", re.IGNORECASE)
_SECTION_END   = re.compile(r"conta corrente.*d[eé]bitos autom", re.IGNORECASE)
_DATE_PREFIX   = re.compile(r"^(\d{2}/\d{2})\s+")
_SKIP_KEYWORDS = (
    "saldo anterior", "saldo em c/c", "saldo final",
    "total entradas", "totalentradas", "total sa",
    "entradas (cr", "saídas (d", "data descri",
    "a =", "b =", "c =", "d =", "g =", "p =",
    "para demais", "este material",
)

# Prefixos de rodapé/sidebar do Itaú que podem mesclar com linhas de transação
_SIDEBAR_PREFIX = re.compile(
    r"^(?:explicativas\s+nofinal\s+doextrato|pelabolsa\s+de\s+valores)\s*",
    re.IGNORECASE,
)

# Matches one or two Brazilian amounts at end of line: 1.234,56  or  1.234,56-
_TWO_AMOUNTS = re.compile(
    r"([\d]{1,3}(?:\.[\d]{3})*,\d{2}-?)\s+([\d]{1,3}(?:\.[\d]{3})*,\d{2}-?)\s*$"
)
_ONE_AMOUNT = re.compile(r"([\d]{1,3}(?:\.[\d]{3})*,\d{2}-?)\s*$")


def _to_float(value: str) -> float:
    return float(value.rstrip("-").replace(".", "").replace(",", "."))


def _detect_year(pdf) -> int:
    """Try to extract the year from the first page header."""
    try:
        text = pdf.pages[0].extract_text() or ""
        match = re.search(r"\b(20\d{2})\b", text)
        if match:
            return int(match.group(1))
    except Exception:
        pass
    return datetime.now().year


def parse_pdf_extrato(content: bytes) -> list[dict]:
    transactions: list[dict] = []

    with pdfplumber.open(io.BytesIO(content)) as pdf:
        year = _detect_year(pdf)
        in_section = False
        current_date = None

        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue

                if _SECTION_START.search(line):
                    in_section = True
                    continue

                if in_section and _SECTION_END.search(line):
                    in_section = False
                    continue

                if not in_section:
                    continue

                lower = line.lower()
                if any(lower.startswith(kw) for kw in _SKIP_KEYWORDS):
                    continue

                # Strip sidebar/footer text that pdfplumber sometimes merges with transactions
                line = _SIDEBAR_PREFIX.sub("", line).strip()
                if not line:
                    continue

                # Extract leading date if present
                date_match = _DATE_PREFIX.match(line)
                if date_match:
                    day, month = date_match.group(1).split("/")
                    try:
                        current_date = datetime(year, int(month), int(day)).date()
                    except ValueError:
                        pass
                    line = line[date_match.end():].strip()

                if current_date is None:
                    continue

                # Re-check skip keywords after stripping the date prefix
                if any(line.lower().startswith(kw) for kw in _SKIP_KEYWORDS):
                    continue

                # Extract amount(s) from end of line
                two = _TWO_AMOUNTS.search(line)
                one = _ONE_AMOUNT.search(line)

                if two:
                    amount_raw = two.group(1)
                    desc = line[: two.start()].strip()
                elif one:
                    amount_raw = one.group(1)
                    desc = line[: one.start()].strip()
                else:
                    continue

                if not desc or not amount_raw:
                    continue

                is_debit = amount_raw.endswith("-")
                amount   = _to_float(amount_raw)

                transactions.append({
                    "transaction_date": current_date.isoformat(),
                    "description":      desc,
                    "amount":           amount,
                    "type":             "expense" if is_debit else "income",
                    "source":           "drive_pdf",
                })

    logger.info("PDF extrato: %d transações extraídas", len(transactions))
    return transactions
