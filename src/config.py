import os
from dataclasses import dataclass
from datetime import datetime
from typing import TypeVar, Callable
from dotenv import load_dotenv
load_dotenv()

T = TypeVar("T")


MANDATORY_INDICATORS = {
    "NY.GDP.PCAP.KD": {
        "name": "PIB per capita (USD constante 2015)",
        "unit": "USD",
    },
    "SP.POP.TOTL": {
        "name": "Populacao total",
        "unit": "Pessoas",
    },
    "SH.XPD.CHEX.GD.ZS": {
        "name": "Gasto em saude (% do PIB)",
        "unit": "% PIB",
    },
    "SE.XPD.TOTL.GD.ZS": {
        "name": "Gasto em educacao (% do PIB)",
        "unit": "% PIB",
    },
    "EG.ELC.ACCS.ZS": {
        "name": "Acesso a eletricidade (% da populacao)",
        "unit": "%",
    },
}


def get_env(
    name: str,
    cast: Callable[[str], T] = str,
    default: T | None = None,
    required: bool = False,
) -> T:
    """
    Le uma variavel de ambiente com conversao de tipo.
    """

    value = os.getenv(name)

    if value is None or not value.strip():

        if required:
            raise ValueError(
                f"Variavel obrigatoria ausente: {name}"
            )

        return default

    return cast(value.strip())


@dataclass(frozen=True)
class Settings:
    world_bank_base_url: str

    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str

    countries_per_page: int
    indicators_per_page: int
    indicators_mrv: int

    request_timeout: int
    retry_attempts: int
    backoff_seconds: float

    start_year: int
    current_year: int

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://"
            f"{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}"
            f"/{self.db_name}"
        )


def load_settings() -> Settings:
    return Settings(
        world_bank_base_url=get_env(
            "WORLD_BANK_BASE_URL",
            required=True,
        ),

        db_host=get_env(
            "DB_HOST",
            required=True,
        ),

        db_port=get_env(
            "DB_PORT",
            cast=int,
            default=5432,
        ),

        db_name=get_env(
            "DB_NAME",
            required=True,
        ),

        db_user=get_env(
            "DB_USER",
            required=True,
        ),

        db_password=get_env(
            "DB_PASSWORD",
            required=True,
        ),

        countries_per_page=get_env(
            "COUNTRIES_PER_PAGE",
            cast=int,
            default=300,
        ),

        indicators_per_page=get_env(
            "INDICATORS_PER_PAGE",
            cast=int,
            default=100,
        ),

        indicators_mrv=get_env(
            "INDICATORS_MRV",
            cast=int,
            default=10,
        ),

        request_timeout=get_env(
            "REQUEST_TIMEOUT",
            cast=int,
            default=30,
        ),

        retry_attempts=get_env(
            "RETRY_ATTEMPTS",
            cast=int,
            default=3,
        ),

        backoff_seconds=get_env(
            "BACKOFF_SECONDS",
            cast=float,
            default=1.5,
        ),

        start_year=get_env(
            "START_YEAR",
            cast=int,
            default=2010,
        ),

        current_year=datetime.now().year,
    )


settings = load_settings()