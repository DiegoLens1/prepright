"""
Simulated print order endpoint for demo purposes.

Generates a thermal-receipt-style text output without requiring a real printer.
Useful for showcasing the product flow during demos and presentations.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from prepright.database import get_db
from prepright import models

router = APIRouter(prefix="/api/print-orders", tags=["print-orders"])


class OrderItem(BaseModel):
    product_id: int
    quantity: float = Field(ge=0.01)


class PrintOrderRequest(BaseModel):
    items: list[OrderItem]
    customer_name: str = ""


class PrintOrderResponse(BaseModel):
    receipt_text: str
    order_number: str
    timestamp: str


# Demo fallback prices when no products exist
_DEMO_PRODUCTS = [
    {"name": "Chocolate Croissant", "price": 4.50},
    {"name": "Cappuccino", "price": 5.00},
    {"name": "Caesar Salad", "price": 12.00},
    {"name": "Espresso", "price": 3.50},
    {"name": "Avocado Toast", "price": 9.00},
]


def _generate_receipt_text(items, order_number, timestamp, products_map):
    """Generate a thermal-receipt-style text string."""
    W = 40  # standard thermal receipt width
    lines = []

    lines.append(f"{'PREPRIGHT':^{W}}")
    lines.append(f"{'Demo Location':^{W}}")
    lines.append(f"{'123 Main Street, Suite 1':^{W}}")
    lines.append(f"{'Tel: (555) 123-4567':^{W}}")
    lines.append("")
    lines.append(f"Order #: {order_number}")
    lines.append(f"Date: {timestamp}")
    lines.append("-" * W)

    total = 0.0
    for item in items:
        product = products_map.get(item.product_id)
        if product:
            name = product["name"]
            price = product["price"]
        else:
            name = f"Product #{item.product_id}"
            price = 0.0

        qty = item.quantity
        line_total = qty * price
        total += line_total

        # Format: name ··· qty ··· price
        price_str = f"${price:.2f}"
        qty_str = str(qty)
        name_width = W - len(qty_str) - len(price_str) - 5
        if name_width < 1:
            name_width = 1

        padded_name = name[:name_width]
        dots = "." * max(1, name_width - len(padded_name))

        lines.append(f"{padded_name}{dots} {qty_str} {price_str}")

    lines.append("-" * W)

    # Subtotal
    lines.append(f"{'Subtotal':<{W - 8}} ${total:.2f}")

    # Tax (10%)
    tax = total * 0.10
    lines.append(f"{'Tax (10%)':<{W - 8}} ${tax:.2f}")

    # Total
    grand_total = total + tax
    lines.append(f"{'TOTAL':<{W - 8}} ${grand_total:.2f}")

    lines.append("")
    lines.append("-" * W)
    lines.append(f"{'Thank you!':^{W}}")
    lines.append(f"{'Visit us again :)':^{W}}")

    return "\n".join(lines)


@router.post("/simulate", response_model=PrintOrderResponse)
def simulate_print_order(
    request: PrintOrderRequest,
    db: Session = Depends(get_db),
):
    """Simulate sending an order to a receipt printer (demo mode).

    Returns a thermal-receipt-style text that can be previewed in the browser.
    """
    # Build product lookup
    products_map = {}
    if request.items:
        first_id = request.items[0].product_id
        db_product = db.query(models.Product).filter(
            models.Product.id == first_id
        ).first()

        if db_product:
            # Use real products from DB
            active_products = (
                db.query(models.Product)
                .filter(models.Product.active == True)
                .all()
            )
            for p in active_products:
                products_map[p.id] = {
                    "name": p.name,
                    "price": round(p.margin_pct, 2) if p.margin_pct else 5.00,
                }

    # Fallback to demo products if no DB products available
    if not products_map:
        for i, dp in enumerate(_DEMO_PRODUCTS):
            products_map[i + 1] = dp

    # Generate order number
    now = datetime.now(timezone.utc)
    order_number = f"ORD-{now.strftime('%y%m%d')}-{now.hour}{now.minute}{now.second}"
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

    receipt_text = _generate_receipt_text(
        request.items, order_number, timestamp, products_map
    )

    return PrintOrderResponse(
        receipt_text=receipt_text,
        order_number=order_number,
        timestamp=timestamp,
    )
