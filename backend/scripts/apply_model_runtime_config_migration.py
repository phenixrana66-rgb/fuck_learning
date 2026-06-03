from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import make_url


REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = REPO_ROOT / "docs" / "migrations" / "20260604_model_runtime_configs.sql"
LEGACY_TABLE = "qa_runtime_configs"
NEW_TABLES = ("model_runtime_configs", "student_qa_retrieval_runtime_configs")

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.common.db import get_database_url, get_engine  # noqa: E402


def main() -> int:
    sql = MIGRATION_PATH.read_text(encoding="utf-8")
    statements = split_sql_statements(sql)
    engine = get_engine()
    skipped_legacy_copy = 0
    executed = 0

    print(f"Migration: {MIGRATION_PATH.relative_to(REPO_ROOT)}")
    print(f"Database: {mask_database_url(get_database_url())}")

    with engine.begin() as conn:
        legacy_table_exists = table_exists(conn, LEGACY_TABLE)
        legacy_source_rows = count_legacy_source_rows(conn) if legacy_table_exists else None
        for statement in statements:
            if not legacy_table_exists and references_legacy_table(statement):
                skipped_legacy_copy += 1
                continue
            conn.exec_driver_sql(statement)
            executed += 1

        counts = {table: count_rows(conn, table) for table in NEW_TABLES if table_exists(conn, table)}

    print(f"Executed statements: {executed}")
    if legacy_source_rows is not None:
        print(f"{LEGACY_TABLE} source rows for student_qa_global: {legacy_source_rows}")
    if skipped_legacy_copy:
        print(f"Skipped legacy copy statements: {skipped_legacy_copy} ({LEGACY_TABLE} does not exist)")
    for table, count in counts.items():
        print(f"{table}: {count} row(s)")
    print("Done.")
    return 0


def split_sql_statements(sql: str) -> list[str]:
    statements: list[str] = []
    chars: list[str] = []
    in_single_quote = False
    in_double_quote = False
    in_backtick = False
    in_line_comment = False
    in_block_comment = False
    i = 0

    while i < len(sql):
        char = sql[i]
        next_char = sql[i + 1] if i + 1 < len(sql) else ""
        prev_char = sql[i - 1] if i > 0 else ""

        if in_line_comment:
            chars.append(char)
            if char == "\n":
                in_line_comment = False
            i += 1
            continue

        if in_block_comment:
            chars.append(char)
            if char == "*" and next_char == "/":
                chars.append(next_char)
                in_block_comment = False
                i += 2
            else:
                i += 1
            continue

        if not in_single_quote and not in_double_quote and not in_backtick:
            if char == "-" and next_char == "-":
                chars.append(char)
                chars.append(next_char)
                in_line_comment = True
                i += 2
                continue
            if char == "/" and next_char == "*":
                chars.append(char)
                chars.append(next_char)
                in_block_comment = True
                i += 2
                continue
            if char == ";":
                statement = "".join(chars).strip()
                if has_executable_sql(statement):
                    statements.append(statement)
                chars = []
                i += 1
                continue

        if char == "'" and not in_double_quote and not in_backtick and prev_char != "\\":
            in_single_quote = not in_single_quote
        elif char == '"' and not in_single_quote and not in_backtick and prev_char != "\\":
            in_double_quote = not in_double_quote
        elif char == "`" and not in_single_quote and not in_double_quote:
            in_backtick = not in_backtick

        chars.append(char)
        i += 1

    statement = "".join(chars).strip()
    if has_executable_sql(statement):
        statements.append(statement)
    return statements


def has_executable_sql(statement: str) -> bool:
    lines = [line for line in statement.splitlines() if not line.strip().startswith("--")]
    return bool("\n".join(lines).strip())


def references_legacy_table(statement: str) -> bool:
    return f"`{LEGACY_TABLE}`" in statement or LEGACY_TABLE in statement


def table_exists(conn, table_name: str) -> bool:
    if conn.dialect.name == "sqlite":
        result = conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        )
    else:
        result = conn.exec_driver_sql("SHOW TABLES LIKE %s", (table_name,))
    return result.first() is not None


def count_rows(conn, table_name: str) -> int:
    result = conn.exec_driver_sql(f"SELECT COUNT(*) FROM `{table_name}`")
    return int(result.scalar_one())


def count_legacy_source_rows(conn) -> int:
    result = conn.exec_driver_sql(
        f"SELECT COUNT(*) FROM `{LEGACY_TABLE}` WHERE `scope_key` = %s",
        ("student_qa_global",),
    )
    return int(result.scalar_one())


def mask_database_url(database_url: str) -> str:
    return make_url(database_url).render_as_string(hide_password=True)


if __name__ == "__main__":
    raise SystemExit(main())
