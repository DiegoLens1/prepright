from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from prepright.database import get_db
from prepright import models, schemas


def _product_to_schema(p):
    recipes = [
        {"id": r.id, "ingredient_id": r.ingredient_id, "quantity_per_unit": r.quantity_per_unit,
         "ingredient_name": r.ingredient.name}
        for r in p.recipes
    ]
    return {
        "id": p.id,
        "name": p.name,
        "category_id": p.category_id,
        "category_name": p.category.name if p.category else None,
        "margin_pct": p.margin_pct,
        "active": p.active,
        "created_at": p.created_at,
        "aliases": [{"id": a.id, "alias_name": a.alias_name} for a in p.aliases],
        "recipes": recipes,
    }


router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("", response_model=list[schemas.ProductRead])
def list_products(db: Session = Depends(get_db)):
    products = (
        db.query(models.Product)
        .options(joinedload(models.Product.category), joinedload(models.Product.aliases), joinedload(models.Product.recipes))
        .filter(models.Product.active == True)
        .all()
    )
    return [_product_to_schema(p) for p in products]


@router.post("", response_model=schemas.ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(prod: schemas.ProductCreate, db: Session = Depends(get_db)):
    if db.query(models.Product).filter(models.Product.name == prod.name).first():
        raise HTTPException(400, "Product already exists")
    db_prod = models.Product(**prod.model_dump(exclude={"aliases", "recipes"}))
    db.add(db_prod)
    db.flush()

    for alias in prod.aliases or []:
        db.add(models.ProductAlias(product_id=db_prod.id, **alias.model_dump()))

    for recipe in prod.recipes or []:
        db.add(models.Recipe(product_id=db_prod.id, **recipe.model_dump()))

    db.commit()
    db.refresh(db_prod)
    return _product_to_schema(db_prod)


@router.put("/{product_id}", response_model=schemas.ProductRead)
def update_product(product_id: int, prod: schemas.ProductUpdate, db: Session = Depends(get_db)):
    db_prod = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not db_prod:
        raise HTTPException(404, "Product not found")

    data = prod.model_dump(exclude_unset=True, exclude={"aliases", "recipes"})
    for k, v in data.items():
        setattr(db_prod, k, v)

    if "aliases" in prod.model_fields_set:
        db.query(models.ProductAlias).filter(models.ProductAlias.product_id == product_id).delete()
        for alias in prod.aliases or []:
            db.add(models.ProductAlias(product_id=product_id, **alias.model_dump()))

    if "recipes" in prod.model_fields_set:
        db.query(models.Recipe).filter(models.Recipe.product_id == product_id).delete()
        for recipe in prod.recipes or []:
            db.add(models.Recipe(product_id=product_id, **recipe.model_dump()))

    db.commit()
    db.refresh(db_prod)
    return _product_to_schema(db_prod)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    db_prod = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not db_prod:
        raise HTTPException(404, "Product not found")
    # Clear rows that FK-reference this product but have no ORM cascade
    # (aliases & recipes cascade automatically). Sales history and predictions
    # for this product are intentionally discarded on a hard delete.
    db.query(models.Prediction).filter(models.Prediction.product_id == product_id).delete(synchronize_session=False)
    db.query(models.SalesRecord).filter(models.SalesRecord.product_id == product_id).delete(synchronize_session=False)
    db.delete(db_prod)
    db.commit()
