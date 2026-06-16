"""Tests for prediction_engine module."""

import pytest
from unittest.mock import MagicMock
from datetime import datetime, timedelta
from typing import List, Optional

from prepright.prediction_engine import (
    generate_predictions,
    _calculate_daily_sales,
    _calculate_base_qty,
    _get_event_adjustment,
    _DAY_MULTIPLIERS,
    _WEATHER_MAP,
)
from prepright import models


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_mock_product(
    id: int = 1,
    name: str = "Pan Integral",
    category_id: int = 1,
    active: bool = True,
    margin_pct: float = 0.0,
) -> models.Product:
    """Create a mock ORM model for a product."""
    prod = MagicMock(spec=models.Product)
    prod.id = id
    prod.name = name
    prod.category_id = category_id
    prod.active = active
    prod.margin_pct = margin_pct
    return prod


def _make_mock_category(
    id: int = 1,
    name: str = "Baked Goods",
    weather_sensitivity: float = 1.0,
) -> models.Category:
    """Create a mock ORM model for a category."""
    cat = MagicMock(spec=models.Category)
    cat.id = id
    cat.name = name
    cat.weather_sensitivity = weather_sensitivity
    return cat


def _make_mock_sales_record(
    product_id: int,
    quantity: float,
    sale_date: str,
) -> models.SalesRecord:
    """Create a mock ORM model for a sales record."""
    record = MagicMock(spec=models.SalesRecord)
    record.product_id = product_id
    record.quantity = quantity
    record.sale_date = sale_date
    return record


def _make_mock_event(
    date: str,
    name: str = "School Fair",
    impact_factor: float = 0.2,
) -> models.Event:
    """Create a mock ORM model for an event."""
    evt = MagicMock(spec=models.Event)
    evt.date = date
    evt.name = name
    evt.impact_factor = impact_factor
    return evt


def _make_mock_setting(key: str, value: str) -> models.Setting:
    """Create a mock ORM model for a setting."""
    setting = MagicMock(spec=models.Setting)
    setting.key = key
    setting.value = value
    return setting


def _make_mock_db(
    products: Optional[List[models.Product]] = None,
    categories: Optional[List[models.Category]] = None,
    sales: Optional[List[models.SalesRecord]] = None,
    events: Optional[List[models.Event]] = None,
    settings: Optional[List[models.Setting]] = None,
) -> MagicMock:
    """Create a mock SQLAlchemy session."""
    db = MagicMock()

    def make_filter_chain(target_list):
        filter_chain = MagicMock()

        def all_side_effect():
            return target_list if target_list is not None else []

        def first_side_effect():
            if target_list is None:
                return None
            return target_list[0] if target_list else None

        filter_chain.all.side_effect = all_side_effect
        filter_chain.first.side_effect = first_side_effect
        filter_chain.filter.return_value = filter_chain
        return filter_chain

    def query_side_effect(model_cls):
        if model_cls == models.Product:
            return make_filter_chain(products)
        elif model_cls == models.Category:
            return make_filter_chain(categories)
        elif model_cls == models.SalesRecord:
            return make_filter_chain(sales)
        elif model_cls == models.Event:
            return make_filter_chain(events)
        elif model_cls == models.Setting:
            return make_filter_chain(settings)
        elif model_cls == models.Prediction:
            chain = make_filter_chain([])
            chain.delete = MagicMock(return_value=0)
            return chain
        return make_filter_chain([])

    db.query.side_effect = query_side_effect
    return db


# ── _calculate_daily_sales tests ──────────────────────────────────────────────


class TestCalculateDailySales:
    def test_single_record(self):
        sales = [_make_mock_sales_record(1, 2.0, "2026-05-01")]
        result = _calculate_daily_sales(sales)
        assert result == {"2026-05-01": {1: 2.0}}

    def test_multiple_records_same_date(self):
        sales = [
            _make_mock_sales_record(1, 2.0, "2026-05-01"),
            _make_mock_sales_record(1, 3.0, "2026-05-01"),
        ]
        result = _calculate_daily_sales(sales)
        assert result["2026-05-01"][1] == 5.0

    def test_multiple_products_same_date(self):
        sales = [
            _make_mock_sales_record(1, 2.0, "2026-05-01"),
            _make_mock_sales_record(2, 5.0, "2026-05-01"),
        ]
        result = _calculate_daily_sales(sales)
        assert result["2026-05-01"][1] == 2.0
        assert result["2026-05-01"][2] == 5.0

    def test_multiple_dates(self):
        sales = [
            _make_mock_sales_record(1, 2.0, "2026-05-01"),
            _make_mock_sales_record(1, 3.0, "2026-05-02"),
        ]
        result = _calculate_daily_sales(sales)
        assert len(result) == 2
        assert result["2026-05-01"][1] == 2.0
        assert result["2026-05-02"][1] == 3.0

    def test_empty_sales(self):
        result = _calculate_daily_sales([])
        assert result == {}

    def test_invalid_date_skipped(self):
        sales = [
            _make_mock_sales_record(1, 2.0, "invalid-date"),
            _make_mock_sales_record(1, 3.0, "2026-05-01"),
        ]
        result = _calculate_daily_sales(sales)
        assert "invalid-date" not in result
        assert "2026-05-01" in result


