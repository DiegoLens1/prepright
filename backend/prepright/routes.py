from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

from prepright.database import get_db
from prepright import models, schemas
from prepright.receipt_parser import ReceiptParser, match_products
from prepright.settings import get_cors_origins
from prepright.prediction_engine import generate_predictions

app = FastAPI(title="PrepRight", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Categories ──────────────────────────────────────────

@app.get("/api/categories", response_model=List[schemas.CategoryRead])
def list_categories(db: Session = Depends(get_db)):
    return db.query(models.Category).filter(models.Category.active == True).all()


@app.post("/api/categories", response_model=schemas.CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(cat: schemas.CategoryCreate, db: Session = Depends(get_db)):
    if db.query(models.Category).filter(models.Category.name == cat.name).first():
        raise HTTPException(400, "Category already exists")
    db_cat = models.Category(**cat.model_dump())
    db.add(db_cat)
    db.commit()
    db.refresh(db_cat)
    return db_cat


@app.put("/api/categories/{category_id}", response_model=schemas.CategoryRead)
def update_category(category_id: int, cat: schemas.CategoryUpdate, db: Session = Depends(get_db)):
    db_cat = db.query(models.Category).options(joinedload(models.Category.products)).filter(models.Category.id == category_id).first()
    if not db_cat:
        raise HTTPException(404, "Category not found")
    for k, v in cat.model_dump(exclude_unset=True).items():
        setattr(db_cat, k, v)
    db.commit()
    db.refresh(db_cat)
    return db_cat


@app.delete("/api/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    db_cat = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not db_cat:
        raise HTTPException(404, "Category not found")
    db.delete(db_cat)
    db.commit()


# ── Ingredients ─────────────────────────────────────────

@app.get("/api/ingredients", response_model=List[schemas.IngredientRead])
def list_ingredients(db: Session = Depends(get_db)):
    return db.query(models.Ingredient).filter(models.Ingredient.active == True).all()


@app.post("/api/ingredients", response_model=schemas.IngredientRead, status_code=status.HTTP_201_CREATED)
def create_ingredient(ing: schemas.IngredientCreate, db: Session = Depends(get_db)):
    if db.query(models.Ingredient).filter(models.Ingredient.name == ing.name).first():
        raise HTTPException(400, "Ingredient already exists")
    db_ing = models.Ingredient(**ing.model_dump())
    db.add(db_ing)
    db.commit()
    db.refresh(db_ing)
    return db_ing


@app.put("/api/ingredients/{ingredient_id}", response_model=schemas.IngredientRead)
def update_ingredient(ingredient_id: int, ing: schemas.IngredientUpdate, db: Session = Depends(get_db)):
    db_ing = db.query(models.Ingredient).filter(models.Ingredient.id == ingredient_id).first()
    if not db_ing:
        raise HTTPException(404, "Ingredient not found")
    for k, v in ing.model_dump(exclude_unset=True).items():
        setattr(db_ing, k, v)
    db.commit()
    db.refresh(db_ing)
    return db_ing


@app.delete("/api/ingredients/{ingredient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ingredient(ingredient_id: int, db: Session = Depends(get_db)):
    db_ing = db.query(models.Ingredient).filter(models.Ingredient.id == ingredient_id).first()
    if not db_ing:
        raise HTTPException(404, "Ingredient not found")
    db.delete(db_ing)
    db.commit()


# ── Products ────────────────────────────────────────────

@app.get("/api/products", response_model=List[schemas.ProductRead])
def list_products(db: Session = Depends(get_db)):
    products = (
        db.query(models.Product)
        .options(joinedload(models.Product.category), joinedload(models.Product.aliases), joinedload(models.Product.recipes))
        .filter(models.Product.active == True)
        .all()
    )
    return [_product_to_schema(p) for p in products]


@app.post("/api/products", response_model=schemas.ProductRead, status_code=status.HTTP_201_CREATED)
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


@app.put("/api/products/{product_id}", response_model=schemas.ProductRead)
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


@app.delete("/api/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    db_prod = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not db_prod:
        raise HTTPException(404, "Product not found")
    db.delete(db_prod)
    db.commit()


# ── Recipes (ingredient breakdown per product) ──────────

@app.get("/api/products/{product_id}/recipes", response_model=List[schemas.RecipeRead])
def get_product_recipes(product_id: int, db: Session = Depends(get_db)):
    db_prod = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not db_prod:
        raise HTTPException(404, "Product not found")
    return db.query(models.Recipe).filter(models.Recipe.product_id == product_id).all()


@app.post("/api/products/{product_id}/recipes", response_model=schemas.RecipeRead, status_code=status.HTTP_201_CREATED)
def add_recipe(product_id: int, recipe: schemas.RecipeCreate, db: Session = Depends(get_db)):
    db_prod = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not db_prod:
        raise HTTPException(404, "Product not found")
    db_recipe = models.Recipe(product_id=product_id, **recipe.model_dump())
    db.add(db_recipe)
    db.commit()
    db.refresh(db_recipe)
    return db_recipe


@app.delete("/api/recipes/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipe(recipe_id: int, db: Session = Depends(get_db)):
    db_recipe = db.query(models.Recipe).filter(models.Recipe.id == recipe_id).first()
    if not db_recipe:
        raise HTTPException(404, "Recipe not found")
    db.delete(db_recipe)
    db.commit()


# ── Events ──────────────────────────────────────────────

@app.get("/api/events", response_model=List[schemas.EventRead])
def list_events(db: Session = Depends(get_db)):
    return db.query(models.Event).order_by(models.Event.date).all()


@app.post("/api/events", response_model=schemas.EventRead, status_code=status.HTTP_201_CREATED)
def create_event(evt: schemas.EventCreate, db: Session = Depends(get_db)):
    if db.query(models.Event).filter(models.Event.date == evt.date).first():
        raise HTTPException(400, "Event on this date already exists")
    db_evt = models.Event(**evt.model_dump())
    db.add(db_evt)
    db.commit()
    db.refresh(db_evt)
    return db_evt


@app.put("/api/events/{event_id}", response_model=schemas.EventRead)
def update_event(event_id: int, evt: schemas.EventUpdate, db: Session = Depends(get_db)):
    db_evt = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not db_evt:
        raise HTTPException(404, "Event not found")
    for k, v in evt.model_dump(exclude_unset=True).items():
        setattr(db_evt, k, v)
    db.commit()
    db.refresh(db_evt)
    return db_evt


@app.delete("/api/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(event_id: int, db: Session = Depends(get_db)):
    db_evt = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not db_evt:
        raise HTTPException(404, "Event not found")
    db.delete(db_evt)
    db.commit()


# ── Settings ────────────────────────────────────────────

@app.get("/api/settings")
def get_settings(db: Session = Depends(get_db)):
    settings = {}
    for s in db.query(models.Setting).all():
        settings[s.key] = s.value
    return settings


@app.put("/api/settings/{key}")
def update_setting(key: str, val: schemas.SettingUpdate, db: Session = Depends(get_db)):
    db_setting = db.query(models.Setting).filter(models.Setting.key == key).first()
    if db_setting:
        db_setting.value = val.value
    else:
        db_setting = models.Setting(key=key, value=val.value)
        db.add(db_setting)
    db.commit()
    return {"key": key, "value": val.value}


# ── Helpers ─────────────────────────────────────────────

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


# ── Receipt Templates ───────────────────────────────────

@app.get("/api/templates", response_model=List[schemas.ReceiptTemplateRead])
def list_templates(db: Session = Depends(get_db)):
    return db.query(models.ReceiptTemplate).order_by(models.ReceiptTemplate.name).all()


@app.post("/api/templates", response_model=schemas.ReceiptTemplateRead, status_code=status.HTTP_201_CREATED)
def create_template(template: schemas.ReceiptTemplateCreate, db: Session = Depends(get_db)):
    if db.query(models.ReceiptTemplate).filter(models.ReceiptTemplate.name == template.name).first():
        raise HTTPException(400, "Template already exists")
    db_template = models.ReceiptTemplate(**template.model_dump())
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template


@app.put("/api/templates/{template_id}", response_model=schemas.ReceiptTemplateRead)
def update_template(template_id: int, template: schemas.ReceiptTemplateUpdate, db: Session = Depends(get_db)):
    db_template = db.query(models.ReceiptTemplate).filter(models.ReceiptTemplate.id == template_id).first()
    if not db_template:
        raise HTTPException(404, "Template not found")
    for k, v in template.model_dump(exclude_unset=True).items():
        setattr(db_template, k, v)
    db.commit()
    db.refresh(db_template)
    return db_template


@app.delete("/api/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(template_id: int, db: Session = Depends(get_db)):
    db_template = db.query(models.ReceiptTemplate).filter(models.ReceiptTemplate.id == template_id).first()
    if not db_template:
        raise HTTPException(404, "Template not found")
    db.delete(db_template)
    db.commit()


# ── Receipt Processing ──────────────────────────────────

@app.post("/api/receipts/process", response_model=dict)
def process_receipt(request: schemas.ReceiptProcessRequest, db: Session = Depends(get_db)):
    """Process a receipt: parse with template, match products, return results."""
    parser = ReceiptParser(db)

    if request.template_name:
        db_template = db.query(models.ReceiptTemplate).filter(
            models.ReceiptTemplate.name == request.template_name,
            models.ReceiptTemplate.active == True
        ).first()
        if not db_template:
            raise HTTPException(404, f"Template '{request.template_name}' not found")

    parsed = parser.parse_receipt(request.text, request.template_name)

    # Match parsed products to database products
    matches = match_products(parsed, db)

    # Create SalesRecord entries
    for match in matches:
        record = models.SalesRecord(
            product_id=match.product_id,
            quantity=match.quantity,
            source_template=parsed.template_name,
            confidence=match.confidence,
        )
        db.add(record)
    db.commit()

    return {
        "template_name": parsed.template_name,
        "parsed_line_count": parsed.parsed_line_count,
        "raw_line_count": parsed.raw_line_count,
        "matched_count": len(matches),
        "total_unmatched": len(parsed.unmatched),
        "unmatched": parsed.unmatched[:20],  # Limit for response size
        "matches": [m.model_dump() for m in matches],
    }


# ── Predictions ─────────────────────────────────────────

@app.post("/api/predictions/generate")
def generate_predictions_endpoint(
    request: dict = {},
    db: Session = Depends(get_db),
):
    """Generate predictions for a date range."""
    start_date = request.get("start_date")
    end_date = request.get("end_date")

    new_predictions = generate_predictions(db, start_date, end_date)

    # Delete existing predictions in range and insert fresh ones
    if start_date:
        db.query(models.Prediction).filter(
            models.Prediction.date >= start_date
        ).delete(synchronize_session="fetch")
    else:
        db.query(models.Prediction).delete(synchronize_session="fetch")
    db.commit()

    for pred in new_predictions:
        db_pred = models.Prediction(
            date=pred["date"],
            product_id=pred["product_id"],
            predicted_qty=pred["predicted_qty"],
            base_qty=pred["base_qty"],
            weather_adjustment=pred["weather_adjustment"],
            event_adjustment=pred["event_adjustment"],
        )
        db.add(db_pred)
    db.commit()

    return {"generated": len(new_predictions), "message": "Predictions generated successfully"}


@app.get("/api/predictions")
def list_predictions(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    product_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Fetch predictions with optional filters."""
    query = db.query(models.Prediction)

    if start_date:
        query = query.filter(models.Prediction.date >= start_date)
    if end_date:
        query = query.filter(models.Prediction.date <= end_date)
    if product_id:
        query = query.filter(models.Prediction.product_id == product_id)

    predictions = query.order_by(models.Prediction.date, models.Prediction.product_id).all()

    result = []
    for p in predictions:
        result.append({
            "id": p.id,
            "date": p.date,
            "product_id": p.product_id,
            "product_name": p.product.name if p.product else None,
            "predicted_qty": p.predicted_qty,
            "base_qty": p.base_qty,
            "weather_adjustment": p.weather_adjustment,
            "event_adjustment": p.event_adjustment,
            "created_at": p.created_at.isoformat(),
        })
    return result


@app.get("/api/predictions/export/pdf")
def export_predictions_pdf(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Export predictions as a printable PDF — landscape, grouped by category, products×days."""
    from math import ceil
    from io import BytesIO
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from collections import OrderedDict
    from datetime import datetime, timedelta

    predictions = list_predictions(start_date, end_date, None, db)

    if not predictions:
        return {"error": "No predictions to export"}

    # Build lookup: (date, product_id) -> prediction
    pred_map: dict = {}
    for p in predictions:
        pred_map[(p["date"], p["product_id"])] = p

    # Get all products
    all_products = db.query(models.Product).filter(models.Product.active == True).all()

    # Group products by category
    categories: dict = OrderedDict()
    for p in all_products:
        cat_name = p.category.name if p.category else "Other"
        if cat_name not in categories:
            categories[cat_name] = []
        categories[cat_name].append(p)

    # Determine weeks from predictions
    all_dates = sorted(set(p["date"] for p in predictions))
    all_dates_set = set(all_dates)
    weeks: list = []
    if all_dates:
        start = datetime.strptime(all_dates[0], "%Y-%m-%d")
        start = start - timedelta(days=start.weekday())
        end = datetime.strptime(all_dates[-1], "%Y-%m-%d")
        current = start
        while current <= end:
            week = []
            for d in range(7):
                day = current + timedelta(days=d)
                day_str = day.strftime("%Y-%m-%d")
                if day_str in all_dates_set:
                    week.append(day_str)
            if week:
                weeks.append(week)
            current += timedelta(weeks=1)

    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    # Create PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Heading1"], fontSize=14, spaceAfter=4)
    week_style = ParagraphStyle("Week", parent=styles["Heading2"], fontSize=11, spaceAfter=4, spaceBefore=8)
    cat_bold_style = ParagraphStyle("CatBold", parent=styles["Heading3"], fontSize=10, spaceAfter=2, spaceBefore=4, fontName="Helvetica-Bold")
    header_style = ParagraphStyle("Header", parent=styles["Normal"], fontSize=8, fontName="Helvetica-Bold", textColor=colors.white)
    cell_style = ParagraphStyle("Cell", parent=styles["Normal"], fontSize=8)
    cell_style_bold = ParagraphStyle("CellBold", parent=styles["Normal"], fontSize=8, fontName="Helvetica-Bold")
    cell_style_muted = ParagraphStyle("CellMuted", parent=styles["Normal"], fontSize=8, textColor=colors.HexColor("#cccccc"))

    elements = []
    elements.append(Paragraph("PrepRight — Weekly Predictions", title_style))

    for week_idx, week_dates in enumerate(weeks):
        if week_idx > 0:
            elements.append(PageBreak())

        week_start = week_dates[0]
        week_end = week_dates[-1]
        elements.append(Paragraph(f"Week of {week_start} — {week_end}", week_style))

        for cat_name, prods in categories.items():
            elements.append(Paragraph(f"<b>{cat_name}</b>", cat_bold_style))

            # Build table: rows = products, columns = days
            # Wrap header strings in Paragraph so they render correctly
            headers = [Paragraph("Product", header_style)] + [
                Paragraph(day_names[i], header_style) for i in range(len(week_dates))
            ]
            table_data = [headers]

            for prod in prods:
                row = [Paragraph(prod.name, cell_style_bold)]
                for day in week_dates:
                    pred = pred_map.get((day, prod.id))
                    if pred:
                        qty = pred["predicted_qty"]
                        cell = Paragraph(str(ceil(qty)), cell_style)
                        row.append(cell)
                    else:
                        row.append(Paragraph("\u2014", cell_style_muted))
                table_data.append(row)

            col_widths = [60 * mm] + [18 * mm] * len(week_dates)

            table = Table(table_data, colWidths=col_widths, repeatRows=1)
            style = TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3b82f6")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("BACKGROUND", (1, 1), (-1, -1), colors.HexColor("#f8f9fa")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ])
            table.setStyle(style)
            elements.append(table)
            elements.append(Spacer(1, 6))

    doc.build(elements)
    buffer.seek(0)

    return {
        "pdf_base64": buffer.read().hex(),
        "filename": f"predictions_{start_date or 'all'}_to_{end_date or 'all'}.pdf",
        "total_predictions": len(predictions),
    }
