from fastapi import APIRouter, HTTPException, Request

from logtriage.models import CategorizeRequest, Severity, Status, TemplateOut

router = APIRouter(prefix="/api/templates")


@router.get("", response_model=list[TemplateOut])
def list_templates(
    request: Request,
    status: Status | None = None,
    severity: Severity | None = None,
    muted: bool | None = None,
) -> list[TemplateOut]:
    store = request.app.state.template_store
    return store.list(status=status, severity=severity, muted=muted)


@router.get("/{cluster_id}", response_model=TemplateOut)
def get_template(request: Request, cluster_id: int) -> TemplateOut:
    store = request.app.state.template_store
    row = store.get(cluster_id)
    if row is None:
        raise HTTPException(status_code=404, detail="template not found")
    return row


@router.post("/{cluster_id}/categorize", response_model=TemplateOut)
def categorize_template(request: Request, cluster_id: int, body: CategorizeRequest) -> TemplateOut:
    store = request.app.state.template_store
    row = store.categorize(cluster_id, body.severity, body.muted, body.actor)
    if row is None:
        raise HTTPException(status_code=404, detail="template not found")
    metrics = request.app.state.metrics
    metrics.set_templates_pending(store.count_pending())
    return row