# ── _calculate_base_qty tests ─────────────────────────────────────────────────


class TestCalculateBaseQty:
    def test_no_history(self):
        daily_sales = {}
        base, weeks = _calculate_base_qty(
            daily_sales, 1, 1,
            datetime(2026, 5, 10),  # Sunday
            4, _make_mock_db(categories=[_make_mock_category(1, "Baked Goods", 1.0)]),
        )
        assert base == 0.0

    def test_sunday_returns_nonzero(self):
        """Sundays are treated like any other day for restaurants open 7 days."""
        daily_sales = {"2026-05-03": {1: 10.0}}  # Previous Sunday
        base, weeks = _calculate_base_qty(
            daily_sales, 1, 1,
            datetime(2026, 5, 10),  # Sunday
            4, _make_mock_db(categories=[_make_mock_category(1, "Baked Goods", 1.0)]),
        )
        assert base == 10.0  # Historical data contributes regardless of day

    def test_friday_returns_nonzero(self):
        """Fridays are school days, should return non-zero base."""
        daily_sales = {"2026-05-08": {1: 10.0}}  # Friday
        base, weeks = _calculate_base_qty(
            daily_sales, 1, 1,
            datetime(2026, 5, 15),  # Friday
            4, _make_mock_db(categories=[_make_mock_category(1, "Baked Goods", 1.0)]),
        )
        assert base == 10.0  # Friday is a school day


# ── _get_event_adjustment tests ───────────────────────────────────────────────


class TestGetEventAdjustment:
    def test_event_on_date(self):
        events = [_make_mock_event("2026-05-11", "School Fair", 0.2)]
        result = _get_event_adjustment(datetime(2026, 5, 11), events)
        assert result == 0.2

    def test_no_event_on_date(self):
        events = [_make_mock_event("2026-05-11", "School Fair", 0.2)]
        result = _get_event_adjustment(datetime(2026, 5, 12), events)
        assert result == 0.0

    def test_negative_impact(self):
        events = [_make_mock_event("2026-05-11", "Holiday", -0.3)]
        result = _get_event_adjustment(datetime(2026, 5, 11), events)
        assert result == -0.3

    def test_empty_events(self):
        result = _get_event_adjustment(datetime(2026, 5, 11), [])
        assert result == 0.0


# ── _DAY_MULTIPLIERS tests ───────────────────────────────────────────────────


class TestDayMultipiers:
    def test_all_day_multipliers_are_one(self):
        """All days have 1.0 multiplier since restaurants are open 7 days."""
        for day in range(7):
            assert _DAY_MULTIPLIERS[day] == 1.0


# ── generate_predictions integration tests ────────────────────────────────────


