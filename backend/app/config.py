import os


class Settings:
    DATABASE_URL: str = os.environ.get(
        "DATABASE_URL", "postgresql+psycopg2://cicada:cicada@postgres:5432/cicada"
    )
    REDIS_URL: str = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    K6_IMAGE: str = os.environ.get("K6_IMAGE", "grafana/k6:latest")

    # path to project root is ON THE HOST required so the backend can mount to k6 containers using docker deamon
    HOST_PROJECT_DIR: str = os.environ.get("HOST_PROJECT_DIR", "")
    DATA_DIR: str = "/data"
    SCRIPTS_DIR: str = "/data/scripts"
    RESULTS_DIR: str = "/data/results"

    COMPOSE_PROJECT_NAME: str = os.environ.get("COMPOSE_PROJECT_NAME", "cicada")
    COMPOSE_NETWORK: str = f"{COMPOSE_PROJECT_NAME}_default"

    @property
    def host_scripts_dir(self) -> str:
        return f"{self.HOST_PROJECT_DIR}/data/scripts"

    @property
    def host_results_dir(self) -> str:
        return f"{self.HOST_PROJECT_DIR}/data/results"

settings = Settings()






