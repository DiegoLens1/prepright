from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from prepright.database import get_db
from prepright import models, schemas
from prepright.receipt_parser import ReceiptParser, match_products

router = APIRouter(prefix="/api/receipts", tags=["receipts"])


@router.post("/process", response_model=dict)
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
    sale_date = date_type.today().isoformat()
    for match in matches:
        record = models.SalesRecord(
            product_id=match.product_id,
            quantity=match.quantity,
            sale_date=sale_date,
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
