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
            "name": "demo",
            "description": "Name + optional quantity (xN) + price; quantity defaults to 1",
            "active": True,
            "source_keyword": "DEMO",
            "line_pattern": r"^(?P<name>.+?)\s+(?:x(?P<qty>\d+)\s+)?(?P<price>\d+[.,]\d{2})$",
            "product_name_group": "name",
            "quantity_group": "qty",
            "price_group": "price",
            "line_prefix": None,
            "line_suffix": None,
            "name_normalize": None,
            "config": None,
        },
    ]

    seed_names = {t["name"] for t in default_templates}

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

    # Prune templates that are no longer part of the seed set, so redeploys
    # fully reconcile the DB (avoids stale rows colliding on auto-detect).
    deleted = (
        db.query(models.ReceiptTemplate)
        .filter(models.ReceiptTemplate.name.notin_(seed_names))
        .delete(synchronize_session=False)
    )

    db.commit()
    db.close()
    print(
        f"Seeded receipt templates: {created} created, {updated} updated, {deleted} deleted."
    )


if __name__ == "__main__":
    seed_templates()
