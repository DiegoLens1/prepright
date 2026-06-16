from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from typing import Optional

from prepright.database import get_db
from prepright import models
from prepright.prediction_engine import generate_predictions

router = APIRouter(prefix="/api/predictions", tags=["predictions"])


class GenerateRequest(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None


@router.post("/generate")
def generate_predictions_endpoint(
    request: GenerateRequest = GenerateRequest(),
    db: Session = Depends(get_db),
):
    """Generate predictions for a date range."""
    start_date = request.start_date
    end_date = request.end_date

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


@router.get("")
def list_predictions(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    product_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Fetch predictions with optional filters."""
    query = db.query(models.Prediction).options(joinedload(models.Prediction.product))

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


@router.get("/sales-records")
def get_sales_records(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    product_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Fetch actual sales records with optional filters."""
    query = db.query(models.SalesRecord)

    if start_date:
        query = query.filter(models.SalesRecord.sale_date >= start_date)
    if end_date:
        query = query.filter(models.SalesRecord.sale_date <= end_date)
    if product_id:
        query = query.filter(models.SalesRecord.product_id == product_id)

    records = query.order_by(models.SalesRecord.sale_date, models.SalesRecord.product_id).all()

    result = []
    for r in records:
        result.append({
            "id": r.id,
            "sale_date": r.sale_date,
            "product_id": r.product_id,
            "product_name": r.product.name if r.product else None,
            "quantity": r.quantity,
            "confidence": r.confidence,
        })
    return result


@router.get("/export/pdf")
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
        raise HTTPException(404, "No predictions to export")

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

    filename = f"predictions_{start_date or 'all'}_to_{end_date or 'all'}.pdf"
    return Response(
        content=buffer.read(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
