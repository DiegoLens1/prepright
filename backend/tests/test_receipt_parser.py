"""Tests for receipt_parser module."""

import pytest
from unittest.mock import MagicMock, Mock
from typing import List, Optional

from prepright.receipt_parser import (
    ReceiptTemplate,
    ReceiptParser,
    ParsedLine,
    ParseResult,
    match_products,
)
from prepright import models, schemas


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_mock_template(
    name: str = "HEMA",
    source_keyword: str = "HEMA",
    line_pattern: str = r"^\d{8}\s+(.+?)\s+(\d+\.\d+)$",
    product_name_group: str = "name",
    quantity_group: str = "qty",
    price_group: str = "price",
    line_prefix: Optional[str] = None,
    line_suffix: Optional[str] = None,
    name_normalize: Optional[str] = None,
    active: bool = True,
) -> models.ReceiptTemplate:
    """Create a mock ORM model for a receipt template."""
    tmpl = MagicMock()
    tmpl.name = name
    tmpl.source_keyword = source_keyword
    tmpl.line_pattern = line_pattern
    tmpl.product_name_group = product_name_group
    tmpl.quantity_group = quantity_group
    tmpl.price_group = price_group
    tmpl.line_prefix = line_prefix
    tmpl.line_suffix = line_suffix
    tmpl.name_normalize = name_normalize
    tmpl.active = active
    return tmpl


def _make_mock_product(
    id: int = 1,
    name: str = "Leche Entera",
    active: bool = True,
    aliases: Optional[List[str]] = None,
) -> models.Product:
    """Create a mock ORM model for a product."""
    prod = MagicMock(spec=models.Product)
    prod.id = id
    prod.name = name
    prod.active = active
    alias_objs = []
    for a in (aliases or []):
        alias_obj = MagicMock(spec=models.ProductAlias)
        alias_obj.alias_name = a
        alias_objs.append(alias_obj)
    # Make aliases iterable (MagicMock iterates to empty by default)
    prod.aliases = alias_objs
    return prod


def _make_mock_db(
    templates: Optional[List[models.ReceiptTemplate]] = None,
    products: Optional[List[models.Product]] = None,
) -> MagicMock:
    """Create a mock SQLAlchemy session."""
    db = MagicMock()

    def make_filter_chain(target_list, is_product=False):
        """Create a filter chain that returns items from target_list on .all() or .first()."""
        filter_chain = MagicMock()

        def all_side_effect():
            if target_list is None:
                return []
            # Filter out inactive products when queried
            if is_product:
                return [p for p in target_list if not hasattr(p, 'active') or p.active is not False]
            return target_list if target_list is not None else []

        def first_side_effect():
            if target_list is None:
                return None
            if is_product:
                for p in target_list:
                    if not hasattr(p, 'active') or p.active is not False:
                        return p
                return None
            return (target_list + [None])[0]

        filter_chain.all.side_effect = all_side_effect
        filter_chain.first.side_effect = first_side_effect

        # Chaining .filter() returns the same chain
        filter_chain.filter.return_value = filter_chain
        return filter_chain

    def query_side_effect(model_cls):
        if model_cls == models.ReceiptTemplate:
            return make_filter_chain(templates, is_product=False)
        elif model_cls == models.Product:
            return make_filter_chain(products, is_product=True)
        return make_filter_chain([], is_product=False)

    db.query.side_effect = query_side_effect
    return db


# ── ReceiptTemplate tests ─────────────────────────────────────────────────────


class TestReceiptTemplate:
    def test_from_db(self):
        tmpl = _make_mock_template()
        rt = ReceiptTemplate.from_db(tmpl)
        assert rt.name == "HEMA"
        assert rt.source_keyword == "HEMA"
        assert rt.line_pattern == r"^\d{8}\s+(.+?)\s+(\d+\.\d+)$"
        assert rt.product_name_group == "name"
        assert rt.quantity_group == "qty"
        assert rt.price_group == "price"
        assert rt.line_prefix is None
        assert rt.line_suffix is None
        assert rt.name_normalize is None

    def test_compile_pattern(self):
        tmpl = _make_mock_template()
        rt = ReceiptTemplate.from_db(tmpl)
        compiled = rt.compile_pattern()
        assert compiled.match("20260511 Pan Integral 5.99")

    def test_normalize_no_rules(self):
        tmpl = _make_mock_template()
        rt = ReceiptTemplate.from_db(tmpl)
        assert rt.normalize_name("  Leche Entera  ") == "  Leche Entera  "

    def test_normalize_single_rule(self):
        tmpl = _make_mock_template(name_normalize="Pan:Pan de,Integral:Integr")
        rt = ReceiptTemplate.from_db(tmpl)
        assert rt.normalize_name("Pan Integral") == "Pan de Integr"

    def test_normalize_multiple_rules(self):
        tmpl = _make_mock_template(name_normalize="Entera:Gruesa,Leche:Lacteo")
        rt = ReceiptTemplate.from_db(tmpl)
        result = rt.normalize_name("Leche Entera")
        assert result == "Lacteo Gruesa"

    def test_normalize_empty_rules(self):
        tmpl = _make_mock_template(name_normalize=",,")
        rt = ReceiptTemplate.from_db(tmpl)
        assert rt.normalize_name("Leche") == "Leche"


