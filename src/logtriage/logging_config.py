import logging


def configure_logging(level: str = "INFO") -> None:
    """Configure the root logger once at process startup.

    All modules use `logging.getLogger(__name__)` and inherit this
    configuration — don't add per-module handlers.
    """
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
