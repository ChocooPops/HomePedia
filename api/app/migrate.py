"""Migrations : exécute les fichiers app/sql/00X_*.sql non encore appliqués, dans l'ordre."""

import logging
from pathlib import Path

from .db import db

logger = logging.getLogger("migrate")
SQL_DIR = Path(__file__).parent / "sql"


def split_sql_statements(sql: str) -> list[str]:
    """
    Découpe un script SQL en instructions, en ignorant les « ; » situés dans
    des chaînes ('...' avec échappement '') ou des commentaires « -- ».
    """
    statements: list[str] = []
    current = ""
    in_string = False
    i = 0
    while i < len(sql):
        ch = sql[i]
        if not in_string and ch == "-" and sql[i + 1 : i + 2] == "-":
            eol = sql.find("\n", i)
            i = len(sql) if eol == -1 else eol + 1
            current += "\n"
            continue
        if ch == "'":
            if in_string and sql[i + 1 : i + 2] == "'":
                current += "''"
                i += 2
                continue
            in_string = not in_string
        if ch == ";" and not in_string:
            if current.strip():
                statements.append(current.strip())
            current = ""
            i += 1
            continue
        current += ch
        i += 1
    if current.strip():
        statements.append(current.strip())
    return statements


def read_sql_file(file_name: str) -> list[str]:
    return split_sql_statements((SQL_DIR / file_name).read_text(encoding="utf-8"))


async def run_migrations() -> None:
    await db.execute(
        "CREATE TABLE IF NOT EXISTS schema_migration ("
        "name VARCHAR(120) NOT NULL PRIMARY KEY, applied_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3))"
    )
    applied = {r["name"] for r in await db.query("SELECT name FROM schema_migration")}
    for path in sorted(SQL_DIR.glob("*.sql")):
        if path.stem in applied:
            continue
        # Base créée avant le suivi des migrations (schéma initial déjà en place) : on enregistre sans rejouer.
        already = path.stem == "001_initial_schema" and await db.query(
            "SELECT 1 FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'data_source'"
        )
        if not already:
            logger.info("Migration %s", path.name)
            async with db.engine.begin() as conn:
                for statement in read_sql_file(path.name):
                    await conn.exec_driver_sql(statement)
        await db.execute("INSERT INTO schema_migration (name) VALUES (:name)", {"name": path.stem})
