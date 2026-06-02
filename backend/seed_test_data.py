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

    # Create categories matching the actual menu
    category_defs = [
        {"name": "Ontbijt", "weather_sensitivity": 0.85},
        {"name": "Lunch broodjes", "weather_sensitivity": 0.9},
        {"name": "Warme broodjes", "weather_sensitivity": 0.95},
        {"name": "Warme snacks", "weather_sensitivity": 0.75},
        {"name": "IJs", "weather_sensitivity": 1.3},
        {"name": "Warme dranken", "weather_sensitivity": 1.2},
        {"name": "Koude dranken", "weather_sensitivity": 1.1},
        {"name": "Hotdogs & Rookworsten", "weather_sensitivity": 0.8},
    ]

    existing_cats = {c.name: c for c in db.query(models.Category).all()}
    for cat_data in category_defs:
        if cat_data["name"] not in existing_cats:
            db.add(models.Category(**cat_data))
    db.commit()
    existing_cats = {c.name: c for c in db.query(models.Category).all()}

    # Products grouped by category
    default_products = [
        # Ontbijt
        {"name": "Klein ontbijt", "category": "Ontbijt", "margin": 60},
        {"name": "Middel ontbijt", "category": "Ontbijt", "margin": 62},
        {"name": "Groot ontbijt wit", "category": "Ontbijt", "margin": 65},
        {"name": "Groot ontbijt bruin", "category": "Ontbijt", "margin": 65},
        # Lunch broodjes
        {"name": "Bagel roomkaas & zalm", "category": "Lunch broodjes", "margin": 55},
        {"name": "Hemaatje wit met roomkaas", "category": "Lunch broodjes", "margin": 58},
        {"name": "Hemaatje bruin met roomkaas", "category": "Lunch broodjes", "margin": 58},
        {"name": "Hemaatje wit mozzarella & tomaat", "category": "Lunch broodjes", "margin": 55},
        {"name": "Hemaatje bruin mozzarella & tomaat", "category": "Lunch broodjes", "margin": 55},
        {"name": "Hemaatje wit tonijnsalade", "category": "Lunch broodjes", "margin": 56},
        {"name": "Hemaatje bruin tonijnsalade", "category": "Lunch broodjes", "margin": 56},
        {"name": "Hemaatje wit pulled chicken", "category": "Lunch broodjes", "margin": 54},
        {"name": "Hemaatje bruin pulled chicken", "category": "Lunch broodjes", "margin": 54},
        {"name": "Bomvol broodje wit gezond", "category": "Lunch broodjes", "margin": 52},
        {"name": "Bomvol broodje bruin gezond", "category": "Lunch broodjes", "margin": 52},
        {"name": "Bomvol broodje wit kip", "category": "Lunch broodjes", "margin": 50},
        {"name": "Bomvol broodje bruin kip", "category": "Lunch broodjes", "margin": 50},
        {"name": "Bomvol broodje wit grillworst", "category": "Lunch broodjes", "margin": 48},
        {"name": "Bomvol broodje bruin grillworst", "category": "Lunch broodjes", "margin": 48},
        # Warme broodjes
        {"name": "Ciabatta pittige kip", "category": "Warme broodjes", "margin": 53},
        {"name": "Ciabatta tuna melt", "category": "Warme broodjes", "margin": 52},
        {"name": "Croque monsieur", "category": "Warme broodjes", "margin": 55},
        {"name": "Tosti ham-kaas", "category": "Warme broodjes", "margin": 58},
        {"name": "Glutenvrije tosti ham-kaas", "category": "Warme broodjes", "margin": 58},
        {"name": "Tosti pulled chicken", "category": "Warme broodjes", "margin": 54},
        # Warme snacks
        {"name": "Kaasstengel", "category": "Warme snacks", "margin": 65},
        {"name": "Ovenkroket", "category": "Warme snacks", "margin": 68},
        {"name": "Broodje ovenkroket", "category": "Warme snacks", "margin": 60},
        {"name": "Kippensoep", "category": "Warme snacks", "margin": 62},
        {"name": "Feta-spinaziebroodje", "category": "Warme snacks", "margin": 56},
        # IJs
        {"name": "Softijs klein", "category": "IJs", "margin": 72},
        {"name": "Softijs groot", "category": "IJs", "margin": 70},
        {"name": "Softijs bakje", "category": "IJs", "margin": 70},
        {"name": "Schepijs hoorn", "category": "IJs", "margin": 75},
        {"name": "Schepijs bakje klein", "category": "IJs", "margin": 73},
        {"name": "Schepijs bakje middel", "category": "IJs", "margin": 72},
        {"name": "Schepijs bakje groot", "category": "IJs", "margin": 70},
        {"name": "Slush standaard", "category": "IJs", "margin": 78},
        {"name": "Slush Blue Citrus", "category": "IJs", "margin": 78},
        {"name": "Slush Mango", "category": "IJs", "margin": 78},
        {"name": "Slush Groene appel", "category": "IJs", "margin": 78},
        {"name": "Slush Watermeloen", "category": "IJs", "margin": 78},
        # Warme dranken
        {"name": "Koffie", "category": "Warme dranken", "margin": 75},
        {"name": "Cappuccino klein", "category": "Warme dranken", "margin": 72},
        {"name": "Cappuccino groot", "category": "Warme dranken", "margin": 70},
        {"name": "Latte machiato", "category": "Warme dranken", "margin": 71},
        {"name": "Koffie verkeerd", "category": "Warme dranken", "margin": 73},
        {"name": "Espresso", "category": "Warme dranken", "margin": 78},
        {"name": "Espresso dubbel", "category": "Warme dranken", "margin": 76},
        {"name": "Chai latte", "category": "Warme dranken", "margin": 68},
        {"name": "Thee", "category": "Warme dranken", "margin": 80},
        {"name": "Verse muntthee", "category": "Warme dranken", "margin": 78},
        # Koude dranken
        {"name": "IJskoffie pistache", "category": "Koude dranken", "margin": 68},
        {"name": "IJskoffie met slagroom", "category": "Koude dranken", "margin": 67},
        {"name": "IJskoffie stroopwafel-karamel", "category": "Koude dranken", "margin": 67},
        {"name": "Sappen", "category": "Koude dranken", "margin": 60},
        {"name": "Smoothies", "category": "Koude dranken", "margin": 62},
        {"name": "Frisdrank", "category": "Koude dranken", "margin": 65},
        # Hotdogs & Rookworsten
        {"name": "Hotdog kip", "category": "Hotdogs & Rookworsten", "margin": 58},
        {"name": "Hotdog varken", "category": "Hotdogs & Rookworsten", "margin": 56},
        {"name": "Halve rookworst", "category": "Hotdogs & Rookworsten", "margin": 60},
        {"name": "Halve rookworst brood", "category": "Hotdogs & Rookworsten", "margin": 55},
        {"name": "Bomvol broodje wit warme rookworst", "category": "Hotdogs & Rookworsten", "margin": 52},
        {"name": "Bomvol broodje bruin warme rookworst", "category": "Hotdogs & Rookworsten", "margin": 52},
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

    # Base daily demand per product (realistic quantities for a Dutch breakfast/lunch spot)
    base_demand = {
        # Ontbijt
        "Klein ontbijt": 8,
        "Middel ontbijt": 12,
        "Groot ontbijt wit": 6,
        "Groot ontbijt bruin": 6,
        # Lunch broodjes
        "Bagel roomkaas & zalm": 5,
        "Hemaatje wit met roomkaas": 10,
        "Hemaatje bruin met roomkaas": 10,
        "Hemaatje wit mozzarella & tomaat": 8,
        "Hemaatje bruin mozzarella & tomaat": 8,
        "Hemaatje wit tonijnsalade": 7,
        "Hemaatje bruin tonijnsalade": 7,
        "Hemaatje wit pulled chicken": 6,
        "Hemaatje bruin pulled chicken": 6,
        "Bomvol broodje wit gezond": 5,
        "Bomvol broodje bruin gezond": 5,
        "Bomvol broodje wit kip": 7,
        "Bomvol broodje bruin kip": 7,
        "Bomvol broodje wit grillworst": 6,
        "Bomvol broodje bruin grillworst": 6,
        # Warme broodjes
        "Ciabatta pittige kip": 6,
        "Ciabatta tuna melt": 5,
        "Croque monsieur": 8,
        "Tosti ham-kaas": 10,
        "Glutenvrije tosti ham-kaas": 3,
        "Tosti pulled chicken": 5,
        # Warme snacks
        "Kaasstengel": 12,
        "Ovenkroket": 10,
        "Broodje ovenkroket": 6,
        "Kippensoep": 8,
        "Feta-spinaziebroodje": 5,
        # IJs
        "Softijs klein": 10,
        "Softijs groot": 8,
        "Softijs bakje": 6,
        "Schepijs hoorn": 7,
        "Schepijs bakje klein": 4,
        "Schepijs bakje middel": 5,
        "Schepijs bakje groot": 4,
        "Slush standaard": 5,
        "Slush Blue Citrus": 4,
        "Slush Mango": 4,
        "Slush Groene appel": 3,
        "Slush Watermeloen": 4,
        # Warme dranken
        "Koffie": 35,
        "Cappuccino klein": 12,
        "Cappuccino groot": 10,
        "Latte machiato": 8,
        "Koffie verkeerd": 10,
        "Espresso": 15,
        "Espresso dubbel": 8,
        "Chai latte": 6,
        "Thee": 14,
        "Verse muntthee": 5,
        # Koude dranken
        "IJskoffie pistache": 5,
        "IJskoffie met slagroom": 4,
        "IJskoffie stroopwafel-karamel": 4,
        "Sappen": 10,
        "Smoothies": 6,
        "Frisdrank": 12,
        # Hotdogs & Rookworsten
        "Hotdog kip": 6,
        "Hotdog varken": 8,
        "Halve rookworst": 5,
        "Halve rookworst brood": 6,
        "Bomvol broodje wit warme rookworst": 5,
        "Bomvol broodje bruin warme rookworst": 5,
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
