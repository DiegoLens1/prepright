"""
Receipt parser with configurable templates.

Each template defines:
- A regex pattern to match product lines
- Group names for extracting product name, quantity, price
- Optional name normalization rules
- A source keyword for auto-detection

Usage:
    parser = ReceiptParser(db_session)
    result = parser.parse_receipt(raw_text, template_name="HEMA")
    print(result.products)  # List[ProductMatch]
"""

import re
import json
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.orm import Session

from prepright import models, schemas


# Lines whose first token is one of these are receipt metadata (store info,
# totals, payment, footer)
_STOP_KEYWORDS = {
    "TOTAAL", "TOTAL", "SUBTOTAAL", "SUBTOTAL", "BTW", "VAT", "KVK", "IBAN",
    "TEL", "PIN", "CONTANT", "CASH", "WISSELGELD", "CHANGE", "KASSA", "BON",
    "DATUM", "DATE", "BEDANKT", "THANK", "TIP",
}


def _is_stop_line(line: str) -> bool:
    """True if the line's first token marks it as receipt metadata, not a product."""
    tokens = line.upper().replace(":", " ").split()
    return bool(tokens) and tokens[0] in _STOP_KEYWORDS


def _plausible_price_count(result: "ParseResult") -> int:
    """Count parsed lines with a positive price — a soft signal of a good parse.

    Used to break ties when auto-selecting among generic templates: a template
    that yields real-looking prices (e.g. 4.50) is preferred over one that
    mis-splits them (e.g. price 0.0 from a qty-less line)."""
    return sum(1 for line in result.lines if line.price and line.price > 0)


@dataclass
class ParsedLine:
    """A single product line parsed from a receipt."""
    product_name: str
    quantity: float
    price: Optional[float] = None


@dataclass
class ParseResult:
    """Result of parsing a receipt."""
    template_name: str
    lines: list[ParsedLine] = field(default_factory=list)
    unmatched: list[str] = field(default_factory=list)
    raw_line_count: int = 0
    parsed_line_count: int = 0


class ReceiptTemplate:
    """Represents a parsed template from the database."""
    name: str
    source_keyword: Optional[str]
    line_pattern: str
    product_name_group: str
    quantity_group: str
    price_group: str
    line_prefix: Optional[str]
    line_suffix: Optional[str]
    name_normalize: Optional[str]

    @classmethod
    def from_db(cls, template: models.ReceiptTemplate) -> "ReceiptTemplate":
        t = cls()
        t.name = template.name
        t.source_keyword = template.source_keyword
        t.line_pattern = template.line_pattern
        t.product_name_group = template.product_name_group
        t.quantity_group = template.quantity_group
        t.price_group = template.price_group
        t.line_prefix = template.line_prefix
        t.line_suffix = template.line_suffix
        t.name_normalize = template.name_normalize
        return t

    def compile_pattern(self) -> re.Pattern:
        return re.compile(self.line_pattern)

    def normalize_name(self, name: str) -> str:
        """Apply normalization rules to a product name."""
        if not self.name_normalize:
            return name
        rules = self.name_normalize.split(",")
        for rule in rules:
            rule = rule.strip()
            if not rule:
                continue
            parts = rule.split(":")
            if len(parts) == 2:
                old, new = parts
                name = name.replace(old.strip(), new.strip())
        return name