# ── ReceiptParser.detect_template tests ──────────────────────────────────────


class TestDetectTemplate:
    def test_detect_by_keyword(self):
        tmpl = _make_mock_template(name="HEMA", source_keyword="HEMA")
        db = _make_mock_db(templates=[tmpl])
        parser = ReceiptParser(db)

        result = parser.detect_template("Total: 150.00 HEMA")
        assert result is not None
        assert result.name == "HEMA"

    def test_detect_longest_keyword(self):
        tmpl1 = _make_mock_template(name="HEMA", source_keyword="HE")
        tmpl2 = _make_mock_template(name="HEMA_FULL", source_keyword="HEMA")
        db = _make_mock_db(templates=[tmpl1, tmpl2])
        parser = ReceiptParser(db)

        result = parser.detect_template("Total: 150.00 HEMA")
        assert result is not None
        assert result.name == "HEMA_FULL"

    def test_detect_case_insensitive(self):
        tmpl = _make_mock_template(name="HEMA", source_keyword="Hema")
        db = _make_mock_db(templates=[tmpl])
        parser = ReceiptParser(db)

        result = parser.detect_template("Total: 150.00 HEMA")
        assert result is not None
        assert result.name == "HEMA"

    def test_no_match(self):
        tmpl = _make_mock_template(name="HEMA", source_keyword="HEMA")
        db = _make_mock_db(templates=[tmpl])
        parser = ReceiptParser(db)

        result = parser.detect_template("Total: 150.00 WALLY")
        assert result is None

    def test_no_templates(self):
        db = _make_mock_db(templates=[])
        parser = ReceiptParser(db)
        result = parser.detect_template("Total: 150.00 HEMA")
        assert result is None


# ── ReceiptParser.parse_receipt tests ─────────────────────────────────────────


