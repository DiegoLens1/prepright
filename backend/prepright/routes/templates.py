from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from prepright.database import get_db
from prepright import models, schemas

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("", response_model=list[schemas.ReceiptTemplateRead])
def list_templates(db: Session = Depends(get_db)):
    return db.query(models.ReceiptTemplate).order_by(models.ReceiptTemplate.name).all()


@router.post("/", response_model=schemas.ReceiptTemplateRead, status_code=status.HTTP_201_CREATED)
def create_template(template: schemas.ReceiptTemplateCreate, db: Session = Depends(get_db)):
    if db.query(models.ReceiptTemplate).filter(models.ReceiptTemplate.name == template.name).first():
        raise HTTPException(400, "Template already exists")
    db_template = models.ReceiptTemplate(**template.model_dump())
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template


@router.put("/{template_id}", response_model=schemas.ReceiptTemplateRead)
def update_template(template_id: int, template: schemas.ReceiptTemplateUpdate, db: Session = Depends(get_db)):
    db_template = db.query(models.ReceiptTemplate).filter(models.ReceiptTemplate.id == template_id).first()
    if not db_template:
        raise HTTPException(404, "Template not found")
    for k, v in template.model_dump(exclude_unset=True).items():
        setattr(db_template, k, v)
    db.commit()
    db.refresh(db_template)
    return db_template


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(template_id: int, db: Session = Depends(get_db)):
    db_template = db.query(models.ReceiptTemplate).filter(models.ReceiptTemplate.id == template_id).first()
    if not db_template:
        raise HTTPException(404, "Template not found")
    db.delete(db_template)
    db.commit()
