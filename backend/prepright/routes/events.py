from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from prepright.database import get_db
from prepright import models, schemas

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("", response_model=list[schemas.EventRead])
def list_events(db: Session = Depends(get_db)):
    return db.query(models.Event).order_by(models.Event.date).all()


@router.post("/", response_model=schemas.EventRead, status_code=status.HTTP_201_CREATED)
def create_event(evt: schemas.EventCreate, db: Session = Depends(get_db)):
    if db.query(models.Event).filter(models.Event.date == evt.date).first():
        raise HTTPException(400, "Event on this date already exists")
    db_evt = models.Event(**evt.model_dump())
    db.add(db_evt)
    db.commit()
    db.refresh(db_evt)
    return db_evt


@router.put("/{event_id}", response_model=schemas.EventRead)
def update_event(event_id: int, evt: schemas.EventUpdate, db: Session = Depends(get_db)):
    db_evt = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not db_evt:
        raise HTTPException(404, "Event not found")
    for k, v in evt.model_dump(exclude_unset=True).items():
        setattr(db_evt, k, v)
    db.commit()
    db.refresh(db_evt)
    return db_evt


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(event_id: int, db: Session = Depends(get_db)):
    db_evt = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not db_evt:
        raise HTTPException(404, "Event not found")
    db.delete(db_evt)
    db.commit()