class TestParseReceipt:
    def test_parse_with_explicit_template(self):
        tmpl = _make_mock_template(
            name="HEMA",
            line_pattern=r"(?P<name>\d{8})\s+(?P<qty>\d+)\s+(?P<name2>.+?)\s+(?P<price>\d+\.\d+)",
            product_name_group="name2",
            quantity_group="qty",
            price_group="price",
        )
        db = _make_mock_db(templates=[tmpl])
        parser = ReceiptParser(db)

        result = parser.parse_receipt(
            "20260511 1 Pan Integral 5.99\n20260512 2 Leche Entera 3.50",
            template_name="HEMA",
        )
        assert result.template_name == "HEMA"
        assert len(result.lines) == 2
        assert result.lines[0].product_name == "Pan Integral"
        assert result.lines[0].price == 5.99
        assert result.lines[1].product_name == "Leche Entera"
        assert result.lines[1].price == 3.50
        assert result.parsed_line_count == 2
        assert result.raw_line_count == 2

    def test_parse_no_template_found(self):
        db = _make_mock_db(templates=[])
        parser = ReceiptParser(db)

        result = parser.parse_receipt("some random text", template_name="NonExistent")
        assert result.template_name == "none"
        assert len(result.unmatched) == 1
        assert result.parsed_line_count == 0

    def test_parse_auto_detect(self):
        tmpl = _make_mock_template(
            name="HEMA",
            source_keyword="HEMA",
            line_pattern=r"(?P<name>\d{8})\s+(?P<qty>\d+)\s+(?P<name2>.+?)\s+(?P<price>\d+\.\d+)",
            product_name_group="name2",
            quantity_group="qty",
            price_group="price",
        )
        db = _make_mock_db(templates=[tmpl])
        parser = ReceiptParser(db)

        result = parser.parse_receipt("20260511 1 Pan Integral 5.99\nHEMA Store")
        assert result.template_name == "HEMA"
        assert len(result.lines) == 1
        assert result.lines[0].product_name == "Pan Integral"

    def test_parse_with_prefix_suffix(self):
        tmpl = _make_mock_template(
            name="CUSTOM",
            source_keyword="CUSTOM",
            line_pattern=r"(?P<name>.+?)\s+(?P<qty>\d+)\s+(?P<price>\d+\.\d+)",
            product_name_group="name",
            quantity_group="qty",
            price_group="price",
            line_prefix=">>",
            line_suffix="<<",
        )
        db = _make_mock_db(templates=[tmpl])
        parser = ReceiptParser(db)

        result = parser.parse_receipt(">>Pan Integral 1 5.99<<\n>>Leche 2 3.50<<\nCUSTOM Store")
        assert len(result.lines) == 2
        assert result.lines[0].product_name == "Pan Integral"
        assert result.lines[1].product_name == "Leche"

    def test_parse_with_normalization(self):
        tmpl = _make_mock_template(
            name="HEMA",
            line_pattern=r"(?P<name>\d{8})\s+(?P<qty>\d+)\s+(?P<name2>.+?)\s+(?P<price>\d+\.\d+)",
            product_name_group="name2",
            quantity_group="qty",
            price_group="price",
            name_normalize="Entera:Gruesa",
        )
        db = _make_mock_db(templates=[tmpl])
        parser = ReceiptParser(db)

        result = parser.parse_receipt("20260511 1 Leche Entera 3.50\nHEMA")
        assert result.lines[0].product_name == "Leche Gruesa"

    def test_parse_empty_lines(self):
        tmpl = _make_mock_template(
            name="HEMA",
            line_pattern=r"(?P<name>\d{8})\s+(?P<qty>\d+)\s+(?P<name2>.+?)\s+(?P<price>\d+\.\d+)",
            product_name_group="name2",
            quantity_group="qty",
            price_group="price",
        )
        db = _make_mock_db(templates=[tmpl])
        parser = ReceiptParser(db)

        result = parser.parse_receipt("\n\n20260511 1 Pan 5.99\n\nHEMA")
        assert len(result.lines) == 1
        assert result.lines[0].product_name == "Pan"

    def test_parse_unmatched_lines(self):
        tmpl = _make_mock_template(
            name="HEMA",
            line_pattern=r"(?P<name>\d{8})\s+(?P<qty>\d+)\s+(?P<name2>.+?)\s+(?P<price>\d+\.\d+)",
            product_name_group="name2",
            quantity_group="qty",
            price_group="price",
        )
        db = _make_mock_db(templates=[tmpl])
        parser = ReceiptParser(db)

        result = parser.parse_receipt("20260511 1 Pan 5.99\nthis doesn't match\nHEMA")
        assert len(result.lines) == 1
        assert len(result.unmatched) == 2  # "this doesn't match" + "HEMA"
        assert "this doesn't match" in result.unmatched

    def test_parse_price_with_comma(self):
        tmpl = _make_mock_template(
            name="HEMA",
            line_pattern=r"(?P<name>\d{8})\s+(?P<qty>\d+)\s+(?P<name2>.+?)\s+(?P<price>\d+[,\.]\d+)",
            product_name_group="name2",
            quantity_group="qty",
            price_group="price",
        )
        db = _make_mock_db(templates=[tmpl])
        parser = ReceiptParser(db)

        result = parser.parse_receipt("20260511 1 Pan 5,99\nHEMA")
        assert result.lines[0].price == 5.99

    def test_parse_default_quantity(self):
        tmpl = _make_mock_template(
            name="HEMA",
            line_pattern=r"(?P<name>\d{8})\s+(?P<qty>\d+)\s+(?P<name2>.+?)\s+(?P<price>\d+\.\d+)",
            product_name_group="name2",
            quantity_group="qty",
            price_group="price",
        )
        db = _make_mock_db(templates=[tmpl])
        parser = ReceiptParser(db)

        # Template expects qty group but line doesn't have it -- should catch exception
        # and add to unmatched
        result = parser.parse_receipt("20260511 Pan 5.99")
        # This will fail because group(2) is None -> float(None) raises ValueError
        # So it goes to unmatched
        assert len(result.unmatched) >= 1


# ── match_products tests ──────────────────────────────────────────────────────


