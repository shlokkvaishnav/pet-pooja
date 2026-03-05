"""
models.py — SQLAlchemy ORM Models
==================================
All database tables for menu items, categories, orders,
sales transactions, and combos.
"""

from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import relationship

from database import Base


class Category(Base):
    """Menu category (e.g., Starters, Main Course, Beverages)."""

    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    name_hi = Column(String(100))  # Hindi name
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    items = relationship("MenuItem", back_populates="category")


class MenuItem(Base):
    """Individual menu item with pricing and cost data."""

    __tablename__ = "menu_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    name_hi = Column(String(200))  # Hindi name
    description = Column(Text)
    category_id = Column(Integer, ForeignKey("categories.id"))
    selling_price = Column(Float, nullable=False)
    food_cost = Column(Float, nullable=False)
    is_veg = Column(Boolean, default=True)
    is_available = Column(Boolean, default=True)
    is_bestseller = Column(Boolean, default=False)
    aliases = Column(String(500))  # pipe-separated fuzzy match aliases e.g. "pnr tikka|panir tikka"
    modifiers = Column(Text)  # JSON string of allowed modifiers e.g. '{"spice":["mild","medium","hot"]}'
    tags = Column(JSON, default=list)  # ["spicy", "chef-special", etc.]
    created_at = Column(DateTime, default=datetime.utcnow)

    category = relationship("Category", back_populates="items")
    sales = relationship("SaleTransaction", back_populates="item")

    @property
    def contribution_margin(self) -> float:
        return self.selling_price - self.food_cost

    @property
    def margin_pct(self) -> float:
        if self.selling_price <= 0:
            return 0.0
        return (self.contribution_margin / self.selling_price) * 100


class SaleTransaction(Base):
    """Individual sale record — one row per item per order."""

    __tablename__ = "sale_transactions"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)
    order_id = Column(String(50), nullable=False)
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    order_type = Column(String(20), default="dine_in")  # dine_in | takeaway | delivery
    sold_at = Column(DateTime, default=datetime.utcnow)

    item = relationship("MenuItem", back_populates="sales")


class Order(Base):
    """Completed or in-progress order."""

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String(50), unique=True, nullable=False)
    items = Column(JSON, default=list)  # [{item_id, name, qty, price, modifiers}]
    total = Column(Float, default=0.0)
    status = Column(String(20), default="building")  # building | confirmed | cancelled
    order_type = Column(String(20), default="dine_in")
    table_number = Column(String(10))
    source = Column(String(20), default="voice")  # voice | manual
    created_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime)


class ComboSuggestion(Base):
    """Generated combo/bundle recommendations."""

    __tablename__ = "combo_suggestions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    item_ids = Column(JSON, nullable=False)  # [1, 5, 12]
    item_names = Column(JSON, nullable=False)  # ["Paneer Tikka", "Naan", ...]
    individual_total = Column(Float)
    combo_price = Column(Float)
    discount_pct = Column(Float)
    expected_margin = Column(Float)
    support = Column(Float)  # Association rule support
    confidence = Column(Float)  # Association rule confidence
    created_at = Column(DateTime, default=datetime.utcnow)
