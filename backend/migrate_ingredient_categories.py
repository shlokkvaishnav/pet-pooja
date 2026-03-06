"""
Migration: Add 'category' column to ingredients and populate it.
Run once: python migrate_ingredient_categories.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from database import engine, SessionLocal
from sqlalchemy import text

CATEGORY_MAP = {
    # Dairy
    "Milk": "Dairy", "Cream": "Dairy", "Butter": "Dairy", "Ghee": "Dairy",
    "Paneer": "Dairy", "Yogurt (Dahi)": "Dairy", "Condensed Milk": "Dairy",
    "Cheese": "Dairy",

    # Vegetables
    "Spinach": "Vegetables", "Green Peas": "Vegetables", "Carrot": "Vegetables",
    "Potato": "Vegetables", "Cauliflower": "Vegetables", "Capsicum": "Vegetables",
    "Onion": "Vegetables", "Tomato": "Vegetables", "Green Chilli": "Vegetables",
    "Coriander Leaves": "Vegetables", "Mint Leaves": "Vegetables",
    "Broccoli": "Vegetables", "Bok Choy": "Vegetables", "Red Bell Pepper": "Vegetables",
    "Bean Sprouts": "Vegetables", "Cabbage": "Vegetables", "Spring Onion": "Vegetables",
    "Mushrooms (Shiitake)": "Vegetables",

    # Meat & Poultry
    "Chicken": "Meat & Poultry", "Chicken (boneless)": "Meat & Poultry",
    "Mutton": "Meat & Poultry", "Pork": "Meat & Poultry", "Beef": "Meat & Poultry",
    "Egg": "Meat & Poultry",

    # Seafood
    "Fish (Rohu)": "Seafood", "Tiger Prawns": "Seafood",

    # Grains & Flour
    "Basmati Rice": "Grains & Flour", "Jasmine Rice": "Grains & Flour",
    "Whole Wheat Flour": "Grains & Flour", "Maida (APF)": "Grains & Flour",
    "Suji (Semolina)": "Grains & Flour", "Besan (Gram Flour)": "Grains & Flour",
    "Glutinous Rice Flour": "Grains & Flour", "Corn Starch": "Grains & Flour",
    "Egg Noodles": "Grains & Flour", "Rice Noodles": "Grains & Flour",
    "Wonton Wrappers": "Grains & Flour", "Dumpling Wrappers": "Grains & Flour",

    # Lentils & Legumes
    "Chickpeas": "Lentils & Legumes", "Black Lentils": "Lentils & Legumes",
    "Yellow Lentils": "Lentils & Legumes",

    # Spices & Seasonings
    "Saffron": "Spices", "Cardamom": "Spices", "Cumin Seeds": "Spices",
    "Turmeric": "Spices", "Red Chilli Powder": "Spices", "Garam Masala": "Spices",
    "Szechuan Pepper": "Spices", "Garlic Paste": "Spices", "Ginger Paste": "Spices",
    "Ginger": "Spices", "Garlic": "Spices", "Sesame Seeds": "Spices",
    "Peanuts": "Dry Fruits & Nuts",

    # Dry Fruits & Nuts
    "Cashew Nuts": "Dry Fruits & Nuts", "Almonds": "Dry Fruits & Nuts",

    # Oils & Fats
    "Oil": "Oils & Fats", "Sesame Oil": "Oils & Fats",

    # Sauces & Condiments
    "Soy Sauce": "Sauces", "Oyster Sauce": "Sauces", "Hoisin Sauce": "Sauces",
    "Chilli Bean Paste": "Sauces", "Black Bean Paste": "Sauces",
    "Sweet & Sour Sauce": "Sauces", "Vinegar": "Sauces", "Honey": "Sauces",
    "Rose Water": "Sauces",

    # Fruits
    "Lemon": "Fruits", "Mango": "Fruits", "Mango Pulp": "Fruits",
    "Lychee (canned)": "Fruits",

    # Beverages
    "Tea Leaves": "Beverages", "Coffee Powder": "Beverages",
    "Jasmine Tea Leaves": "Beverages", "Soda Water": "Beverages",

    # Other / Misc
    "Sugar": "Pantry Staples", "Charcoal": "Other", "Tofu": "Other",
}


def migrate():
    with engine.connect() as conn:
        # Add column if not exists (SQLite compatible)
        try:
            conn.execute(text("ALTER TABLE ingredients ADD COLUMN category VARCHAR(50) DEFAULT 'Other'"))
            conn.commit()
            print("Added 'category' column to ingredients table.")
        except Exception:
            print("Column 'category' already exists, skipping ALTER.")

    db = SessionLocal()
    try:
        rows = db.execute(text("SELECT id, name FROM ingredients")).fetchall()
        updated = 0
        for row in rows:
            cat = CATEGORY_MAP.get(row[1], "Other")
            db.execute(
                text("UPDATE ingredients SET category = :cat WHERE id = :id"),
                {"cat": cat, "id": row[0]},
            )
            updated += 1
        db.commit()
        print(f"Updated {updated} ingredients with categories.")
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
