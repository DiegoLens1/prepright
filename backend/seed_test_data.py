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

    # Products grouped by category. Margins default to 0 (no prep buffer);
    # adjust per product on the Products page if a buffer is desired.
    default_products = [
        # Ontbijt
        {"name": "Klein ontbijt", "category": "Ontbijt"},
        {"name": "Middel ontbijt", "category": "Ontbijt"},
        {"name": "Groot ontbijt wit", "category": "Ontbijt"},
        {"name": "Groot ontbijt bruin", "category": "Ontbijt"},
        # Lunch broodjes
        {"name": "Bagel roomkaas & zalm", "category": "Lunch broodjes"},
        {"name": "Hemaatje wit met roomkaas", "category": "Lunch broodjes"},
        {"name": "Hemaatje bruin met roomkaas", "category": "Lunch broodjes"},
        {"name": "Hemaatje wit mozzarella & tomaat", "category": "Lunch broodjes"},
        {"name": "Hemaatje bruin mozzarella & tomaat", "category": "Lunch broodjes"},
        {"name": "Hemaatje wit tonijnsalade", "category": "Lunch broodjes"},
        {"name": "Hemaatje bruin tonijnsalade", "category": "Lunch broodjes"},
        {"name": "Hemaatje wit pulled chicken", "category": "Lunch broodjes"},
        {"name": "Hemaatje bruin pulled chicken", "category": "Lunch broodjes"},
        {"name": "Bomvol broodje wit gezond", "category": "Lunch broodjes"},
        {"name": "Bomvol broodje bruin gezond", "category": "Lunch broodjes"},
        {"name": "Bomvol broodje wit kip", "category": "Lunch broodjes"},
        {"name": "Bomvol broodje bruin kip", "category": "Lunch broodjes"},
        {"name": "Bomvol broodje wit grillworst", "category": "Lunch broodjes"},
        {"name": "Bomvol broodje bruin grillworst", "category": "Lunch broodjes"},
        # Warme broodjes
        {"name": "Ciabatta pittige kip", "category": "Warme broodjes"},
        {"name": "Ciabatta tuna melt", "category": "Warme broodjes"},
        {"name": "Croque monsieur", "category": "Warme broodjes"},
        {"name": "Tosti ham-kaas", "category": "Warme broodjes"},
        {"name": "Glutenvrije tosti ham-kaas", "category": "Warme broodjes"},
        {"name": "Tosti pulled chicken", "category": "Warme broodjes"},
        # Warme snacks
        {"name": "Kaasstengel", "category": "Warme snacks"},
        {"name": "Ovenkroket", "category": "Warme snacks"},
        {"name": "Broodje ovenkroket", "category": "Warme snacks"},
        {"name": "Kippensoep", "category": "Warme snacks"},
        {"name": "Feta-spinaziebroodje", "category": "Warme snacks"},
        # IJs
        {"name": "Softijs klein", "category": "IJs"},
        {"name": "Softijs groot", "category": "IJs"},
        {"name": "Softijs bakje", "category": "IJs"},
        {"name": "Schepijs hoorn", "category": "IJs"},
        {"name": "Schepijs bakje klein", "category": "IJs"},
        {"name": "Schepijs bakje middel", "category": "IJs"},
        {"name": "Schepijs bakje groot", "category": "IJs"},
        {"name": "Slush standaard", "category": "IJs"},
        {"name": "Slush Blue Citrus", "category": "IJs"},
        {"name": "Slush Mango", "category": "IJs"},
        {"name": "Slush Groene appel", "category": "IJs"},
        {"name": "Slush Watermeloen", "category": "IJs"},
        # Warme dranken
        {"name": "Koffie", "category": "Warme dranken"},
        {"name": "Cappuccino klein", "category": "Warme dranken"},
        {"name": "Cappuccino groot", "category": "Warme dranken"},
        {"name": "Latte machiato", "category": "Warme dranken"},
        {"name": "Koffie verkeerd", "category": "Warme dranken"},
        {"name": "Espresso", "category": "Warme dranken"},
        {"name": "Espresso dubbel", "category": "Warme dranken"},
        {"name": "Chai latte", "category": "Warme dranken"},
        {"name": "Thee", "category": "Warme dranken"},
        {"name": "Verse muntthee", "category": "Warme dranken"},
        # Koude dranken
        {"name": "IJskoffie pistache", "category": "Koude dranken"},
        {"name": "IJskoffie met slagroom", "category": "Koude dranken"},
        {"name": "IJskoffie stroopwafel-karamel", "category": "Koude dranken"},
        {"name": "Sappen", "category": "Koude dranken"},
        {"name": "Smoothies", "category": "Koude dranken"},
        {"name": "Frisdrank", "category": "Koude dranken"},
        # Hotdogs & Rookworsten
        {"name": "Hotdog kip", "category": "Hotdogs & Rookworsten"},
        {"name": "Hotdog varken", "category": "Hotdogs & Rookworsten"},
        {"name": "Halve rookworst", "category": "Hotdogs & Rookworsten"},
        {"name": "Halve rookworst brood", "category": "Hotdogs & Rookworsten"},
        {"name": "Bomvol broodje wit warme rookworst", "category": "Hotdogs & Rookworsten"},
        {"name": "Bomvol broodje bruin warme rookworst", "category": "Hotdogs & Rookworsten"},
    ]

    cat_map = {c.name: c.id for c in existing_cats.values()}

    products = []
    for p in default_products:
        existing = db.query(models.Product).filter(models.Product.name == p["name"]).first()
        if not existing:
            prod = models.Product(
                name=p["name"],
                category_id=cat_map[p["category"]],
                margin_pct=p.get("margin", 0),
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
