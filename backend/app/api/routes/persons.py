import base64
import os
from pathlib import Path
from typing import List, Optional
import cv2
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.core.logging import logger
from backend.app.database.connection import get_db
from backend.app.database.repositories import PersonRepository
from backend.app.schemas.person import (
    PersonCreate, PersonUpdate, PersonResponse,
    EnrollmentRequest
)
from backend.app.ml.detector import SCRFDDetector
from backend.app.ml.recognizer import face_recognizer
from backend.app.ml.alignment import align_face_5pts
from backend.app.ml.vector_store import vector_store
from backend.app.services.quality_service import quality_analyzer

router = APIRouter(prefix="/persons", tags=["Person Management & Enrollment"])

detector = SCRFDDetector()

@router.get("", response_model=List[PersonResponse])
async def list_persons(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    persons = await PersonRepository.get_all(db, skip=skip, limit=limit, search=search)
    responses = []
    for p in persons:
        resp = PersonResponse(
            id=p.id,
            student_id=p.student_id,
            name=p.name,
            department=p.department,
            class_name=p.class_name,
            email=p.email,
            profile_image=p.profile_image,
            active=p.active,
            created_at=p.created_at,
            updated_at=p.updated_at,
            samples_count=len(p.samples),
            samples=[
                {
                    "id": s.id,
                    "image_path": s.image_path,
                    "quality_score": s.quality_score,
                    "created_at": s.created_at
                }
                for s in p.samples
            ]
        )
        responses.append(resp)
    return responses

@router.post("", response_model=PersonResponse)
async def create_person(
    person_in: PersonCreate,
    db: AsyncSession = Depends(get_db)
):
    existing = await PersonRepository.get_by_student_id(db, person_in.student_id)
    if existing:
        raise HTTPException(status_code=400, detail=f"Student ID '{person_in.student_id}' already registered.")

    person = await PersonRepository.create(db, person_in)
    return PersonResponse(
        id=person.id,
        student_id=person.student_id,
        name=person.name,
        department=person.department,
        class_name=person.class_name,
        email=person.email,
        profile_image=person.profile_image,
        active=person.active,
        created_at=person.created_at,
        updated_at=person.updated_at,
        samples_count=0,
        samples=[]
    )

@router.get("/{id}", response_model=PersonResponse)
async def get_person(id: int, db: AsyncSession = Depends(get_db)):
    person = await PersonRepository.get_by_id(db, id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    return PersonResponse(
        id=person.id,
        student_id=person.student_id,
        name=person.name,
        department=person.department,
        class_name=person.class_name,
        email=person.email,
        profile_image=person.profile_image,
        active=person.active,
        created_at=person.created_at,
        updated_at=person.updated_at,
        samples_count=len(person.samples),
        samples=[
            {
                "id": s.id,
                "image_path": s.image_path,
                "quality_score": s.quality_score,
                "created_at": s.created_at
            }
            for s in person.samples
        ]
    )

@router.put("/{id}", response_model=PersonResponse)
async def update_person(id: int, update_in: PersonUpdate, db: AsyncSession = Depends(get_db)):
    person = await PersonRepository.update(db, id, update_in)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    return await get_person(id, db)

@router.delete("/{id}")
async def delete_person(id: int, db: AsyncSession = Depends(get_db)):
    person = await PersonRepository.get_by_id(db, id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    # Remove embeddings from FAISS
    vector_store.remove_by_student_id(person.student_id)

    # Delete sample images from disk
    for sample in person.samples:
        try:
            p = Path(sample.image_path)
            if p.exists():
                p.unlink()
        except Exception as e:
            logger.warning(f"Could not delete sample file {sample.image_path}: {e}")

    await PersonRepository.delete(db, id)
    return {"success": True, "message": f"Person '{person.name}' and biometric vectors deleted successfully."}

async def _process_single_image(
    img: np.ndarray,
    person,
    idx: int,
    person_dir: Path,
    db: AsyncSession
) -> tuple[bool, Optional[str]]:
    """Helper to detect, validate quality, align, embed, and store a single enrollment sample."""
    try:
        if img is None:
            return False, f"Sample {idx+1}: Corrupt or unreadable image data"

        # 1. Detection
        faces = detector.detect(img)
        if len(faces) == 0:
            return False, f"Sample {idx+1}: No face detected"
        elif len(faces) > 1:
            return False, f"Sample {idx+1}: Multiple faces detected (must contain exactly 1 face)"

        face = faces[0]

        # 2. Quality Check
        quality = quality_analyzer.analyze(img, face.bbox, face.landmarks, face.confidence)
        if not quality.is_valid:
            return False, f"Sample {idx+1}: Quality rejected ({quality.reason})"

        # 3. Alignment
        aligned = align_face_5pts(img, face.landmarks)

        # 4. Save aligned face crop
        sample_filename = f"{person.student_id}_{int(os.times().system*1000)}_{idx}.jpg"
        sample_path = person_dir / sample_filename
        cv2.imwrite(str(sample_path), aligned)

        # 5. ArcFace Embedding
        emb = face_recognizer.extract_embedding(aligned)

        # 6. Store in FAISS
        vector_store.add_embedding(
            emb,
            {
                "student_id": person.student_id,
                "person_id": person.student_id,
                "name": person.name,
                "department": person.department or "",
                "class_name": person.class_name or "",
                "quality": quality.quality_score
            }
        )

        # 7. Store FaceSample in DB
        await PersonRepository.add_sample(
            db=db,
            person_id=person.id,
            image_path=str(sample_path),
            quality_score=quality.quality_score,
            embedding_ref=person.student_id
        )

        # If first accepted sample and person has no profile image, set it
        if not person.profile_image:
            person.profile_image = f"/data/faces/{person.student_id}/{sample_filename}"
            await db.commit()

        return True, None

    except Exception as e:
        logger.error(f"Error processing enrollment sample {idx}: {e}")
        return False, f"Sample {idx+1}: Processing error ({str(e)})"


@router.post("/{id}/enroll")
async def enroll_person_samples(
    id: int,
    enrollment: EnrollmentRequest,
    db: AsyncSession = Depends(get_db)
):
    person = await PersonRepository.get_by_id(db, id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    accepted_samples = 0
    rejected_samples = 0
    rejection_reasons = []

    person_dir = settings.FACES_DIR / person.student_id
    person_dir.mkdir(parents=True, exist_ok=True)

    for idx, sample in enumerate(enrollment.samples):
        try:
            # Decode base64
            img_data = sample.image_base64
            if "," in img_data:
                img_data = img_data.split(",")[1]
            img_bytes = base64.b64decode(img_data)
            np_arr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            ok, err = await _process_single_image(img, person, idx, person_dir, db)
            if ok:
                accepted_samples += 1
            else:
                rejected_samples += 1
                if err:
                    rejection_reasons.append(err)

        except Exception as e:
            logger.error(f"Base64 decode error for sample {idx}: {e}")
            rejected_samples += 1
            rejection_reasons.append(f"Sample {idx+1}: Base64 decoding failed")

    return {
        "student_id": person.student_id,
        "name": person.name,
        "total_submitted": len(enrollment.samples),
        "accepted": accepted_samples,
        "rejected": rejected_samples,
        "rejection_reasons": rejection_reasons,
        "total_registered_embeddings": vector_store.count()
    }


@router.post("/{id}/enroll-files")
async def enroll_person_files(
    id: int,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Enroll a person by uploading raw image files directly (JPG, PNG, WebP)."""
    person = await PersonRepository.get_by_id(db, id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    accepted_samples = 0
    rejected_samples = 0
    rejection_reasons = []

    person_dir = settings.FACES_DIR / person.student_id
    person_dir.mkdir(parents=True, exist_ok=True)

    for idx, file in enumerate(files):
        try:
            content = await file.read()
            np_arr = np.frombuffer(content, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            ok, err = await _process_single_image(img, person, idx, person_dir, db)
            if ok:
                accepted_samples += 1
            else:
                rejected_samples += 1
                if err:
                    rejection_reasons.append(f"{file.filename or f'File {idx+1}'}: {err}")

        except Exception as e:
            logger.error(f"File upload error for {file.filename}: {e}")
            rejected_samples += 1
            rejection_reasons.append(f"{file.filename or f'File {idx+1}'}: Upload read failed ({str(e)})")

    return {
        "student_id": person.student_id,
        "name": person.name,
        "total_submitted": len(files),
        "accepted": accepted_samples,
        "rejected": rejected_samples,
        "rejection_reasons": rejection_reasons,
        "total_registered_embeddings": vector_store.count()
    }

