from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from prepright.database import get_db
from prepright import models, schemas

router = APIRouter(prefix="/api/ingredients", tags=["ingredients"])


@router.get("", response_model=list[schemas.IngredientRead])
def list_ingredients(db: Session = Depends(get_db)):
    return db.query(models.Ingredient).filter(models.Ingredient.active == True).all()


@router.post("/", response_model=schemas.IngredientRead, status_code=status.HTTP_201_CREATED)
def create_ingredient(ing: schemas.IngredientCreate, db: Session = Depends(get_db)):
    if db.query(models.Ingredient).filter(models.Ingredient.name == ing.name).first():
        raise HTTPException(400, "Ingredient already exists")
    db_ing = models.Ingredient(**ing.model_dump())
    db.add(db_ing)
    db.commit()
    db.refresh(db_ing)
    return db_ing


@router.put("/{ingredient_id}", response_model=schemas.IngredientRead)
def update_ingredient(ingredient_id: int, ing: schemas.IngredientUpdate, db: Session = Depends(get_db)):
    db_ing = db.query(models.Ingredient).filter(models.Ingredient.id == ingredient_id).first()
    if not db_ing:
        raise HTTPException(404, "Ingredient not found")
    for k, v in ing.model_dump(exclude_unset=True).items():
        setattr(db_ing, k, v)
    db.commit()
    db.refresh(db_ing)
    return db_ing


@router.delete("/{ingredient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ingredient(ingredient_id: int, db: Session = Depends(get_db)):
    db_ing = db.query(models.Ingredient).filter(models.Ingredient.id == ingredient_id).first()
    if not db_ing:
        raise HTTPException(404, "Ingredient not found")
    db.delete(db_ing)
    db.commit()