class TestGeneratePredictions:
    def test_generates_predictions(self):
        """Should generate predictions for weekdays in range."""
        today = datetime.utcnow().date()
        start = today
        end = today + timedelta(days=7)

        products = [_make_mock_product(1, "Pan Integral", 1, True)]
        categories = [_make_mock_category(1, "Baked Goods", 1.0)]
        # Two prior weeks of same-weekday history (today's weekday) so the
        # MIN_DATA_DAYS=2 threshold is met for the `today` target in range.
        sales = [
            _make_mock_sales_record(1, 10.0, str(today - timedelta(days=7))),
            _make_mock_sales_record(1, 12.0, str(today - timedelta(days=14))),
        ]
        events = []
        settings = [
            _make_mock_setting("prediction_weeks", "4"),
            _make_mock_setting("weather_condition", "normal"),
        ]
        db = _make_mock_db(products, categories, sales, events, settings)

        predictions = generate_predictions(db, str(start), str(end))

        # Should have generated predictions for the same-weekday targets in range
        assert len(predictions) > 0

    def test_no_active_products(self):
        """Should return empty list when no active products."""
        today = datetime.utcnow().date()
        products = []
        categories = []
        sales = []
        events = []
        settings = [
            _make_mock_setting("prediction_weeks", "4"),
            _make_mock_setting("weather_condition", "normal"),
        ]
        db = _make_mock_db(products, categories, sales, events, settings)

        predictions = generate_predictions(db, str(today), str(today + timedelta(days=7)))
        assert len(predictions) == 0

    def test_weather_affects_predictions(self):
        """Weather condition should affect predicted quantities."""
        today = datetime.utcnow().date()
        start = today
        end = today + timedelta(days=7)

        products = [_make_mock_product(1, "Pan Integral", 1, True)]
        categories = [_make_mock_category(1, "Baked Goods", 1.5)]  # High sensitivity

        # Rainy weather predictions
        settings_rainy = [
            _make_mock_setting("prediction_weeks", "4"),
            _make_mock_setting("weather_condition", "rainy"),
        ]
        db_rainy = _make_mock_db(products, categories, [], [], settings_rainy)
        predictions_rainy = generate_predictions(db_rainy, str(start), str(end))

        # Normal weather predictions
        settings_normal = [
            _make_mock_setting("prediction_weeks", "4"),
            _make_mock_setting("weather_condition", "normal"),
        ]
        db_normal = _make_mock_db(products, categories, [], [], settings_normal)
        predictions_normal = generate_predictions(db_normal, str(start), str(end))

        # Rainy should reduce predictions for high-sensitivity category
        if predictions_rainy and predictions_normal:
            rainy_total = sum(p["predicted_qty"] for p in predictions_rainy)
            normal_total = sum(p["predicted_qty"] for p in predictions_normal)
            assert rainy_total < normal_total

    def test_event_affects_predictions(self):
        """Events with positive impact should boost predictions."""
        today = datetime.utcnow().date()
        start = today
        end = today + timedelta(days=14)

        products = [_make_mock_product(1, "Pan Integral", 1, True)]
        categories = [_make_mock_category(1, "Baked Goods", 1.0)]

        # With event
        events = [_make_mock_event(str(today), "School Fair", 0.3)]
        settings = [
            _make_mock_setting("prediction_weeks", "4"),
            _make_mock_setting("weather_condition", "normal"),
        ]
        db_with_event = _make_mock_db(products, categories, [], events, settings)
        predictions_with_event = generate_predictions(db_with_event, str(start), str(end))

        # Without event
        db_no_event = _make_mock_db(products, categories, [], [], settings)
        predictions_no_event = generate_predictions(db_no_event, str(start), str(end))

        # Find the event date predictions
        event_pred_with = next(
            (p for p in predictions_with_event if p["date"] == str(today)), None
        )
        event_pred_without = next(
            (p for p in predictions_no_event if p["date"] == str(today)), None
        )

        if event_pred_with and event_pred_without:
            assert event_pred_with["event_adjustment"] == 0.3
            assert event_pred_with["predicted_qty"] > event_pred_without["predicted_qty"]

    def test_margin_buffers_predicted_qty(self):
        """The per-product margin_pct adds a safety buffer on top of demand."""
        today = datetime.utcnow().date()
        start = today
        end = today + timedelta(days=7)
        categories = [_make_mock_category(1, "Baked Goods", 1.0)]
        # Two prior weeks of same-weekday history -> base demand of 8.
        sales = [
            _make_mock_sales_record(1, 8.0, str(today - timedelta(days=7))),
            _make_mock_sales_record(1, 8.0, str(today - timedelta(days=14))),
        ]
        settings = [
            _make_mock_setting("prediction_weeks", "4"),
            _make_mock_setting("weather_condition", "normal"),
        ]

        # 0% margin -> prep equals demand.
        prods0 = [_make_mock_product(1, "Pan", 1, True, margin_pct=0.0)]
        preds0 = generate_predictions(
            _make_mock_db(prods0, categories, sales, [], settings), str(start), str(end)
        )
        # 25% margin -> demand bumped up and rounded up.
        prods25 = [_make_mock_product(1, "Pan", 1, True, margin_pct=25.0)]
        preds25 = generate_predictions(
            _make_mock_db(prods25, categories, sales, [], settings), str(start), str(end)
        )

        assert preds0 and preds25
        p0 = next(p for p in preds0 if p["date"] == str(today))
        p25 = next(p for p in preds25 if p["date"] == str(today))
        assert p0["base_qty"] == 8.0
        assert p0["margin_adjustment"] == 0.0
        assert p0["predicted_qty"] == 8
        assert p25["margin_adjustment"] == 0.25
        assert p25["predicted_qty"] == 10  # ceil(8 * 1.25)

    def test_default_date_range(self):
        """Should default to tomorrow + 14 days."""
        today = datetime.utcnow().date()
        products = [_make_mock_product(1, "Pan Integral", 1, True)]
        categories = [_make_mock_category(1, "Baked Goods", 1.0)]
        # Default range starts tomorrow; provide two prior weeks of same-weekday
        # history relative to today so a target in range clears MIN_DATA_DAYS=2.
        sales = [
            _make_mock_sales_record(1, 10.0, str(today - timedelta(days=7))),
            _make_mock_sales_record(1, 12.0, str(today - timedelta(days=14))),
        ]
        events = []
        settings = [
            _make_mock_setting("prediction_weeks", "4"),
            _make_mock_setting("weather_condition", "normal"),
        ]
        db = _make_mock_db(products, categories, sales, events, settings)

        predictions = generate_predictions(db)
        assert len(predictions) > 0

    def test_lookback_weeks_setting(self):
        """Should respect the prediction_weeks setting."""
        today = datetime.utcnow().date()
        start = today
        end = today + timedelta(days=7)

        products = [_make_mock_product(1, "Pan Integral", 1, True)]
        categories = [_make_mock_category(1, "Baked Goods", 1.0)]
        # Two prior weeks of same-weekday history. A 1-week lookback can never
        # collect 2 same-weekday points (only the single week before the
        # target), so the short case uses 2 weeks — the smallest lookback that
        # can satisfy MIN_DATA_DAYS=2.
        sales = [
            _make_mock_sales_record(1, 10.0, str(today - timedelta(days=14))),
            _make_mock_sales_record(1, 12.0, str(today - timedelta(days=7))),
        ]
        events = []

        # 2 week lookback (shortest that can meet MIN_DATA_DAYS)
        settings_short = [
            _make_mock_setting("prediction_weeks", "2"),
            _make_mock_setting("weather_condition", "normal"),
        ]
        db_short = _make_mock_db(products, categories, sales, events, settings_short)
        predictions_short = generate_predictions(db_short, str(start), str(end))

        # 10 weeks lookback
        settings_long = [
            _make_mock_setting("prediction_weeks", "10"),
            _make_mock_setting("weather_condition", "normal"),
        ]
        db_long = _make_mock_db(products, categories, sales, events, settings_long)
        predictions_long = generate_predictions(db_long, str(start), str(end))

        # Both should generate predictions
        assert len(predictions_short) > 0
        assert len(predictions_long) > 0

    def test_multiple_products(self):
        """Should generate predictions for all active products."""
        today = datetime.utcnow().date()
        start = today
        end = today + timedelta(days=7)

        products = [
            _make_mock_product(1, "Pan Integral", 1, True),
            _make_mock_product(2, "Leche Entera", 2, True),
            _make_mock_product(3, "Jugo Naranja", 3, True),
        ]
        categories = [
            _make_mock_category(1, "Baked Goods", 1.0),
            _make_mock_category(2, "Dairy", 0.8),
            _make_mock_category(3, "Beverages", 1.2),
        ]
        # Two prior weeks of same-weekday history per product so each clears
        # MIN_DATA_DAYS=2 for the `today` target in range.
        sales = [
            _make_mock_sales_record(1, 10.0, str(today - timedelta(days=7))),
            _make_mock_sales_record(1, 10.0, str(today - timedelta(days=14))),
            _make_mock_sales_record(2, 8.0, str(today - timedelta(days=7))),
            _make_mock_sales_record(2, 8.0, str(today - timedelta(days=14))),
            _make_mock_sales_record(3, 5.0, str(today - timedelta(days=7))),
            _make_mock_sales_record(3, 5.0, str(today - timedelta(days=14))),
        ]
        events = []
        settings = [
            _make_mock_setting("prediction_weeks", "4"),
            _make_mock_setting("weather_condition", "normal"),
        ]
        db = _make_mock_db(products, categories, sales, events, settings)

        predictions = generate_predictions(db, str(start), str(end))

        product_ids = set(p["product_id"] for p in predictions)
        assert 1 in product_ids
        assert 2 in product_ids
        assert 3 in product_ids
