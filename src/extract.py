import logging
import time
from typing import Any
import requests
from config import MANDATORY_INDICATORS, settings
logger = logging.getLogger(__name__)


def request_json(session: requests.Session, endpoint: str, params: dict[str, Any]) -> list[Any]:
    # monta a url completa do endpoint
    url = f"{settings.world_bank_base_url}{endpoint}"

    # tenta a requisicao varias vezes em caso de falha
    for attempt in range(1, settings.retry_attempts + 1):
        try:
            response = session.get(url, params=params, timeout=settings.request_timeout)
            response.raise_for_status()

            payload = response.json()

            # valida o formato esperado da resposta da api
            if not isinstance(payload, list) or len(payload) != 2:
                raise ValueError("Resposta da API em formato inesperado.")

            return payload

        except (requests.RequestException, ValueError) as exc:
            if attempt >= settings.retry_attempts:
                raise RuntimeError(f"Falha ao acessar endpoint {endpoint}") from exc

            # aplica backoff exponencial entre as tentativas
            wait_seconds = settings.backoff_seconds * (2 ** (attempt - 1))

            logger.warning(
                "Falha em %s tentativa %s/%s: %s. Tentando novamente em %.1fs.",
                endpoint,
                attempt,
                settings.retry_attempts,
                exc,
                wait_seconds,
            )

            time.sleep(wait_seconds)

    raise RuntimeError("Estado de retry inalcancavel.")


def extract_countries() -> list[dict[str, Any]]:
    page = 1
    all_rows: list[dict[str, Any]] = []

    with requests.Session() as session:
        # percorre todas as paginas do endpoint de paises
        while True:
            payload = request_json(
                session=session,
                endpoint="/country",
                params={
                    "format": "json",
                    "page": page,
                    "per_page": settings.countries_per_page,
                },
            )

            meta, rows = payload
            total_pages = int(meta.get("pages", 0))

            all_rows.extend(rows)

            logger.info(
                "Paises: pagina %s/%s, %s registros.",
                page,
                total_pages,
                len(rows),
            )

            if page >= total_pages:
                break

            page += 1

    logger.info("Extracao de paises concluida com %s registros.", len(all_rows))

    return all_rows


def extract_indicator(session: requests.Session, indicator_code: str) -> list[dict[str, Any]]:
    page = 1
    all_rows: list[dict[str, Any]] = []
    total_pages = 0

    # percorre todas as paginas do indicador atual
    while True:
        payload = request_json(
            session=session,
            endpoint=f"/country/all/indicator/{indicator_code}",
            params={
                "format": "json",
                "page": page,
                "per_page": settings.indicators_per_page,
                "mrv": settings.indicators_mrv,
            },
        )

        meta, rows = payload
        total_pages = int(meta.get("pages", 0))

        all_rows.extend(rows)

        logger.info(
            "Indicador %s: pagina %s/%s, %s registros.",
            indicator_code,
            page,
            total_pages,
            len(rows),
        )

        if page >= total_pages:
            break

        page += 1

    # registra o total extraido para o indicador
    logger.info(
        "Indicador %s concluido com %s paginas e %s registros.",
        indicator_code,
        total_pages,
        len(all_rows),
    )

    return all_rows


def extract_all_indicators() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}

    with requests.Session() as session:
        # extrai os cinco indicadores obrigatorios
        for code, metadata in MANDATORY_INDICATORS.items():
            rows = extract_indicator(
                session=session,
                indicator_code=code,
            )

            out[code] = {
                "metadata": metadata,
                "records": rows,
            }

    return out