"""
models.py — SQLAlchemy ORM Models (Supabase PostgreSQL)
=========================================================
All database tables for menu items, categories, orders,
order items, KOTs, sales transactions, combos, staff,
restaurant tables, shifts, and ingredients.
"""

from datetime import datetime, timezone

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
    CheckConstraint,
)
from sqlalchemy.orm import relationship

from database import Base


def _utcnow():
    return datetime.now(timezone.utc)


# ── Staff ────────────────────────────────────────

class Staff(Base):
    """Restaurant employee — waiter, cashier, manager, or chef."""

    __tablename__ = "staff"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    role = Column(String(30), nullable=False, default="waiter")  # waiter | cashier | manager | chef
    pin_hash = Column(String(128), nullable=False)  # hashed 4-6 digit PIN for POS login
    phone = Column(String(20))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_utcnow)

    orders = relationship("Order", back_populates="staff", foreign_keys="Order.staff_id")
    shifts_opened = relationship("Shift", back_populates="opened_by_staff", foreign_keys="Shift.opened_by")
    shifts_closed = relationship("Shift", back_populates="closed_by_staff", foreign_keys="Shift.closed_by")
    stock_logs = relationship("StockLog", back_populates="staff")

    __table_args__ = (
        CheckConstraint("role IN ('waiter','cashier','manager','chef')", name="ck_staff_role"),
    )


# ── Restaurant Tables ────────────────────────────

class RestaurantTable(Base):
    """Physical table in the restaurant with real-time state."""

    __tablename__ = "restaurant_tables"

    id = Column(Integer, primary_key=True, index=True)
    table_number = Column(String(10), unique=True, nullable=False)
    capacity = Column(Integer, nullable=False, default=4)
    section = Column(String(50), default="main")  # main | patio | private | bar
    status = Column(String(20), default="empty")  # empty | occupied | reserved | cleaning
    current_order_id = Column(String(50), ForeignKey("orders.order_id"), nullable=True)

    current_order = relationship("Order", foreign_keys=[current_order_id])

    __table_args__ = (
        CheckConstraint("status IN ('empty','occupied','reserved','cleaning')", name="ck_table_status"),
    )


# ── Shifts ───────────────────────────────────────

class Shift(Base):
    """Operational shift / cash session. Revenue and orders are grouped by shift."""

    __tablename__ = "shifts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50))  # "Lunch", "Dinner", or auto-generated
    started_at = Column(DateTime, nullable=False, default=_utcnow)
    ended_at = Column(DateTime, nullable=True)
    opened_by = Column(Integer, ForeignKey("staff.id"), nullable=False)
    closed_by = Column(Integer, ForeignKey("staff.id"), nullable=True)
    opening_cash = Column(Float, default=0.0)
    closing_cash = Column(Float, nullable=True)
    status = Column(String(10), default="open")  # open | closed

    opened_by_staff = relationship("Staff", back_populates="shifts_opened", foreign_keys=[opened_by])
    closed_by_staff = relationship("Staff", back_populates="shifts_closed", foreign_keys=[closed_by])
    orders = relationship("Order", back_populates="shift")
    sale_transactions = relationship("SaleTransaction", back_populates="shift")

    __table_args__ = (
        CheckConstraint("status IN ('open','closed')", name="ck_shift_status"),
    )


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
    """Individual menu item with pricing, cost data, aliases and modifiers."""

    __tablename__ = "menu_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    name_hi = Column(String(200))  # Hindi name
    description = Column(Text)
    aliases = Column(Text, default="")  # pipe-separated: "pnr tikka|panir tikka|tikka paneer"
    category_id = Column(Integer, ForeignKey("categories.id"))
    selling_price = Column(Float, nullable=False)
    food_cost = Column(Float, nullable=False)
    modifiers = Column(JSON, default=dict)  # {"spice_level": [...], "size": [...], "add_ons": [...]}
    is_veg = Column(Boolean, default=True)
    is_available = Column(Boolean, default=True)
    is_bestseller = Column(Boolean, default=False)
    current_stock = Column(Integer, nullable=True)  # None = unlimited
    tags = Column(JSON, default=list)  # ["spicy", "chef-special", etc.]
    created_at = Column(DateTime, default=_utcnow)

    category = relationship("Category", back_populates="items")
    sales = relationship("SaleTransaction", back_populates="item")
    ingredients = relationship("MenuItemIngredient", back_populates="menu_item")

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
    shift_id = Column(Integer, ForeignKey("shifts.id"), nullable=True)
    sold_at = Column(DateTime, default=_utcnow)

    item = relationship("MenuItem", back_populates="sales")
    shift = relationship("Shift", back_populates="sale_transactions")


