"""
Recategorização em lote das transações existentes.

Uso local:
  python recategorize.py           # apenas sem categoria
  python recategorize.py --all     # todas (sobrescreve categorias existentes)
"""
import logging
import sys
import time

from dotenv import load_dotenv

load_dotenv()

from ai import categorize_transaction
from database import get_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def run(only_uncategorized: bool = True) -> dict:
    db = get_db()

    categories = (
        db.table("categories")
        .select("id, name, parent_id, type, classification")
        .eq("is_active", True)
        .execute()
        .data
    )
    logger.info("Categorias carregadas: %d", len(categories))

    q = db.table("transactions").select("id, description, type")
    if only_uncategorized:
        q = q.is_("category_id", "null")
    transactions = q.execute().data

    total = len(transactions)
    logger.info("Transações a processar: %d", total)

    success = 0
    failed  = 0

    for i, tx in enumerate(transactions, 1):
        try:
            cat = categorize_transaction(tx["description"], tx["type"], categories)
            db.table("transactions").update({
                "category_id":   cat["category_id"],
                "classification": cat["classification"],
            }).eq("id", tx["id"]).execute()
            logger.info("[%d/%d] ✓ %s", i, total, tx["description"][:60])
            success += 1
        except Exception as e:
            logger.warning("[%d/%d] ✗ %s — %s", i, total, tx["description"][:50], e)
            failed += 1
        time.sleep(1.5)

    result = {"total": total, "success": success, "failed": failed}
    logger.info("Concluído: %s", result)
    return result


if __name__ == "__main__":
    only_uncategorized = "--all" not in sys.argv
    if not only_uncategorized:
        logger.info("Modo --all: recategorizando TODAS as transações")
    run(only_uncategorized)
