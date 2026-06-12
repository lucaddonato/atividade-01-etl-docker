import logging
from typing import Any

from sqlalchemy import (
    CHAR,
    NUMERIC,
    SMALLINT,
    TIMESTAMP,
    Column,
    ForeignKey,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    func,
)

from sqlalchemy.dialects.postgresql import insert as pg_insert

from config import settings

logger = logging.getLogger(__name__)


# ============================================================
# METADATA
# ============================================================

metadata = MetaData()


# ============================================================
# COUNTRIES
# ============================================================

countries_table = Table(
    "countries",
    metadata,
    Column("iso2_code", CHAR(2), primary_key=True),
    Column("iso3_code", CHAR(3)),
    Column("name", String(100), nullable=False),
    Column("region", String(80)),
    Column("income_group", String(60)),
    Column("capital", String(80)),
    Column("longitude", NUMERIC(9, 4)),
    Column("latitude", NUMERIC(9, 4)),
    Column(
        "loaded_at",
        TIMESTAMP,
        server_default=func.now(),
    ),
)


# ============================================================
# INDICATORS
# ============================================================

indicators_table = Table(
    "indicators",
    metadata,
    Column(
        "indicator_code",
        String(40),
        primary_key=True,
    ),
    Column(
        "indicator_name",
        Text,
        nullable=False,
    ),
    Column(
        "unit",
        String(30),
    ),
)


# ============================================================
# WDI_FACTS
# ============================================================

wdi_facts_table = Table(
    "wdi_facts",
    metadata,
    Column(
        "iso2_code",
        CHAR(2),
        ForeignKey("countries.iso2_code"),
        primary_key=True,
    ),
    Column(
        "indicator_code",
        String(40),
        ForeignKey("indicators.indicator_code"),
        primary_key=True,
    ),
    Column(
        "year",
        SMALLINT,
        nullable=False,
        primary_key=True,
    ),
    Column(
        "value",
        NUMERIC(18, 4),
    ),
    Column(
        "loaded_at",
        TIMESTAMP,
        server_default=func.now(),
    ),
)


# ============================================================
# ENGINE
# ============================================================

engine = create_engine(
    settings.database_url,
    future=True,
    pool_pre_ping=True,
)


# ============================================================
# GENERIC UPSERT
# ============================================================

def execute_upsert(
    table: Table,
    rows: list[dict[str, Any]],
    conflict_columns: list[str],
    update_columns: list[str],
) -> int:
    """
    Executa upsert em lote utilizando PostgreSQL.
    """

    if not rows:
        return 0

    stmt = pg_insert(table).values(rows)

    update_dict = {
        column: getattr(stmt.excluded, column)
        for column in update_columns
    }

    if "loaded_at" in table.c:
        update_dict["loaded_at"] = func.now()

    stmt = stmt.on_conflict_do_update(
        index_elements=conflict_columns,
        set_=update_dict,
    )

    with engine.begin() as conn:
        conn.execute(stmt)

    logger.info(
        "Carga %s: %s linhas.",
        table.name,
        len(rows),
    )

    return len(rows)


# ============================================================
# COUNTRIES
# ============================================================

def upsert_countries(
    rows: list[dict[str, Any]],
) -> int:
    """
    Insere ou atualiza países.
    """

    return execute_upsert(
        table=countries_table,
        rows=rows,
        conflict_columns=[
            "iso2_code",
        ],
        update_columns=[
            "iso3_code",
            "name",
            "region",
            "income_group",
            "capital",
            "longitude",
            "latitude",
        ],
    )


# ============================================================
# INDICATORS
# ============================================================

def upsert_indicators(
    rows: list[dict[str, Any]],
) -> int:
    """
    Insere ou atualiza indicadores.
    """

    return execute_upsert(
        table=indicators_table,
        rows=rows,
        conflict_columns=[
            "indicator_code",
        ],
        update_columns=[
            "indicator_name",
            "unit",
        ],
    )


# ============================================================
# FACTS
# ============================================================

def upsert_facts(
    rows: list[dict[str, Any]],
) -> int:
    """
    Insere ou atualiza fatos.
    """

    return execute_upsert(
        table=wdi_facts_table,
        rows=rows,
        conflict_columns=[
            "iso2_code",
            "indicator_code",
            "year",
        ],
        update_columns=[
            "value",
        ],
    )


# ============================================================
# PIPELINE LOAD
# ============================================================

def load_all(
    countries: list[dict[str, Any]],
    indicators: list[dict[str, Any]],
    facts: list[dict[str, Any]],
) -> None:
    """
    Ordem obrigatória:
    countries -> indicators -> facts
    """

    upsert_countries(countries)

    upsert_indicators(indicators)

    upsert_facts(facts)

    logger.info(
        "Carga finalizada. Countries=%s | Indicators=%s | Facts=%s",
        len(countries),
        len(indicators),
        len(facts),
    )