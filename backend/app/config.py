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


def _validate_settings(s: Settings) -> None:
    """Fail fast with a clear error if required env vars are missing or invalid."""
    if not s.HOST_PROJECT_DIR:
        raise EnvironmentError(
            "HOST_PROJECT_DIR environment variable is not set. "
            "Set it to the absolute path of the project root on the host machine "
            "(e.g. HOST_PROJECT_DIR=/home/user/cicada). "
            "This is required so the backend can mount volumes into k6 containers."
        )
    if not os.path.isabs(s.HOST_PROJECT_DIR):
        raise EnvironmentError(
            f"HOST_PROJECT_DIR must be an absolute path, got: {s.HOST_PROJECT_DIR!r}. "
            "Example: HOST_PROJECT_DIR=/home/user/cicada"
        )
    if not os.path.isdir(s.HOST_PROJECT_DIR):
        raise EnvironmentError(
            f"HOST_PROJECT_DIR={s.HOST_PROJECT_DIR!r} does not exist or is not a directory. "
            "Ensure the path exists on the host machine before starting the application."
        )


settings = Settings()
_validate_settings(settings)
