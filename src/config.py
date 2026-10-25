import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    data_dir: Path = BASE_DIR / "data"
    raw_data_dir: Path = BASE_DIR / "data" / "raw"
    processed_data_dir: Path = BASE_DIR / "data" / "processed"
    source_url: str = "https://data.humdata.org/dataset/wfp-food-prices-for-kenya/download/wfp_food_prices_ken.csv"
    database_url: str = ""

    def get_database_url(self) -> str:
        if self.database_url:
            return self._normalize_db_url(self.database_url)

        env_db_url = os.getenv("DATABASE_URL")
        if env_db_url:
            return self._normalize_db_url(env_db_url)

        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD", "")
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME")

        if db_user and db_name:
            return f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

        db_path = (BASE_DIR / "kenya_food_prices.db").as_posix()
        return f"sqlite:///{db_path}"

    @staticmethod
    def _normalize_db_url(url: str) -> str:
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url


settings = Settings()
