from typing import List, Optional, Dict, Any
from sqlalchemy import select, update, delete, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.person import Person, FaceSample
from backend.app.models.recognition_event import RecognitionEvent, Camera
from backend.app.schemas.person import PersonCreate, PersonUpdate
from backend.app.schemas.camera import CameraCreate

class PersonRepository:
    @staticmethod
    async def create(db: AsyncSession, obj_in: PersonCreate) -> Person:
        person = Person(
            student_id=obj_in.student_id,
            name=obj_in.name,
            department=obj_in.department,
            class_name=obj_in.class_name,
            email=obj_in.email,
            profile_image=obj_in.profile_image,
            active=obj_in.active
        )
        db.add(person)
        await db.commit()
        await db.refresh(person)
        return person

    @staticmethod
    async def get_by_id(db: AsyncSession, person_id: int) -> Optional[Person]:
        stmt = select(Person).options(selectinload(Person.samples)).where(Person.id == person_id)
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def get_by_student_id(db: AsyncSession, student_id: str) -> Optional[Person]:
        stmt = select(Person).options(selectinload(Person.samples)).where(Person.student_id == student_id)
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def get_all(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None
    ) -> List[Person]:
        stmt = select(Person).options(selectinload(Person.samples)).order_by(desc(Person.created_at))
        if search:
            stmt = stmt.where(
                (Person.name.ilike(f"%{search}%")) |
                (Person.student_id.ilike(f"%{search}%")) |
                (Person.department.ilike(f"%{search}%"))
            )
        stmt = stmt.offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def update(db: AsyncSession, person_id: int, obj_in: PersonUpdate) -> Optional[Person]:
        person = await PersonRepository.get_by_id(db, person_id)
        if not person:
            return None

        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(person, field, value)

        await db.commit()
        await db.refresh(person)
        return person

    @staticmethod
    async def delete(db: AsyncSession, person_id: int) -> bool:
        person = await PersonRepository.get_by_id(db, person_id)
        if not person:
            return False
        await db.delete(person)
        await db.commit()
        return True

    @staticmethod
    async def add_sample(
        db: AsyncSession,
        person_id: int,
        image_path: str,
        quality_score: float,
        embedding_ref: Optional[str] = None
    ) -> FaceSample:
        sample = FaceSample(
            person_id=person_id,
            image_path=image_path,
            embedding_reference=embedding_ref,
            quality_score=quality_score
        )
        db.add(sample)
        await db.commit()
        await db.refresh(sample)
        return sample


class RecognitionEventRepository:
    @staticmethod
    async def log_event(
        db: AsyncSession,
        track_id: int,
        status: str,
        similarity: float,
        quality: float,
        camera_id: str,
        person_id: Optional[int] = None,
        bbox: Optional[str] = None
    ) -> RecognitionEvent:
        event = RecognitionEvent(
            person_id=person_id,
            track_id=track_id,
            status=status,
            similarity=similarity,
            quality=quality,
            camera_id=camera_id,
            bbox=bbox
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)
        return event

    @staticmethod
    async def get_recent(db: AsyncSession, limit: int = 50) -> List[RecognitionEvent]:
        stmt = (
            select(RecognitionEvent)
            .options(selectinload(RecognitionEvent.person))
            .order_by(desc(RecognitionEvent.timestamp))
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_statistics(db: AsyncSession) -> Dict[str, Any]:
        total_persons = await db.scalar(select(func.count(Person.id)))
        total_samples = await db.scalar(select(func.count(FaceSample.id)))
        total_events = await db.scalar(select(func.count(RecognitionEvent.id)))
        known_events = await db.scalar(select(func.count(RecognitionEvent.id)).where(RecognitionEvent.status == "KNOWN"))
        unknown_events = await db.scalar(select(func.count(RecognitionEvent.id)).where(RecognitionEvent.status == "UNKNOWN"))

        return {
            "registered_persons": total_persons or 0,
            "face_samples": total_samples or 0,
            "total_events": total_events or 0,
            "known_events": known_events or 0,
            "unknown_events": unknown_events or 0
        }


class CameraRepository:
    @staticmethod
    async def get_all(db: AsyncSession) -> List[Camera]:
        result = await db.execute(select(Camera))
        return list(result.scalars().all())

    @staticmethod
    async def upsert(db: AsyncSession, obj_in: CameraCreate) -> Camera:
        cam = await db.get(Camera, obj_in.id)
        if not cam:
            cam = Camera(
                id=obj_in.id,
                name=obj_in.name,
                source=obj_in.source,
                resolution=obj_in.resolution,
                fps=obj_in.fps,
                is_active=obj_in.is_active,
                status="DISCONNECTED"
            )
            db.add(cam)
        else:
            cam.name = obj_in.name
            cam.source = obj_in.source
            cam.resolution = obj_in.resolution
            cam.fps = obj_in.fps
            cam.is_active = obj_in.is_active

        await db.commit()
        await db.refresh(cam)
        return cam
