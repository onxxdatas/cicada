from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Test
from app.schemas import TestCreate, TestOut

router = APIRouter(prefix="/api/tests", tags=["tests"])


@router.post("", response_model=TestOut)
def create_test(payload: TestCreate, db: Session = Depends(get_db)):
    test = Test(
        name=payload.name,
        target_url=payload.target_url,
        method=payload.method.upper(),
        headers=payload.headers,
        body=payload.body,
        vus=payload.vus,
        stages=[s.model_dump() for s in payload.stages],
        thresholds=[t.model_dump() for t in payload.thresholds],
    )
    db.add(test)
    db.commit()
    db.refresh(test)
    return test


@router.get("", response_model=list[TestOut])
def list_tests(db: Session = Depends(get_db)):
    return db.query(Test).order_by(desc(Test.created_at)).all()


@router.get("/{test_id}", response_model=TestOut)
def get_test(test_id: str, db: Session = Depends(get_db)):
    test = db.get(Test, test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    return test


@router.delete("/{test_id}", status_code=204)
def delete_test(test_id: str, db: Session = Depends(get_db)):
    test = db.get(Test, test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    db.delete(test)
    db.commit()