class TestMatchProducts:
    def test_exact_alias_match(self):
        prod = _make_mock_product(id=1, name="Leche Entera", aliases=["leche entera"])
        db = _make_mock_db(products=[prod])

        parsed = ParseResult(
            template_name="HEMA",
            lines=[ParsedLine(product_name="leche entera", quantity=1.0, price=3.50)],
        )

        matches = match_products(parsed, db)
        assert len(matches) == 1
        assert matches[0].product_id == 1
        assert matches[0].confidence == "high"
        assert matches[0].matched_name == "Leche Entera"

    def test_name_contains_match(self):
        prod = _make_mock_product(id=1, name="Leche Entera 1L", aliases=[])
        db = _make_mock_db(products=[prod])

        parsed = ParseResult(
            template_name="HEMA",
            lines=[ParsedLine(product_name="Leche Entera", quantity=2.0, price=7.00)],
        )

        matches = match_products(parsed, db)
        assert len(matches) == 1
        assert matches[0].confidence == "high"

    def test_alias_contains_match(self):
        prod = _make_mock_product(id=1, name="Leche Entera 1L", aliases=["leche"])
        db = _make_mock_db(products=[prod])

        parsed = ParseResult(
            template_name="HEMA",
            lines=[ParsedLine(product_name="Leche fresca", quantity=1.0, price=4.00)],
        )

        matches = match_products(parsed, db)
        assert len(matches) == 1
        assert matches[0].confidence == "medium"

    def test_keyword_overlap_match(self):
        prod = _make_mock_product(id=1, name="Pan Integral", aliases=[])
        db = _make_mock_db(products=[prod])

        parsed = ParseResult(
            template_name="HEMA",
            lines=[ParsedLine(product_name="Pan de integral", quantity=1.0, price=5.99)],
        )

        matches = match_products(parsed, db)
        assert len(matches) == 1
        assert matches[0].confidence == "medium"

    def test_no_match(self):
        prod = _make_mock_product(id=1, name="Leche Entera", aliases=["leche"])
        db = _make_mock_db(products=[prod])

        parsed = ParseResult(
            template_name="HEMA",
            lines=[ParsedLine(product_name="Manzana Roja", quantity=3.0, price=6.00)],
        )

        matches = match_products(parsed, db)
        assert len(matches) == 0

    def test_no_products_in_db(self):
        db = _make_mock_db(products=[])

        parsed = ParseResult(
            template_name="HEMA",
            lines=[ParsedLine(product_name="Pan", quantity=1.0, price=5.99)],
        )

        matches = match_products(parsed, db)
        assert len(matches) == 0

    def test_multiple_lines(self):
        prod1 = _make_mock_product(id=1, name="Leche Entera", aliases=["leche"])
        prod2 = _make_mock_product(id=2, name="Pan Integral", aliases=["pan"])
        db = _make_mock_db(products=[prod1, prod2])

        parsed = ParseResult(
            template_name="HEMA",
            lines=[
                ParsedLine(product_name="leche", quantity=2.0, price=7.00),
                ParsedLine(product_name="Pan", quantity=1.0, price=5.99),
            ],
        )

        matches = match_products(parsed, db)
        assert len(matches) == 2
        assert matches[0].product_id == 1
        assert matches[1].product_id == 2

    def test_case_insensitive_alias(self):
        prod = _make_mock_product(id=1, name="Leche Entera", aliases=["LECHE"])
        db = _make_mock_db(products=[prod])

        parsed = ParseResult(
            template_name="HEMA",
            lines=[ParsedLine(product_name="leche entera", quantity=1.0, price=3.50)],
        )

        matches = match_products(parsed, db)
        assert len(matches) == 1
        assert matches[0].confidence == "high"

    def test_inactive_product_skipped(self):
        prod = _make_mock_product(id=1, name="Leche Entera", aliases=["leche"], active=False)
        db = _make_mock_db(products=[prod])

        parsed = ParseResult(
            template_name="HEMA",
            lines=[ParsedLine(product_name="leche", quantity=1.0, price=3.50)],
        )

        matches = match_products(parsed, db)
        assert len(matches) == 0

    def test_higher_score_wins(self):
        # Product with alias match should beat product with only keyword overlap
        prod1 = _make_mock_product(id=1, name="Leche Entera", aliases=["leche entera"])
        prod2 = _make_mock_product(id=2, name="Leche Deslactosada", aliases=[])
        db = _make_mock_db(products=[prod1, prod2])

        parsed = ParseResult(
            template_name="HEMA",
            lines=[ParsedLine(product_name="leche entera", quantity=1.0, price=3.50)],
        )

        matches = match_products(parsed, db)
        assert len(matches) == 1
        assert matches[0].product_id == 1  # exact alias match wins
