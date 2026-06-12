import logging

from extract import (
    extract_all_indicators,
    extract_countries,
)

from transform import (
    transform_countries,
    transform_indicators,
    transform_facts,
)

from load import load_all


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)

logger = logging.getLogger(__name__)


# ============================================================
# EXTRACTION
# ============================================================

def extract_data() -> tuple[list[dict], dict]:
    """
    Executa toda a etapa de extração.
    """

    logger.info("Iniciando extração.")

    countries = extract_countries()

    indicators_payload = extract_all_indicators()

    logger.info("Extração concluída.")

    return countries, indicators_payload


# ============================================================
# TRANSFORMATION
# ============================================================

def transform_data(
    raw_countries: list[dict],
    indicators_payload: dict,
) -> tuple[list[dict], list[dict], list[dict]]:
    """
    Executa todas as transformações.
    """

    logger.info("Iniciando transformação.")

    countries = transform_countries(
        raw_countries
    )

    indicators = transform_indicators(
        indicators_payload
    )

    facts = transform_facts(
        indicators_payload=indicators_payload,
        valid_country_codes={
            row["iso2_code"]
            for row in countries
        },
    )

    logger.info(
        "Transformação concluída. "
        "Countries=%s | Indicators=%s | Facts=%s",
        len(countries),
        len(indicators),
        len(facts),
    )

    return countries, indicators, facts


# ============================================================
# LOAD
# ============================================================

def load_data(
    countries: list[dict],
    indicators: list[dict],
    facts: list[dict],
) -> None:
    """
    Executa a carga no banco.
    """

    logger.info("Iniciando carga.")

    load_all(
        countries=countries,
        indicators=indicators,
        facts=facts,
    )

    logger.info("Carga concluída.")


# ============================================================
# ETL
# ============================================================

def run_etl() -> None:
    """
    Orquestra o pipeline completo.
    """

    logger.info("=" * 60)
    logger.info("Iniciando pipeline ETL World Bank")
    logger.info("=" * 60)

    try:

        raw_countries, indicators_payload = (
            extract_data()
        )

        countries, indicators, facts = (
            transform_data(
                raw_countries,
                indicators_payload,
            )
        )

        load_data(
            countries,
            indicators,
            facts,
        )

        logger.info("=" * 60)
        logger.info("Pipeline finalizado com sucesso")
        logger.info("=" * 60)

    except Exception as exc:

        logger.exception(
            "Falha durante a execução do pipeline: %s",
            exc,
        )

        raise


# ============================================================
# ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    run_etl()