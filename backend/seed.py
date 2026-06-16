"""
Seed script: creates default categories and settings.
Run once: python -c "from seed import seed_db; seed_db()"
"""
from sqlalchemy.orm import Session
from prepright.database import engine, SessionLocal
from prepright import models


def seed_db():
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Default categories with weather sensitivity
    default_categories = [
        {"name": "Ontbijt", "weather_sensitivity": 0.85},
        {"name": "Lunch broodjes", "weather_sensitivity": 0.9},
        {"name": "Warme broodjes", "weather_sensitivity": 0.95},
        {"name": "Warme snacks", "weather_sensitivity": 0.75},
        {"name": "IJs", "weather_sensitivity": 1.3},
        {"name": "Warme dranken", "weather_sensitivity": 1.2},
        {"name": "Koude dranken", "weather_sensitivity": 1.1},
        {"name": "Hotdogs & Rookworsten", "weather_sensitivity": 0.8},
    ]

    for cat_data in default_categories:
        if not db.query(models.Category).filter(models.Category.name == cat_data["name"]).first():
            db.add(models.Category(**cat_data))

    # Default settings
    default_settings = {
        "weather_condition": "normal",
        "default_margin_pct": "0",
        "prediction_weeks": "3",
    }
    for key, value in default_settings.items():
        existing = db.query(models.Setting).filter(models.Setting.key == key).first()
        if not existing:
            db.add(models.Setting(key=key, value=value))

    db.commit()
    db.close()
    print("Database seeded successfully.")


if __name__ == "__main__":
    seed_db()
