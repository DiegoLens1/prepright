from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from prepright.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    margin_pct = Column(Float, default=0.0)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    category = relationship("Category")
    aliases = relationship("ProductAlias", back_populates="product", cascade="all, delete-orphan")
    recipes = relationship("Recipe", back_populates="product", cascade="all, delete-orphan")


class ProductAlias(Base):
    __tablename__ = "product_aliases"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    alias_name = Column(String, index=True, nullable=False)

    product = relationship("Product", back_populates="aliases")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    active = Column(Boolean, default=True)
    weather_sensitivity = Column(Float, default=1.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    unit = Column(String, default="units")
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False)
    quantity_per_unit = Column(Float, default=0.0)

    product = relationship("Product", back_populates="recipes")
    ingredient = relationship("Ingredient")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    impact_factor = Column(Float, default=0.0)


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True, index=True)
    value = Column(Text, nullable=True)


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    predicted_qty = Column(Float, default=0.0)
    base_qty = Column(Float, default=0.0)
    weather_adjustment = Column(Float, default=0.0)
    event_adjustment = Column(Float, default=0.0)
    discount_adjustment = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    product = relationship("Product")


class ReceiptTemplate(Base):
    """Configurable template for parsing receipts from different POS systems."""
    __tablename__ = "receipt_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    source_keyword = Column(String, nullable=True)
    line_pattern = Column(Text, nullable=False)
    product_name_group = Column(String, default="name")
    # No default: a quantity column is optional (e.g. "name + price" receipts).
    # A "qty" default would be applied when the seed passes None, leaving the
    # template pointing at a regex group that doesn't exist.
    quantity_group = Column(String, nullable=True)
    price_group = Column(String, default="price")
    line_prefix = Column(Text, nullable=True)
    line_suffix = Column(Text, nullable=True)
    name_normalize = Column(Text, nullable=True)
    config = Column(Text, nullable=True)


class SalesRecord(Base):
    """Records when a product is sold (from receipt processing)."""
    __tablename__ = "sales_records"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Float, default=0.0)
    sale_date = Column(String, nullable=False)
    source_template = Column(String, nullable=True)
    confidence = Column(String, default="medium")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    product = relationship("Product")
