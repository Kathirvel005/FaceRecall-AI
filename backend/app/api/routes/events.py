from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.database.connection import get_db
from backend.app.database.repositories import RecognitionEventRepository
from backend.app.schemas.recognition import RecognitionEventResponse

router = APIRouter(prefix="/events", tags=["Recognition Events Log"])

@router.get("", response_model=List[RecognitionEventResponse])
async def list_events(
    limit: int = Query(default=100, le=500),
    db: AsyncSession = Depends(get_db)
):
    events = await RecognitionEventRepository.get_recent(db, limit=limit)
    return [
        RecognitionEventResponse(
            id=e.id,
            person_id=e.person_id,
            student_id=e.person.student_id if e.person else None,
            name=e.person.name if e.person else "UNKNOWN",
            track_id=e.track_id,
            status=e.status,
            similarity=e.similarity,
            quality=e.quality,
            camera_id=e.camera_id,
            bbox=e.bbox,
            timestamp=e.timestamp
        )
        for e in events
    ]
