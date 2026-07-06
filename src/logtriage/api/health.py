from fastapi import APIRouter, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, generate_latest

router = APIRouter()


@router.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@router.get("/readyz")
def readyz(request: Request) -> Response:
    if not getattr(request.app.state, "ready", False):
        return Response(status_code=503, content="not ready")
    return Response(status_code=200, content="ready")


@router.get("/metrics")
def metrics(request: Request) -> Response:
    registry = getattr(request.app.state, "metrics_registry", REGISTRY)
    return Response(content=generate_latest(registry), media_type=CONTENT_TYPE_LATEST)
