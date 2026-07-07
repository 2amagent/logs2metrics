from pathlib import Path
from typing import Literal

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class S3Config(BaseSettings):
    bucket: str = "logtriage"
    endpoint_url: str | None = None  # set for MinIO / non-AWS S3-compatible stores
    region: str = "us-east-1"
    access_key_id: str | None = None
    secret_access_key: str | None = None


class AzureConfig(BaseSettings):
    account_url: str | None = None
    container: str = "logtriage"
    connection_string: str | None = None


class LocalConfig(BaseSettings):
    data_dir: str = "./data/archive"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LOGTRIAGE_", env_nested_delimiter="__")

    # HTTP / process
    host: str = "0.0.0.0"
    port: int = 8000

    # logging
    log_level: str = "INFO"

    # ingest pipeline
    message_field: str = "log"
    queue_max_size: int = 10_000

    # sqlite
    db_path: str = "./data/logtriage.db"

    # drain3
    drain3_config_path: str = "./drain3.ini"
    drain3_persistence_path: str = "./data/drain3_state.bin"

    # template store
    sample_line_cap: int = 5

    # object storage — "none" disables archival entirely (no-op ObjectStore),
    # for deployments relying on their log transporter's own S3/blob output
    # instead of this service's per-line, cluster/severity-enriched archive.
    object_store_backend: Literal["none", "local", "s3", "azure"] = "none"
    local: LocalConfig = LocalConfig()
    s3: S3Config = S3Config()
    azure: AzureConfig = AzureConfig()

    # archival buffer flush thresholds
    flush_size_bytes: int = 1_000_000
    flush_interval_seconds: float = 30.0

    @classmethod
    def from_yaml(cls, path: str | Path | None) -> "Settings":
        """Load defaults from a YAML file (if present), then let env vars override."""
        data: dict = {}
        if path and Path(path).exists():
            with open(path) as f:
                data = yaml.safe_load(f) or {}
        return cls(**data)
