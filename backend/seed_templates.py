import json
import sys
from datetime import datetime

from prepright.database import SessionLocal
from prepright import models

db = SessionLocal()


def seed_templates():
    """Seed default receipt templates."""
    templates = [
        {
            "name": "HEMA",
            "description": "HEMA thermal printer receipts (Dutch POS)",
            "active": True,
            "source_keyword": "HEMA",
            "line_pattern": r"^\d{8}\s+(.+?)\s+(\d+\.\d+)$",
            "product_name_group": "name",
            "quantity_group": "qty",
            "price_group": "price",
            "line_prefix": None,
            "line_suffix": None,
            "name_normalize": "BD:Bak, klein:klein, normaal:normaal, rund:rund",
            "config": json.dumps({"product_code_length": 8}),
        },
        {
            "name": "Generic POS",
            "description": "Generic POS receipt format (adjust as needed)",
            "active": False,
            "source_keyword": None,
            "line_pattern": r"^(\d+)\s+(.+?)\s+(\d+\.\d+)$",
            "product_name_group": "name",
            "quantity_group": "qty",
            "price_group": "price",
            "line_prefix": None,
            "line_suffix": None,
            "name_normalize": None,
            "config": json.dumps({}),
        },
    ]

    for t_data in templates:
        existing = db.query(models.ReceiptTemplate).filter(
            models.ReceiptTemplate.name == t_data["name"]
        ).first()
        if existing:
            print(f"Template '{t_data['name']}' already exists, skipping")
            continue

        template = models.ReceiptTemplate(**t_data)
        db.add(template)
        print(f"Seeded template: {t_data['name']}")

    db.commit()


def main():
    print("Seeding receipt templates...")
    seed_templates()
    print("Done!")
    db.close()


if __name__ == "__main__":
    main()