class Order(Base):
    """Completed or in-progress order."""

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String(50), unique=True, nullable=False)
    order_number = Column(String(20))  # Human-readable order number
    total_amount = Column(Float, default=0.0)
    status = Column(String(20), default="building")  # building | confirmed | cancelled
    order_type = Column(String(20), default="dine_in")
    table_number = Column(String(10))  # kept for backward compat / quick display
    table_id = Column(Integer, ForeignKey("restaurant_tables.id"), nullable=True)
    staff_id = Column(Integer, ForeignKey("staff.id"), nullable=True)
    shift_id = Column(Integer, ForeignKey("shifts.id"), nullable=True)
    source = Column(String(20), default="voice")  # voice | manual
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    order_items = relationship("OrderItem", back_populates="order")
    kots = relationship("KOT", back_populates="order")
    staff = relationship("Staff", back_populates="orders", foreign_keys=[staff_id])
    table = relationship("RestaurantTable", foreign_keys=[table_id])
    shift = relationship("Shift", back_populates="orders")


class OrderItem(Base):
    """Individual item within an order."""

    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String(50), ForeignKey("orders.order_id"), nullable=False)
    item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, nullable=False)
    modifiers_applied = Column(JSON, default=dict)  # {"spice_level": "hot", ...}
    line_total = Column(Float, nullable=False)

    order = relationship("Order", back_populates="order_items")
    menu_item = relationship("MenuItem")


class KOT(Base):
    """Kitchen Order Ticket — sent to kitchen after order confirmation."""

    __tablename__ = "kots"

    id = Column(Integer, primary_key=True, index=True)
    kot_id = Column(String(50), unique=True, nullable=False)  # KOT-YYYYMMDD-XXXX
    order_id = Column(String(50), ForeignKey("orders.order_id"), nullable=False)
    items_summary = Column(JSON, nullable=False)  # [{name, qty, modifiers}]
    print_ready = Column(Text)  # Plain-text kitchen-friendly format
    created_at = Column(DateTime, default=_utcnow)

    order = relationship("Order", back_populates="kots")


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
    lift = Column(Float)  # Association rule lift
    combo_score = Column(Float)  # lift × avg_cm × confidence
    created_at = Column(DateTime, default=_utcnow)


# ── Ingredients & Stock ──────────────────────────

class Ingredient(Base):
    """Raw ingredient tracked in inventory (e.g., chicken, paneer, oil)."""

    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), unique=True, nullable=False)
    unit = Column(String(20), nullable=False, default="g")  # g | kg | ml | L | pcs
    current_stock = Column(Float, nullable=False, default=0.0)
    reorder_level = Column(Float, nullable=False, default=0.0)  # alert when stock <= this
    cost_per_unit = Column(Float, nullable=False, default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_utcnow)

    menu_item_ingredients = relationship("MenuItemIngredient", back_populates="ingredient")
    stock_logs = relationship("StockLog", back_populates="ingredient")

    @property
    def is_low_stock(self) -> bool:
        return self.current_stock <= self.reorder_level


class MenuItemIngredient(Base):
    """How much of an ingredient a single serving of a menu item consumes."""

    __tablename__ = "menu_item_ingredients"

    id = Column(Integer, primary_key=True, index=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False)
    quantity_used = Column(Float, nullable=False)  # in ingredient's unit per 1 serving

    menu_item = relationship("MenuItem", back_populates="ingredients")
    ingredient = relationship("Ingredient", back_populates="menu_item_ingredients")


class VoiceSession(Base):
    """Persistent voice-ordering session — survives server restarts."""

    __tablename__ = "voice_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    last_active = Column(Float, nullable=False)  # Unix timestamp
    order_items = Column(JSON, default=list)
    last_items = Column(JSON, default=list)
    turn_count = Column(Integer, default=0)
    confirmed = Column(Boolean, default=False)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "last_active": self.last_active,
            "order_items": self.order_items or [],
            "last_items": self.last_items or [],
            "turn_count": self.turn_count,
            "confirmed": self.confirmed,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "VoiceSession":
        return cls(
            session_id=d["session_id"],
            last_active=d.get("last_active", 0.0),
            order_items=d.get("order_items", []),
            last_items=d.get("last_items", []),
            turn_count=d.get("turn_count", 0),
            confirmed=d.get("confirmed", False),
        )


class StockLog(Base):
    """Audit trail for every inventory change — purchase, usage, waste, adjustment."""

    __tablename__ = "stock_logs"

    id = Column(Integer, primary_key=True, index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False)
    change_qty = Column(Float, nullable=False)  # positive = add, negative = deduct
    reason = Column(String(30), nullable=False)  # purchase | usage | waste | adjustment
    note = Column(Text, nullable=True)
    staff_id = Column(Integer, ForeignKey("staff.id"), nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    ingredient = relationship("Ingredient", back_populates="stock_logs")
    staff = relationship("Staff", back_populates="stock_logs")

    __table_args__ = (
        CheckConstraint("reason IN ('purchase','usage','waste','adjustment')", name="ck_stocklog_reason"),
    )
