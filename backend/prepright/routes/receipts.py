from datetime import date as date_type
import base64
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from prepright.database import get_db
from prepright import models, schemas
from prepright.receipt_parser import ReceiptParser, match_products
from prepright.esc_pos import print_to_usb_printer, esc_pos_to_text

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


@router.post("/process-and-print", response_model=dict)
def process_and_print_receipt(
    request: schemas.ReceiptProcessRequest,
    printer_port: str = "/dev/usb/lp0",
    db: Session = Depends(get_db),
):
    """Process a receipt and print it to a USB thermal printer."""
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

    # Print to USB thermal printer
    print_result = print_to_usb_printer(request.text, port=printer_port)

    return {
        "template_name": parsed.template_name,
        "parsed_line_count": parsed.parsed_line_count,
        "raw_line_count": parsed.raw_line_count,
        "matched_count": len(matches),
        "total_unmatched": len(parsed.unmatched),
        "unmatched": parsed.unmatched[:20],
        "matches": [m.model_dump() for m in matches],
        "printed": print_result == "ok",
        "print_result": print_result,
    }


@router.post("/print")
def print_escpos(
    file: Optional[UploadFile] = File(None),
    data: Optional[str] = Form(None),
    template_name: Optional[str] = Form(None),
    printer_port: str = Form("/dev/usb/lp0"),
    db: Session = Depends(get_db),
):
    """Receive raw ESC/POS bytes, parse the receipt, store sales records, and print.

    Accepts ESC/POS data in two ways:
    1. Binary file upload (multipart/form-data with field 'file')
    2. Base64-encoded string in form field 'data'

    The ESC/POS bytes are decoded to text, parsed with the receipt parser,
    products are matched and sales records created, then the raw bytes
    are sent to the USB printer.

    Example with curl (binary from file):
        curl -X POST "http://<PI>:8000/api/receipts/print" \
          -F "file=@receipt.bin"

    Example with curl (base64 string):
        curl -X POST "http://<PI>:8000/api/receipts/print" \
          -F "data=BASE64_STRING"
    """
    if file:
        raw_bytes = file.file.read()
    elif data:
        try:
            raw_bytes = base64.b64decode(data)
        except Exception:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid base64 in 'data' field"},
            )
    else:
        return JSONResponse(
            status_code=400,
            content={"error": "Provide 'file' (binary) or 'data' (base64 string)"},
        )

    if not raw_bytes:
        return JSONResponse(
            status_code=400,
            content={"error": "Empty input"},
        )

    # 1. Decode ESC/POS bytes to plain text for parsing
    text = esc_pos_to_text(raw_bytes)
    text = text.strip()

    # 2. Parse receipt and match products
    parser = ReceiptParser(db)

    if template_name:
        db_template = db.query(models.ReceiptTemplate).filter(
            models.ReceiptTemplate.name == template_name,
            models.ReceiptTemplate.active == True
        ).first()
        if not db_template:
            return JSONResponse(
                status_code=404,
                content={"error": f"Template '{template_name}' not found"},
            )

    parsed = parser.parse_receipt(text, template_name)
    matches = match_products(parsed, db)

    # 3. Create SalesRecord entries
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

    # 4. Send raw ESC/POS bytes to USB printer
    try:
        with open(printer_port, "wb") as f:
            f.write(raw_bytes)
        printed_ok = True
        print_result = "ok"
    except FileNotFoundError:
        printed_ok = False
        print_result = f"Printer device not found: {printer_port}"
    except PermissionError:
        printed_ok = False
        print_result = f"Permission denied on {printer_port}. Add user to dialout+lp groups."
    except OSError as e:
        printed_ok = False
        print_result = f"IO error writing to printer: {e}"

    return JSONResponse(content={
        "template_name": parsed.template_name,
        "parsed_line_count": parsed.parsed_line_count,
        "raw_line_count": parsed.raw_line_count,
        "matched_count": len(matches),
        "total_unmatched": len(parsed.unmatched),
        "unmatched": parsed.unmatched[:20],
        "matches": [m.model_dump() for m in matches],
        "printed": printed_ok,
        "print_result": print_result,
    })
