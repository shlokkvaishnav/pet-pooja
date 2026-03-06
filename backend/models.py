"""
models.py — SQLAlchemy ORM Models (Supabase PostgreSQL)
=========================================================
All database tables for menu items, categories, orders,
order items, KOTs, combos, restaurant tables, and ingredients.
Multi-tenant: every major table has restaurant_id FK.
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
    ARRAY,
)
from sqlalchemy.orm import relationship

from database import Base


def _utcnow():
    return datetime.now(timezone.utc)


# ── Restaurant (Master Table) ──────────────────

class Restaurant(Base):
    """Master restaurant record — each restaurant has its own menu, staff, orders."""

    __tablename__ = "restaurants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)  # URL-friendly identifier
    email = Column(String(200), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)  # bcrypt / sha256
    phone = Column(String(20))
    address = Column(Text)
    cuisine_type = Column(String(100))  # "Indian", "Chinese", "Multi-cuisine"
    logo_url = Column(String(500))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_utcnow)

    # Relationships
    categories = relationship("Category", back_populates="restaurant")
    menu_items = relationship("MenuItem", back_populates="restaurant")
    orders = relationship("Order", back_populates="restaurant")
    settings = relationship("RestaurantSettings", back_populates="restaurant", uselist=False)


class RestaurantSettings(Base):
    """Per-restaurant user-facing settings and preferences."""

    __tablename__ = "restaurant_settings"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False, unique=True)
    menu_management = Column(JSON, default=dict)
    notifications = Column(JSON, default=dict)
    integrations = Column(JSON, default=dict)
    billing_plan = Column(JSON, default=dict)
    security = Column(JSON, default=dict)
    voice_ai_config = Column(JSON, default=dict)
    profile_extras = Column(JSON, default=dict)  # operating_hours, gst_number, etc.
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    restaurant = relationship("Restaurant", back_populates="settings")



# ── Restaurant Tables ────────────────────────────

class RestaurantTable(Base):
    """Physical table in the restaurant with real-time state."""

    __tablename__ = "restaurant_tables"

    id = Column(Integer, primary_key=True, index=True)
    table_number = Column(String(10), unique=True, nullable=False)
    capacity = Column(Integer, nullable=False, default=4)
    section = Column(String(50), default="main")  # main | patio | private | bar
    status = Column(String(20), default="empty")  # empty | occupied | reserved | cleaning
    current_order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)

    current_order = relationship("Order", foreign_keys=[current_order_id])

    __table_args__ = (
        CheckConstraint("status IN ('empty','occupied','reserved','cleaning')", name="ck_table_status"),
    )



class Category(Base):
    """Menu category (e.g., Starters, Main Course, Beverages)."""

    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=True)
    name = Column(String(100), nullable=False)
    name_hi = Column(String(100))  # Hindi name
    name_mr = Column(String(100))  # Marathi name
    name_kn = Column(String(100))  # Kannada name
    name_gu = Column(String(100))  # Gujarati name
    name_hi_en = Column(String(100))  # Hinglish name
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    restaurant = relationship("Restaurant", back_populates="categories")
    items = relationship("MenuItem", back_populates="category")


class MenuItem(Base):
    """Individual menu item with pricing, cost data, aliases and modifiers."""

    __tablename__ = "menu_items"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=True)
    name = Column(String(200), nullable=False)
    name_hi = Column(String(200))  # Hindi name
    name_mr = Column(String(200))  # Marathi name
    name_kn = Column(String(200))  # Kannada name
    name_gu = Column(String(200))  # Gujarati name
    name_hi_en = Column(String(200))  # Hinglish name
    description = Column(Text)
    aliases = Column(ARRAY(Text), default=[])  # ["pnr tikka", "panir tikka", "tikka paneer"]
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

    restaurant = relationship("Restaurant", back_populates="menu_items")
    category = relationship("Category", back_populates="items")
    ingredients = relationship("MenuItemIngredient", back_populates="menu_item")

    @property
    def contribution_margin(self) -> float:
        return self.selling_price - self.food_cost

    @property
    def margin_pct(self) -> float:
        if self.selling_price <= 0:
            return 0.0
        return (self.contribution_margin / self.selling_price) * 100


class Order(Base):
    """Completed or in-progress order."""

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    order_id = Column(String(50), unique=True, nullable=False)
    order_number = Column(String(20))  # Human-readable order number
    total_amount = Column(Float, default=0.0)
    status = Column(String(20), default="building")  # building | confirmed | cancelled
    order_type = Column(String(20), default="dine_in")
    table_number = Column(String(10))  # kept for backward compat / quick display
    table_id = Column(Integer, ForeignKey("restaurant_tables.id"), nullable=True)
    source = Column(String(20), default="voice")  # voice | manual
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    restaurant = relationship("Restaurant", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order")
    kots = relationship("KOT", back_populates="order", foreign_keys="[KOT.order_id]")
    table = relationship("RestaurantTable", foreign_keys=[table_id])


class OrderItem(Base):
    """Individual item within an order."""

    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_pk = Column(Integer, ForeignKey("orders.id"), nullable=False)
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
    order_pk = Column(Integer, ForeignKey("orders.id"), nullable=False)  # integer FK
    order_id = Column(String(50), ForeignKey("orders.order_id"), nullable=False)
    items_summary = Column(JSON, nullable=False)  # [{name, qty, modifiers}]
    print_ready = Column(Text)  # Plain-text kitchen-friendly format
    created_at = Column(DateTime, default=_utcnow)

    order = relationship("Order", back_populates="kots", foreign_keys=[order_id])


class ComboSuggestion(Base):
    """Generated combo/bundle recommendations."""

    __tablename__ = "combo_suggestions"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=True)
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
    last_active = Column(DateTime, nullable=False)  # UTC timestamp
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
        from datetime import datetime, timezone
        la = d.get("last_active")
        if la is None:
            la = datetime.now(timezone.utc)
        elif isinstance(la, (int, float)):
            la = datetime.fromtimestamp(la, tz=timezone.utc)
        return cls(
            session_id=d["session_id"],
            last_active=la,
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
    created_at = Column(DateTime, default=_utcnow)

    ingredient = relationship("Ingredient", back_populates="stock_logs")

    __table_args__ = (
        CheckConstraint("reason IN ('purchase','usage','waste','adjustment')", name="ck_stocklog_reason"),
    )


# ── v_sales (read-only view) ──────────────────────

class VSale(Base):
    """Read-only ORM model mapped to the v_sales view.
    Replaces the old SaleTransaction table — no writes, zero duplication.
    """

    __tablename__ = "v_sales"
    __table_args__ = {"info": {"is_view": True}}

    id = Column(Integer, primary_key=True)
    restaurant_id = Column(Integer)
    item_id = Column(Integer)
    order_id = Column(String(50))
    quantity = Column(Integer)
    unit_price = Column(Float)
    total_price = Column(Float)
    order_type = Column(String(20))
    sold_at = Column(DateTime)
