from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import AnalysisResult
from app.schemas.schemas import AnalysisAlertsRequest, AnalysisProcessResponse, AnalysisResultRead
from app.services.processor import process_alerts

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/alerts", response_model=AnalysisProcessResponse)
async def receive_alerts(
    payload: AnalysisAlertsRequest,
    db: Session = Depends(get_db),
) -> AnalysisProcessResponse:
    result = await process_alerts(db, payload.alerts)
    return AnalysisProcessResponse(
        status="processed",
        processed_count=result["processed"],
        duplicate_count=result["duplicates"],
        incident_count=result["incidents"],
        failed_count=result["failed"],
    )


@router.post("/correlate", response_model=AnalysisProcessResponse)
async def correlate_alerts(
    payload: AnalysisAlertsRequest,
    db: Session = Depends(get_db),
) -> AnalysisProcessResponse:
    return await receive_alerts(payload, db)


@router.get("/incidents/{incident_id}", response_model=AnalysisResultRead)
def get_incident_analysis(
    incident_id: str,
    db: Session = Depends(get_db),
) -> AnalysisResult:
    result = (
        db.query(AnalysisResult)
        .filter(AnalysisResult.incident_id == incident_id)
        .order_by(AnalysisResult.created_at.desc())
        .first()
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis result not found")
    return result
