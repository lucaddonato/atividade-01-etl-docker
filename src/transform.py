import logging
from typing import Any, Iterable
from config import settings
logger = logging.getLogger(__name__)


def clean_string(value: Any, *, title_case: bool = False) -> str | None:
    # aplica limpeza padrao para campos de texto
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    return text.title() if title_case else text


def to_int_safe(value: Any) -> int | None:
    # converte valores para inteiro de forma segura
    if value in (None, ""):
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def to_float_safe(value: Any) -> float | None:
    # converte valores para decimal de forma segura
    if value in (None, ""):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_income_group(
    group_id: str | None,
    group_name: str | None,
) -> str | None:
    # padroniza os grupos de renda exigidos pelo projeto
    normalized_id = clean_string(group_id)
    normalized_name = clean_string(group_name)

    if normalized_id == "LIC":
        return "Low income"

    if normalized_id in {"LMC", "UMC", "MIC"}:
        return "Middle income"

    if normalized_id == "HIC":
        return "High income"

    return normalized_name


def transform_countries(
    raw_countries: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    skipped_non_country = 0
    skipped_income = 0

    for country in raw_countries:
        iso2_code = clean_string(country.get("iso2Code"))

        region = clean_string(
            (country.get("region") or {}).get("value"),
            title_case=True,
        )

        # t1: remove agregados regionais e registros que nao sao paises
        if iso2_code is None or len(iso2_code) != 2 or region == "Aggregates":
            skipped_non_country += 1
            continue

        income_id = clean_string(
            (country.get("incomeLevel") or {}).get("id")
        )

        if income_id not in {"LIC", "MIC", "LMC", "UMC", "HIC"}:
            skipped_income += 1
            continue

        # t2 e t3: limpa textos e converte tipos dos campos
        rows.append(
            {
                "iso2_code": iso2_code,
                "iso3_code": clean_string(country.get("id")),
                "name": clean_string(country.get("name")),
                "region": region,
                "income_group": normalize_income_group(
                    income_id,
                    (country.get("incomeLevel") or {}).get("value"),
                ),
                "capital": clean_string(country.get("capitalCity")),
                "longitude": to_float_safe(country.get("longitude")),
                "latitude": to_float_safe(country.get("latitude")),
            }
        )

    logger.info(
        "Countries transformados: %s mantidos, %s nao-pais removidos, %s renda fora de escopo removidos.",
        len(rows),
        skipped_non_country,
        skipped_income,
    )

    return rows


def transform_indicators(
    indicators_payload: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    # monta a dimensao de indicadores obrigatorios
    rows: list[dict[str, Any]] = []

    for indicator_code, payload in indicators_payload.items():
        resolved_name = clean_string(payload["metadata"]["name"])

        for record in payload["records"]:
            # utiliza o nome retornado pela api quando disponivel
            name_from_api = clean_string(
                (record.get("indicator") or {}).get("value")
            )

            if name_from_api:
                resolved_name = name_from_api
                break

        rows.append(
            {
                "indicator_code": indicator_code,
                "indicator_name": clean_string(resolved_name),
                "unit": clean_string(payload["metadata"]["unit"]),
            }
        )

    logger.info(
        "Indicators transformados: %s linhas.",
        len(rows),
    )

    return rows


def transform_facts(
    indicators_payload: dict[str, dict[str, Any]],
    valid_country_codes: Iterable[str],
) -> list[dict[str, Any]]:
    allowed_iso2 = set(valid_country_codes)

    dedup: dict[tuple[str, str, int], dict[str, Any]] = {}

    duplicate_count = 0
    skipped_non_country = 0
    skipped_year = 0
    null_values = 0

    for indicator_code, payload in indicators_payload.items():
        for record in payload["records"]:
            iso2_code = clean_string(
                (record.get("country") or {}).get("id")
            )

            # t1: mantem apenas paises validos carregados na dimensao
            if (
                iso2_code is None
                or len(iso2_code) != 2
                or iso2_code not in allowed_iso2
            ):
                skipped_non_country += 1
                continue

            # t3: converte o ano para inteiro
            year = to_int_safe(record.get("date"))

            # t4: mantem apenas anos entre 2010 e o ano atual
            if (
                year is None
                or year < settings.start_year
                or year > settings.current_year
            ):
                skipped_year += 1
                continue

            value = to_float_safe(record.get("value"))

            if value is None:
                null_values += 1

            key = (
                iso2_code,
                indicator_code,
                year,
            )

            transformed = {
                "iso2_code": iso2_code,
                "indicator_code": indicator_code,
                "year": year,
                "value": value,
            }

            # t5: remove duplicatas mantendo o ultimo registro encontrado
            if key in dedup:
                duplicate_count += 1

            dedup[key] = transformed

    logger.info(
        "Facts transformados: %s mantidos, %s duplicatas, %s nao-pais, %s anos fora da janela, %s valores nulos.",
        len(dedup),
        duplicate_count,
        skipped_non_country,
        skipped_year,
        null_values,
    )

    return list(dedup.values())