from pathlib import Path

from drain3 import TemplateMiner
from drain3.file_persistence import FilePersistence
from drain3.template_miner_config import TemplateMinerConfig

from logtriage.ports.clusterer import ClusterResult, Clusterer


class Drain3Clusterer(Clusterer):
    """Single owner of Drain3 state. Only the worker thread may call add_log_message."""

    def __init__(self, config_path: str, persistence_path: str):
        Path(persistence_path).parent.mkdir(parents=True, exist_ok=True)
        miner_config = TemplateMinerConfig()
        miner_config.load(config_path)
        persistence = FilePersistence(persistence_path)
        self._miner = TemplateMiner(persistence_handler=persistence, config=miner_config)

    def add_log_message(self, message: str) -> ClusterResult:
        result = self._miner.add_log_message(message)
        return ClusterResult(
            change_type=result["change_type"],
            cluster_id=result["cluster_id"],
            cluster_size=result["cluster_size"],
            template_mined=result["template_mined"],
            cluster_count=result["cluster_count"],
        )

    def save_state(self) -> None:
        self._miner.save_state("shutdown")

    def known_cluster_ids(self) -> set[int]:
        return {c.cluster_id for c in self._miner.drain.clusters}