class ReceiptParser:
    """Main parser that applies templates to raw receipt text."""

    def __init__(self, db: Session):
        self.db = db

    def detect_template(self, text: str) -> Optional[ReceiptTemplate]:
        """Auto-detect which template to use based on source_keyword in text."""
        templates = self.db.query(models.ReceiptTemplate).filter(
            models.ReceiptTemplate.active == True
        ).all()

        text_lower = text.lower()
        best_match = None
        best_keyword_len = 0

        for t in templates:
            if t.source_keyword and t.source_keyword.lower() in text_lower:
                if len(t.source_keyword) > best_keyword_len:
                    best_keyword_len = len(t.source_keyword)
                    best_match = t

        return ReceiptTemplate.from_db(best_match) if best_match else None

    def parse_receipt(self, text: str, template_name: Optional[str] = None) -> ParseResult:
        """Parse a receipt using the specified or auto-detected template.

        Selection order:
        1. Explicit ``template_name`` if given (returns a "none" result if it is
           not found, preserving the original contract).
        2. Auto-detection via ``source_keyword``.
        3. Best-effort: try every active template and keep the one that parses
           the most lines — needed because the bundled generic templates carry
           no ``source_keyword`` and so can never be auto-detected by keyword.
        """
        if template_name:
            db_template = self.db.query(models.ReceiptTemplate).filter(
                models.ReceiptTemplate.name == template_name,
                models.ReceiptTemplate.active == True
            ).first()
            if not db_template:
                return self._none_result(text)
            return self._parse_with_template(text, ReceiptTemplate.from_db(db_template))

        detected = self.detect_template(text)
        if detected:
            return self._parse_with_template(text, detected)

        return self._best_effort_parse(text)

    @staticmethod
    def _none_result(text: str) -> ParseResult:
        """Result returned when no usable template could be applied."""
        return ParseResult(
            template_name="none",
            unmatched=[text[:200]],
            raw_line_count=1,
            parsed_line_count=0,
        )

    def _best_effort_parse(self, text: str) -> ParseResult:
        """Parse with every active template and return the best-scoring result.

        Score is ``(parsed_line_count, plausible_price_count, -unmatched)`` so
        the template that parses the most lines wins, with realistic prices and
        fewer leftovers as tie-breakers. Falls back to a "none" result if no
        template parses anything."""
        templates = self.db.query(models.ReceiptTemplate).filter(
            models.ReceiptTemplate.active == True
        ).all()

        best: Optional[ParseResult] = None
        best_score = None
        for db_t in templates:
            result = self._parse_with_template(text, ReceiptTemplate.from_db(db_t))
            score = (
                result.parsed_line_count,
                _plausible_price_count(result),
                -len(result.unmatched),
            )
            if best_score is None or score > best_score:
                best, best_score = result, score

        if best is None or best.parsed_line_count == 0:
            return self._none_result(text)
        return best

    def _parse_with_template(self, text: str, template: ReceiptTemplate) -> ParseResult:
        """Apply a single template to the receipt text."""
        result = ParseResult(template_name=template.name)
        compiled = template.compile_pattern()

        lines = text.split("\n")
        result.raw_line_count = len(lines)

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Skip receipt metadata (store header, totals, payment, footer).
            if _is_stop_line(line):
                continue

            # Apply prefix/suffix stripping
            if template.line_prefix and line.startswith(template.line_prefix):
                line = line[len(template.line_prefix):]
            if template.line_suffix and line.endswith(template.line_suffix):
                line = line[:-len(template.line_suffix)]

            match = compiled.match(line)
            if match:
                try:
                    product_name = match.group(template.product_name_group).strip()

                    # Only read a group if the regex actually defines it. The
                    # quantity_group column defaults to "qty", so a "name + price"
                    # template (no qty group) would otherwise raise IndexError on
                    # every line. A missing quantity group means quantity = 1.
                    groups = compiled.groupindex
                    quantity = 1.0
                    if template.quantity_group and template.quantity_group in groups:
                        quantity_str = match.group(template.quantity_group)
                        quantity = float(quantity_str) if quantity_str else 1.0

                    price = None
                    if template.price_group and template.price_group in groups:
                        price_str = match.group(template.price_group)
                        if price_str:
                            price = float(price_str.replace(",", "."))

                    product_name = template.normalize_name(product_name)

                    result.lines.append(ParsedLine(
                        product_name=product_name,
                        quantity=quantity,
                        price=price,
                    ))
                    result.parsed_line_count += 1
                except (AttributeError, ValueError, IndexError):
                    result.unmatched.append(line)
            else:
                result.unmatched.append(line)

        return result


def match_products(parsed: ParseResult, db: Session) -> list[schemas.ProductMatch]:
    """Match parsed product names to database products via aliases/keywords."""
    matches = []
    products = db.query(models.Product).filter(
        models.Product.active == True
    ).all()

    for line in parsed.lines:
        best_match = None
        best_score = 0
        confidence = "low"

        name_lower = line.product_name.lower().strip()

        for product in products:
            # 1. Check aliases (exact match, case-insensitive)
            for alias in product.aliases:
                if alias.alias_name.lower().strip() == name_lower:
                    score = 100
                    if score > best_score:
                        best_score = score
                        best_match = product
                        confidence = "high"

            # 2. Check if product name is contained in receipt name
            if product.name.lower() in name_lower or name_lower in product.name.lower():
                score = 90
                if score > best_score:
                    best_score = score
                    best_match = product
                    confidence = "high"

            # 3. Check if any alias is contained in receipt name
            for alias in product.aliases:
                alias_lower = alias.alias_name.lower().strip()
                if alias_lower in name_lower or name_lower in alias_lower:
                    score = 70
                    if score > best_score:
                        best_score = score
                        best_match = product
                        confidence = "medium"

            # 4. Keyword matching (check product name words)
            product_words = set(product.name.lower().split())
            receipt_words = set(name_lower.split())
            if product_words and receipt_words:
                overlap = len(product_words & receipt_words) / max(len(product_words), len(receipt_words))
                if overlap > 0.6:
                    score = int(overlap * 60)
                    if score > best_score:
                        best_score = score
                        best_match = product
                        confidence = "medium"

        if best_match:
            matches.append(schemas.ProductMatch(
                product_id=best_match.id,
                product_name=line.product_name,
                matched_name=best_match.name,
                quantity=line.quantity,
                price=line.price,
                confidence=confidence,
            ))
        else:
            # No match found — add to unmatched
            pass

    return matches
