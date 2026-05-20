"""
Seed 5 weeks of realistic test data for testing the prediction engine.
Run: python seed_test_data.py
"""
import random
import math
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from prepright.database import engine, SessionLocal
from prepright import models


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def seed_test_data():
    """Generate 5 weeks of realistic sales data across products."""
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Categories are seeded by seed.py; ensure they exist
    existing_cats = {c.name: c for c in db.query(models.Category).all()}
    if not existing_cats:
        # Fallback: create default categories if seed.py wasn't run
        default_categories = [
            {"name": "Baked Goods", "weather_sensitivity": 0.85},
            {"name": "Beverages", "weather_sensitivity": 1.1},
            {"name": "Dairy", "weather_sensitivity": 0.95},
            {"name": "Fresh Prep", "weather_sensitivity": 0.8},
            {"name": "Snacks", "weather_sensitivity": 1.0},
            {"name": "Other", "weather_sensitivity": 1.0},
        ]
        for cat_data in default_categories:
            if cat_data["name"] not in existing_cats:
                db.add(models.Category(**cat_data))
        db.commit()
        existing_cats = {c.name: c for c in db.query(models.Category).all()}

    # Ensure default products exist
    default_products = [
        # Baked Goods (cat 1)
        {"name": "Croissant", "category": "Baked Goods", "margin": 65},
        {"name": "Baguette", "category": "Baked Goods", "margin": 60},
        {"name": "Muffin", "category": "Baked Goods", "margin": 70},
        {"name": "Sourdough Loaf", "category": "Baked Goods", "margin": 55},
        {"name": "Cinnamon Roll", "category": "Baked Goods", "margin": 68},
        # Beverages (cat 2)
        {"name": "Coffee (Large)", "category": "Beverages", "margin": 75},
        {"name": "Coffee (Small)", "category": "Beverages", "margin": 72},
        {"name": "Hot Chocolate", "category": "Beverages", "margin": 65},
        {"name": "Orange Juice", "category": "Beverages", "margin": 50},
        {"name": "Iced Tea", "category": "Beverages", "margin": 60},
        # Dairy (cat 3)
        {"name": "Milk (1L)", "category": "Dairy", "margin": 30},
        {"name": "Yogurt", "category": "Dairy", "margin": 45},
        {"name": "Cheese Slice", "category": "Dairy", "margin": 40},
        {"name": "Butter", "category": "Dairy", "margin": 35},
        # Fresh Prep (cat 4)
        {"name": "Sandwich", "category": "Fresh Prep", "margin": 50},
        {"name": "Salad Bowl", "category": "Fresh Prep", "margin": 55},
        {"name": "Soup (Ladle)", "category": "Fresh Prep", "margin": 58},
        {"name": "Pasta Dish", "category": "Fresh Prep", "margin": 45},
        # Snacks (cat 5)
        {"name": "Chips", "category": "Snacks", "margin": 55},
        {"name": "Cookie", "category": "Snacks", "margin": 65},
        {"name": "Granola Bar", "category": "Snacks", "margin": 50},
        {"name": "Brownie", "category": "Snacks", "margin": 62},
        {"name": "Pretzel", "category": "Snacks", "margin": 58},
        # Other (cat 6)
        {"name": "Water Bottle", "category": "Other", "margin": 40},
        {"name": "Napkins", "category": "Other", "margin": 80},
    ]

    cat_map = {c.name: c.id for c in existing_cats.values()}

    products = []
    for p in default_products:
        existing = db.query(models.Product).filter(models.Product.name == p["name"]).first()
        if not existing:
            prod = models.Product(
                name=p["name"],
                category_id=cat_map[p["category"]],
                margin_pct=p["margin"],
                active=True,
            )
            db.add(prod)
            products.append(prod)
        else:
            products.append(existing)
    db.commit()

    # Build product lookup
    prod_map = {p.name: p for p in products}

    # Day-of-week multipliers (school context: weekdays=1.0, Sat=0.3, Sun=0.0)
    day_multipliers = {0: 1.0, 1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 5: 0.3, 6: 0.0}

    # Base daily demand per product (realistic school quantities)
    base_demand = {
        "Croissant": 15,
        "Baguette": 8,
        "Muffin": 12,
        "Sourdough Loaf": 5,
        "Cinnamon Roll": 10,
        "Coffee (Large)": 25,
        "Coffee (Small)": 15,
        "Hot Chocolate": 8,
        "Orange Juice": 10,
        "Iced Tea": 7,
        "Milk (1L)": 6,
        "Yogurt": 8,
        "Cheese Slice": 5,
        "Butter": 3,
        "Sandwich": 18,
        "Salad Bowl": 7,
        "Soup (Ladle)": 12,
        "Pasta Dish": 6,
        "Chips": 10,
        "Cookie": 12,
        "Granola Bar": 6,
        "Brownie": 8,
        "Pretzel": 5,
        "Water Bottle": 10,
        "Napkins": 3,
    }

    # Weather patterns for 5 weeks (simulate changing weather)
    weather_pattern = [
        "sunny", "sunny", "cloudy", "rainy", "rainy", "cloudy", "sunny",  # Week 1
        "sunny", "sunny", "sunny", "cloudy", "cloudy", "rainy", "rainy",  # Week 2
        "cloudy", "sunny", "sunny", "sunny", "cloudy", "rainy", "rainy",  # Week 3
        "rainy", "rainy", "cloudy", "sunny", "sunny", "sunny", "sunny",   # Week 4
        "sunny", "cloudy", "cloudy", "rainy", "rainy", "cloudy", "sunny", # Week 5
    ]

    # Weather impact on demand (multiplier)
    weather_impact = {
        "sunny": 1.15,   # More foot traffic
        "cloudy": 1.0,
        "rainy": 0.75,   # Less foot traffic
        "snowy": 0.5,
    }

    random.seed(42)

    # Generate 5 weeks = 35 days of data (leading up to today)
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    # Start 5 weeks before today, aligned to a Monday
    start_date = today - timedelta(days=35)
    days_offset = start_date.weekday()  # shift to Monday
    start_date = start_date - timedelta(days=days_offset)
    total_records = 0
    total_skipped = 0

    for day_offset in range(35):
        current_date = start_date + timedelta(days=day_offset)
        date_str = current_date.strftime("%Y-%m-%d")
        day_of_week = current_date.weekday()  # 0=Mon, 6=Sun
        weather = weather_pattern[day_offset]

        # Skip Sundays entirely (no school)
        if day_of_week == 6:
            total_skipped += 1
            continue

        for prod_name, base_qty in base_demand.items():
            prod = prod_map[prod_name]
            cat = db.get(models.Category, prod.category_id)

            # Apply day multiplier
            qty = base_qty * day_multipliers[day_of_week]

            # Apply weather impact
            qty *= weather_impact.get(weather, 1.0)

            # Add realistic variance (±20%)
            qty *= random.uniform(0.8, 1.2)

            # Add slight upward trend over weeks (growing demand)
            week_num = day_offset // 7
            qty *= (1 + week_num * 0.03)

            # Round to nearest integer (or half for some items)
            if prod_name in ("Soup (Ladle)", "Milk (1L)"):
                qty = round(qty, 1)
            else:
                qty = max(0, round(qty))

            record = models.SalesRecord(
                product_id=prod.id,
                quantity=qty,
                sale_date=date_str,
                source_template="seed_test_data",
                confidence="high",
            )
            db.add(record)
            total_records += 1

    db.commit()
    db.close()

    print(f"Seeded {total_records} sales records across 5 weeks ({total_skipped} Sundays skipped).")
    print(f"Products: {len(products)}")
    print(f"Weather pattern: {weather_pattern}")
    print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {(start_date + timedelta(days=34)).strftime('%Y-%m-%d')}")


if __name__ == "__main__":
    seed_test_data()
