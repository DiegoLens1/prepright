"""
Seed default receipt parsing templates.
Run: python seed_templates.py
"""
from sqlalchemy.orm import Session
from prepright.database import engine, SessionLocal
from prepright import models


def seed_templates():
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    default_templates = [
        {
            "name": "Standard POS",
            "description": "Generic receipt format with name, qty, price on each line",
            "active": True,
            "source_keyword": None,
            "line_pattern": r"^(?P<name>[^0-9]+?)\s+(?P<qty>\d+\.?\d*)\s*×?\s*(?P<price>\d+\.?\d+)$",
            "product_name_group": "name",
            "quantity_group": "qty",
            "price_group": "price",
            "line_prefix": None,
            "line_suffix": None,
            "name_normalize": None,
            "config": None,
        },
        {
            "name": "Decimal Qty (kg/litres)",
            "description": "Weight/volume items like cheese, milk sold by kg or litre",
            "active": True,
            "source_keyword": None,
            "line_pattern": r"^(?P<name>[^0-9]+?)\s+(?P<qty>\d+\.?\d+)\s*(kg|litre|lt|l|g|kg)\s*@\s*(?P<price>\d+\.?\d+)/\w+\s*=\s*(?P<total>\d+\.?\d+)$",
            "product_name_group": "name",
            "quantity_group": "qty",
            "price_group": "total",
            "line_prefix": None,
            "line_suffix": None,
            "name_normalize": None,
            "config": None,
        },
        {
            "name": "Simple (name + price)",
            "description": "Items with name and price, quantity assumed 1",
            "active": True,
            "source_keyword": "DEMO",
            "line_pattern": r"^(?P<name>[^0-9]+?)\s+(?P<price>\d+\.?\d+)$",
            "product_name_group": "name",
            "quantity_group": None,
            "price_group": "price",
            "line_prefix": None,
            "line_suffix": None,
            "name_normalize": None,
            "config": None,
        },
    ]

    created = 0
    updated = 0
    for tmpl_data in default_templates:
        existing = db.query(models.ReceiptTemplate).filter(
            models.ReceiptTemplate.name == tmpl_data["name"]
        ).first()
        if existing:
            # Upsert: reconcile the stored template with the bundled definition
            # so pattern/group tweaks take effect on redeploy instead of being
            # silently skipped.
            for key, value in tmpl_data.items():
                setattr(existing, key, value)
            updated += 1
        else:
            db.add(models.ReceiptTemplate(**tmpl_data))
            created += 1

    db.commit()
    db.close()
    print(f"Seeded receipt templates: {created} created, {updated} updated.")


if __name__ == "__main__":
    seed_templates()
