from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from prepright.database import get_db
from prepright import models, schemas

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=list[schemas.CategoryRead])
def list_categories(include_inactive: bool = False, db: Session = Depends(get_db)):
    query = db.query(models.Category)
    if not include_inactive:
        query = query.filter(models.Category.active == True)
    return query.all()


@router.post("", response_model=schemas.CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(cat: schemas.CategoryCreate, db: Session = Depends(get_db)):
    if db.query(models.Category).filter(models.Category.name == cat.name).first():
        raise HTTPException(400, "Category already exists")
    db_cat = models.Category(**cat.model_dump())
    db.add(db_cat)
    db.commit()
    db.refresh(db_cat)
    return db_cat


@router.put("/{category_id}", response_model=schemas.CategoryRead)
def update_category(category_id: int, cat: schemas.CategoryUpdate, db: Session = Depends(get_db)):
    db_cat = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not db_cat:
        raise HTTPException(404, "Category not found")
    for k, v in cat.model_dump(exclude_unset=True).items():
        setattr(db_cat, k, v)
    db.commit()
    db.refresh(db_cat)
    return db_cat


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    db_cat = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not db_cat:
        raise HTTPException(404, "Category not found")
    db.delete(db_cat)
    db.commit()
