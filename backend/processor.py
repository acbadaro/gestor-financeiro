"""
Pipeline principal: Google Drive → parser → IA → Supabase.
Chamado pelo scheduler a cada 12 horas.
"""

import asyncio
import logging

from ai import categorize_transaction
from config import GOOGLE_DRIVE_FOLDER_ID
from database import get_db
from drive.auth import get_drive_service
from drive.monitor import download_file, list_new_files
from drive.parsers.pdf_extrato import parse_pdf_extrato
from drive.parsers.xlsx_fatura import parse_xlsx_fatura

logger = logging.getLogger(__name__)


def _get_processed_ids() -> set:
    res = get_db().table("drive_processed_files").select("file_id").execute()
    return {row["file_id"] for row in res.data}


def _mark_processed(file_id, file_name, file_type, tx_count, status="success", error=None):
    get_db().table("drive_processed_files").upsert({
        "file_id":             file_id,
        "file_name":           file_name,
        "file_type":           file_type,
        "transactions_count":  tx_count,
        "status":              status,
        "error_message":       error,
    }).execute()


def _get_admin_id() -> str | None:
    res = get_db().table("users").select("id").eq("role", "admin").eq("is_active", True).limit(1).execute()
    return res.data[0]["id"] if res.data else None


def _get_categories() -> list[dict]:
    return get_db().table("categories").select("id, name, parent_id, type, classification").eq("is_active", True).execute().data


async def process_new_files():
    if not GOOGLE_DRIVE_FOLDER_ID:
        logger.warning("GOOGLE_DRIVE_FOLDER_ID não configurado — pulando verificação do Drive")
        return

    try:
        service = get_drive_service()
    except Exception as e:
        logger.error("Falha ao conectar ao Google Drive: %s", e)
        return

    processed_ids = _get_processed_ids()
    new_files     = list_new_files(service, GOOGLE_DRIVE_FOLDER_ID, processed_ids)

    if not new_files:
        return

    admin_id = _get_admin_id()
    if not admin_id:
        logger.error("Nenhum usuário admin encontrado — não é possível importar transações")
        return

    categories = _get_categories()

    for file in new_files:
        file_id   = file["id"]
        file_name = file["name"]
        mime      = file.get("mimeType", "")

        logger.info("Processando: %s", file_name)

        try:
            content = download_file(service, file_id, mime)

            is_pdf   = "pdf" in mime or file_name.lower().endswith(".pdf")
            is_xlsx  = "spreadsheet" in mime or file_name.lower().endswith((".xlsx", ".xls"))

            if is_pdf:
                transactions = parse_pdf_extrato(content)
                file_type    = "pdf_extrato"
            elif is_xlsx:
                transactions = parse_xlsx_fatura(content)
                file_type    = "xlsx_fatura"
            else:
                logger.warning("Tipo de arquivo não suportado: %s (%s)", file_name, mime)
                continue

            saved = 0
            db = get_db()
            for tx in transactions:
                try:
                    try:
                        cat = categorize_transaction(tx["description"], tx["type"], categories)
                        await asyncio.sleep(1.5)
                    except Exception as e:
                        logger.warning("Categorização falhou para '%s': %s", tx["description"], e)
                        cat = {"category_id": None, "classification": "controllable"}
                    db.table("transactions").insert({
                        "user_id":          admin_id,
                        "category_id":      cat.get("category_id"),
                        "description":      tx["description"],
                        "amount":           tx["amount"],
                        "type":             tx["type"],
                        "classification":   cat.get("classification"),
                        "transaction_date": tx["transaction_date"],
                        "is_recurring":     False,
                        "source":           tx["source"],
                        "is_confirmed":     False,
                    }).execute()
                    saved += 1
                except Exception as e:
                    logger.error("Erro ao salvar '%s': %s", tx["description"], e)

            _mark_processed(file_id, file_name, file_type, saved)
            logger.info("Concluído: %s — %d transação(ões) salva(s)", file_name, saved)

        except Exception as e:
            logger.error("Falha ao processar %s: %s", file_name, e)
            _mark_processed(file_id, file_name, "unknown", 0, "error", str(e))
