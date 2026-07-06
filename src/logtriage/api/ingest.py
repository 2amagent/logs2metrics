import json

from fastapi import APIRouter, Request, Response

router = APIRouter()


@router.post("/ingest", status_code=202)
async def ingest(request: Request) -> Response:
    content_type = request.headers.get("content-type", "")
    body = await request.body()

    records: list[dict]
    if "ndjson" in content_type or (body and body.lstrip()[:1] not in (b"[", b"{")):
        records = [json.loads(line) for line in body.splitlines() if line.strip()]
    else:
        parsed = json.loads(body) if body else []
        records = parsed if isinstance(parsed, list) else [parsed]

    worker = request.app.state.worker
    metrics = request.app.state.metrics
    accepted = 0
    for record in records:
        if worker.enqueue(record):
            accepted += 1
            metrics.inc_ingested_total()
        else:
            return Response(status_code=503, content="queue full")

    return Response(status_code=202, content=json.dumps({"accepted": accepted}), media_type="application/json")
