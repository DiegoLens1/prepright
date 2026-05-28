from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from prepright.database import get_db
from prepright import models, schemas

router = APIRouter(prefix="/api", tags=["recipes"])


@router.get("/products/{product_id}/recipes", response_model=list[schemas.RecipeRead])
def get_product_recipes(product_id: int, db: Session = Depends(get_db)):
    db_prod = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not db_prod:
        raise HTTPException(404, "Product not found")
    return db.query(models.Recipe).options(joinedload(models.Recipe.ingredient)).filter(models.Recipe.product_id == product_id).all()


@router.post("/products/{product_id}/recipes", response_model=schemas.RecipeRead, status_code=status.HTTP_201_CREATED)
def add_recipe(product_id: int, recipe: schemas.RecipeCreate, db: Session = Depends(get_db)):
    db_prod = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not db_prod:
        raise HTTPException(404, "Product not found")
    db_recipe = models.Recipe(product_id=product_id, **recipe.model_dump())
    db.add(db_recipe)
    db.commit()
    db.refresh(db_recipe)
    return db_recipe


@router.delete("/recipes/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipe(recipe_id: int, db: Session = Depends(get_db)):
    db_recipe = db.query(models.Recipe).filter(models.Recipe.id == recipe_id).first()
    if not db_recipe:
        raise HTTPException(404, "Recipe not found")
    db.delete(db_recipe)
    db.commit()
