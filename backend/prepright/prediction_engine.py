"""Prediction engine for forecasting daily product demand."""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from math import ceil
from typing import List, Optional

from sqlalchemy.orm import Session

from prepright import models


# Day-of-week multipliers (restaurants open 7 days)
# Monday=0, Sunday=6
_DAY_MULTIPLIERS = {
    0: 1.0,   # Monday
    1: 1.0,   # Tuesday
    2: 1.0,   # Wednesday
    3: 1.0,   # Thursday
    4: 1.0,   # Friday
    5: 1.0,   # Saturday
    6: 1.0,   # Sunday
}

# Weather adjustment map per category sensitivity
_WEATHER_MAP = {
    "normal": 0.0,
    "rainy": -0.15,
    "cold": -0.20,
    "hot": 0.10,
}


def _get_setting(db: Session, key: str, default: str = "4") -> str:
    """Get a setting value with a default fallback."""
    setting = db.query(models.Setting).filter(models.Setting.key == key).first()
    return setting.value if setting else default


def _get_weather_condition(db: Session) -> str:
    """Get current weather condition from settings."""
    return _get_setting(db, "weather_condition", "normal")


def _get_lookback_weeks(db: Session) -> int:
    """Get the number of weeks to look back for predictions."""
    val = _get_setting(db, "prediction_weeks", "4")
    try:
        return max(1, int(val))
    except (ValueError, TypeError):
        return 4


def _calculate_daily_sales(sales: List[models.SalesRecord]) -> dict:
    """Group sales records by date and product, return {date_str: {product_id: total_qty}}."""
    daily = defaultdict(lambda: defaultdict(float))
    for record in sales:
        try:
            date = datetime.strptime(record.sale_date, "%Y-%m-%d").date()
        except (ValueError, AttributeError):
            continue
        daily[str(date)][record.product_id] += record.quantity
    return dict(daily)


def _calculate_base_qty(
    daily_sales: dict,
    product_id: int,
    category_id: int,
    target_date: datetime,
    lookback_weeks: int,
    db: Session,
) -> tuple:
    """Calculate base predicted quantity for a product on a target date."""
    target_day_of_week = target_date.weekday()

    # Get the category's weather sensitivity
    category = (
        db.query(models.Category)
        .filter(models.Category.id == category_id)
        .first()
    )
    weather_sensitivity = category.weather_sensitivity if category else 1.0

    # Collect only same day-of-week history
    same_day_history = []

    # Normalize to a plain date so comparisons work whether the caller passes
    # a date or a datetime.
    target_day = target_date.date() if isinstance(target_date, datetime) else target_date
    cutoff_date = target_day - timedelta(weeks=lookback_weeks)

    for date_str, product_sales in daily_sales.items():
        if date_str < str(cutoff_date):
            continue
        if product_id not in product_sales:
            continue

        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        # Only count days strictly *before* the prediction date — the same
        # weekday in previous weeks. Never fold in the target day's own actuals
        # (or any later day) when predicting today or a past date.
        if date_obj >= target_day:
            continue
        if date_obj.weekday() == target_day_of_week:
            same_day_history.append(product_sales[product_id])

    # Base quantity: average of same day-of-week only
    base = 0.0
    data_days = len(same_day_history)

    if same_day_history:
        base = sum(same_day_history) / len(same_day_history)

    return base, data_days


def _get_event_adjustment(target_date: datetime, events: List[models.Event]) -> float:
    """Calculate event impact for a given date."""
    date_str = target_date.strftime("%Y-%m-%d")
    for event in events:
        if event.date == date_str and event.impact_factor:
            return event.impact_factor
    return 0.0





def generate_predictions(
    db: Session,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> List[dict]:
    """
    Generate demand predictions for all active products.

    Args:
        db: SQLAlchemy session
        start_date: Start date string (YYYY-MM-DD), defaults to tomorrow
        end_date: End date string (YYYY-MM-DD), defaults to 2 weeks from start

    Returns:
        List of prediction dicts ready to be stored
    """
    today = datetime.now(timezone.utc).date()
    tomorrow = today + timedelta(days=1)

    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
    else:
        start = tomorrow

    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    else:
        end = start + timedelta(days=14)

    lookback_weeks = _get_lookback_weeks(db)
    weather_condition = _get_weather_condition(db)
    weather_adjustment = _WEATHER_MAP.get(weather_condition, 0.0)

    # Fetch all events
    events = db.query(models.Event).order_by(models.Event.date).all()
    event_map = {e.date: e for e in events}

    # Fetch all active products with categories
    products = (
        db.query(models.Product)
        .filter(models.Product.active == True)
        .all()
    )

    # Fetch sales records from lookback period
    lookback_start = start - timedelta(weeks=lookback_weeks)
    sales = (
        db.query(models.SalesRecord)
        .filter(models.SalesRecord.sale_date >= str(lookback_start))
        .all()
    )

    # Group sales by date
    daily_sales = _calculate_daily_sales(sales)

    # Cache weather sensitivity per category to avoid per-product queries
    cat_sensitivity: dict[int, float] = {}
    for prod in products:
        if prod.category_id not in cat_sensitivity:
            cat = (
                db.query(models.Category)
                .filter(models.Category.id == prod.category_id)
                .first()
            )
            cat_sensitivity[prod.category_id] = cat.weather_sensitivity if cat else 1.0

    # Minimum same-day-of-week data points required before we trust predictions
    MIN_DATA_DAYS = 2

    predictions = []
    current = start

    while current <= end:
        for product in products:
            # Calculate base quantity and count matching historical days
            base_qty, data_days = _calculate_base_qty(
                daily_sales,
                product.id,
                product.category_id,
                current,
                lookback_weeks,
                db,
            )

            # Skip predictions if not enough same-day historical data
            if data_days < MIN_DATA_DAYS:
                continue

            if base_qty == 0.0:
                continue

            # Apply weather adjustment (scaled by category sensitivity, cached)
            weather_adj = weather_adjustment * cat_sensitivity.get(product.category_id, 1.0)
            weather_adjusted = base_qty * (1 + weather_adj)

            # Apply event adjustment
            date_str = current.strftime("%Y-%m-%d")
            event_adj = _get_event_adjustment(current, events)
            event_adjusted = weather_adjusted * (1 + event_adj)

            # Apply day-of-week multiplier
            day_mult = _DAY_MULTIPLIERS.get(current.weekday(), 1.0)
            predicted_qty = event_adjusted * day_mult

            predictions.append({
                "date": date_str,
                "product_id": product.id,
                "product_name": product.name,
                "predicted_qty": ceil(predicted_qty),
                "base_qty": round(base_qty, 2),
                "weather_adjustment": round(weather_adj, 4),
                "event_adjustment": round(event_adj, 4),

            })

        current += timedelta(days=1)

    return predictions
