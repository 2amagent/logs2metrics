from logtriage.adapters.drain3_clusterer import Drain3Clusterer
from logtriage.adapters.object_store_azure import AzureObjectStore
from logtriage.adapters.object_store_local import LocalObjectStore
from logtriage.adapters.object_store_null import NullObjectStore
from logtriage.adapters.object_store_s3 import S3ObjectStore
from logtriage.adapters.prometheus_metrics_sink import PrometheusMetricsSink
from logtriage.adapters.sqlite_template_store import SqliteTemplateStore
from logtriage.config import Settings
from logtriage.ports.clusterer import Clusterer
from logtriage.ports.metrics_sink import MetricsSink
from logtriage.ports.object_store import ObjectStore
from logtriage.ports.template_store import TemplateStore


def build_template_store(settings: Settings) -> TemplateStore:
    return SqliteTemplateStore(settings.db_path, sample_line_cap=settings.sample_line_cap)


def build_object_store(settings: Settings) -> ObjectStore:
    backend = settings.object_store_backend
    if backend == "none":
        return NullObjectStore()
    if backend == "local":
        return LocalObjectStore(settings.local.data_dir)
    if backend == "s3":
        return S3ObjectStore(
            bucket=settings.s3.bucket,
            endpoint_url=settings.s3.endpoint_url,
            region=settings.s3.region,
            access_key_id=settings.s3.access_key_id,
            secret_access_key=settings.s3.secret_access_key,
        )
    if backend == "azure":
        return AzureObjectStore()
    raise ValueError(f"Unknown object_store_backend: {backend!r}")


def build_metrics_sink(settings: Settings) -> MetricsSink:
    return PrometheusMetricsSink()


def build_clusterer(settings: Settings) -> Clusterer:
    return Drain3Clusterer(
        config_path=settings.drain3_config_path,
        persistence_path=settings.drain3_persistence_path,
    )
