"""
migrate_languages.py — Add Marathi, Kannada, Gujarati, Hinglish columns and populate translations
"""
import sys
sys.path.insert(0, ".")

from sqlalchemy import text
from database import engine, SessionLocal
from models import MenuItem, Category

# ── Step 1: Add columns if they don't exist ──
NEW_COLS = {
    "categories": ["name_mr", "name_kn", "name_gu", "name_hi_en"],
    "menu_items": ["name_mr", "name_kn", "name_gu", "name_hi_en"],
}

with engine.connect() as conn:
    for table, cols in NEW_COLS.items():
        for col in cols:
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} VARCHAR(200)"))
                conn.commit()
                print(f"  ✅ Added {table}.{col}")
            except Exception as e:
                conn.rollback()
                if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                    print(f"  ⏭️  {table}.{col} already exists")
                else:
                    print(f"  ⚠️  {table}.{col}: {e}")

print("\n── Columns ready ──\n")

# ── Step 2: Category translations ──
CATEGORY_TRANSLATIONS = {
    "Starters": {
        "mr": "स्टार्टर्स",
        "kn": "ಸ್ಟಾರ್ಟರ್ಸ್",
        "gu": "સ્ટાર્ટર્સ",
        "hi_en": "Starters",
    },
    "Main Course Veg": {
        "mr": "मुख्य जेवण (शाकाहारी)",
        "kn": "ಮುಖ್ಯ ಊಟ (ಶಾಖಾಹಾರಿ)",
        "gu": "મુખ્ય ભોજન (શાકાહારી)",
        "hi_en": "Main Course Veg",
    },
    "Main Course Non-Veg": {
        "mr": "मुख्य जेवण (मांसाहारी)",
        "kn": "ಮುಖ್ಯ ಊಟ (ಮಾಂಸಾಹಾರಿ)",
        "gu": "મુખ્ય ભોજન (માંસાહારી)",
        "hi_en": "Main Course Non-Veg",
    },
    "Breads": {
        "mr": "ब्रेड्स / रोटी",
        "kn": "ಬ್ರೆಡ್ಸ್ / ರೊಟ್ಟಿ",
        "gu": "બ્રેડ્સ / રોટી",
        "hi_en": "Rotis & Naan",
    },
    "Rice & Biryani": {
        "mr": "भात आणि बिरयानी",
        "kn": "ಅನ್ನ ಮತ್ತು ಬಿರಿಯಾನಿ",
        "gu": "ભાત અને બિરયાની",
        "hi_en": "Rice & Biryani",
    },
    "Beverages": {
        "mr": "पेये",
        "kn": "ಪಾನೀಯಗಳು",
        "gu": "પીણાં",
        "hi_en": "Beverages & Drinks",
    },
}

# ── Step 3: Menu Item translations ──
ITEM_TRANSLATIONS = {
    # === STARTERS (1-10) ===
    "Paneer Tikka": {
        "mr": "पनीर टिक्का", "kn": "ಪನೀರ್ ಟಿಕ್ಕಾ", "gu": "પનીર ટિક્કા", "hi_en": "Paneer Tikka",
    },
    "Chicken Tikka": {
        "mr": "चिकन टिक्का", "kn": "ಚಿಕನ್ ಟಿಕ್ಕಾ", "gu": "ચિકન ટિક્કા", "hi_en": "Chicken Tikka",
    },
    "Veg Spring Roll": {
        "mr": "व्हेज स्प्रिंग रोल", "kn": "ವೆಜ್ ಸ್ಪ್ರಿಂಗ್ ರೋಲ್", "gu": "વેજ સ્પ્રિંગ રોલ", "hi_en": "Veg Spring Roll",
    },
    "Hara Bhara Kebab": {
        "mr": "हरा भरा कबाब", "kn": "ಹರಾ ಭರಾ ಕಬಾಬ್", "gu": "હરા ભરા કબાબ", "hi_en": "Hara Bhara Kebab",
    },
    "Fish Amritsari": {
        "mr": "फिश अमृतसरी", "kn": "ಫಿಶ್ ಅಮೃತ್ಸರಿ", "gu": "ફિશ અમૃતસરી", "hi_en": "Fish Amritsari",
    },
    "Mushroom Galouti": {
        "mr": "मशरूम गलौटी", "kn": "ಮಶ್ರೂಮ್ ಗಲೌಟಿ", "gu": "મશરૂમ ગલૌટી", "hi_en": "Mushroom Galouti",
    },
    "Tandoori Chicken": {
        "mr": "तंदूरी चिकन", "kn": "ತಂದೂರಿ ಚಿಕನ್", "gu": "તંદૂરી ચિકન", "hi_en": "Tandoori Chicken",
    },
    "Dahi Kebab": {
        "mr": "दही कबाब", "kn": "ಮೊಸರು ಕಬಾಬ್", "gu": "દહીં કબાબ", "hi_en": "Dahi Kebab",
    },
    "Malai Chaap": {
        "mr": "मलाई चाप", "kn": "ಮಲಾಯಿ ಚಾಪ್", "gu": "મલાઈ ચાપ", "hi_en": "Malai Chaap",
    },
    "Seekh Kebab": {
        "mr": "सीख कबाब", "kn": "ಸೀಖ್ ಕಬಾಬ್", "gu": "સીખ કબાબ", "hi_en": "Seekh Kebab",
    },
    # === MAIN COURSE VEG (11-20) ===
    "Dal Makhani": {
        "mr": "दाल मखनी", "kn": "ದಾಲ್ ಮಖನಿ", "gu": "દાળ મખની", "hi_en": "Dal Makhani",
    },
    "Paneer Butter Masala": {
        "mr": "पनीर बटर मसाला", "kn": "ಪನೀರ್ ಬಟರ್ ಮಸಾಲಾ", "gu": "પનીર બટર મસાલા", "hi_en": "Paneer Butter Masala",
    },
    "Palak Paneer": {
        "mr": "पालक पनीर", "kn": "ಪಾಲಕ್ ಪನೀರ್", "gu": "પાલક પનીર", "hi_en": "Palak Paneer",
    },
    "Chole Bhature": {
        "mr": "छोले भटूरे", "kn": "ಛೋಲೆ ಭಟೂರೆ", "gu": "છોલે ભટૂરે", "hi_en": "Chole Bhature",
    },
    "Shahi Paneer": {
        "mr": "शाही पनीर", "kn": "ಶಾಹಿ ಪನೀರ್", "gu": "શાહી પનીર", "hi_en": "Shahi Paneer",
    },
    "Mix Veg": {
        "mr": "मिक्स भाजी", "kn": "ಮಿಕ್ಸ್ ವೆಜ್", "gu": "મિક્સ વેજ", "hi_en": "Mix Veg",
    },
    "Dal Tadka": {
        "mr": "दाल तडका", "kn": "ದಾಲ್ ತಡ್ಕಾ", "gu": "દાળ તડકા", "hi_en": "Dal Tadka",
    },
    "Malai Kofta": {
        "mr": "मलाई कोफ्ता", "kn": "ಮಲಾಯಿ ಕೋಫ್ತಾ", "gu": "મલાઈ કોફ્તા", "hi_en": "Malai Kofta",
    },
    "Aloo Gobi": {
        "mr": "आलू गोबी", "kn": "ಆಲೂ ಗೋಬಿ", "gu": "બટાકા ગોબી", "hi_en": "Aloo Gobi",
    },
    "Kadhai Paneer": {
        "mr": "कडाही पनीर", "kn": "ಕಡಾಯಿ ಪನೀರ್", "gu": "કઢાઈ પનીર", "hi_en": "Kadhai Paneer",
    },
    # === MAIN COURSE NON-VEG (21-30) ===
    "Butter Chicken": {
        "mr": "बटर चिकन", "kn": "ಬಟರ್ ಚಿಕನ್", "gu": "બટર ચિકન", "hi_en": "Butter Chicken",
    },
    "Kadhai Chicken": {
        "mr": "कडाही चिकन", "kn": "ಕಡಾಯಿ ಚಿಕನ್", "gu": "કઢાઈ ચિકન", "hi_en": "Kadhai Chicken",
    },
    "Mutton Rogan Josh": {
        "mr": "मटण रोगन जोश", "kn": "ಮಟನ್ ರೋಗನ್ ಜೋಶ್", "gu": "મટન રોગન જોશ", "hi_en": "Mutton Rogan Josh",
    },
    "Egg Curry": {
        "mr": "अंडा करी", "kn": "ಮೊಟ್ಟೆ ಕರಿ", "gu": "ઈંડા કરી", "hi_en": "Egg Curry",
    },
    "Chicken Biryani Boneless": {
        "mr": "चिकन बिरयानी बोनलेस", "kn": "ಚಿಕನ್ ಬಿರಿಯಾನಿ ಬೋನ್‌ಲೆಸ್", "gu": "ચિકન બિરયાની બોનલેસ", "hi_en": "Chicken Biryani Boneless",
    },
    "Chicken Curry": {
        "mr": "चिकन करी", "kn": "ಚಿಕನ್ ಕರಿ", "gu": "ચિકન કરી", "hi_en": "Chicken Curry",
    },
    "Keema Matar": {
        "mr": "कीमा मटर", "kn": "ಕೀಮಾ ಮಟರ್", "gu": "કીમા મટર", "hi_en": "Keema Matar",
    },
    "Fish Curry": {
        "mr": "फिश करी", "kn": "ಮೀನು ಕರಿ", "gu": "ફિશ કરી", "hi_en": "Fish Curry",
    },
    "Prawn Masala": {
        "mr": "प्रॉन मसाला", "kn": "ಸಿಗಡಿ ಮಸಾಲಾ", "gu": "ઝીંગા મસાલા", "hi_en": "Prawn Masala",
    },
    "Mutton Keema": {
        "mr": "मटण कीमा", "kn": "ಮಟನ್ ಕೀಮಾ", "gu": "મટન કીમા", "hi_en": "Mutton Keema",
    },
    # === BREADS (31-38) ===
    "Butter Naan": {
        "mr": "बटर नान", "kn": "ಬಟರ್ ನಾನ್", "gu": "બટર નાન", "hi_en": "Butter Naan",
    },
    "Garlic Naan": {
        "mr": "गार्लिक नान", "kn": "ಬೆಳ್ಳುಳ್ಳಿ ನಾನ್", "gu": "ગાર્લિક નાન", "hi_en": "Garlic Naan",
    },
    "Tandoori Roti": {
        "mr": "तंदूरी रोटी", "kn": "ತಂದೂರಿ ರೊಟ್ಟಿ", "gu": "તંદૂરી રોટી", "hi_en": "Tandoori Roti",
    },
    "Lachha Paratha": {
        "mr": "लच्छा पराठा", "kn": "ಲಚ್ಛಾ ಪರಾಠಾ", "gu": "લચ્છા પરાઠા", "hi_en": "Lachha Paratha",
    },
    "Cheese Naan": {
        "mr": "चीज नान", "kn": "ಚೀಸ್ ನಾನ್", "gu": "ચીઝ નાન", "hi_en": "Cheese Naan",
    },
    "Missi Roti": {
        "mr": "मिस्सी रोटी", "kn": "ಮಿಸ್ಸಿ ರೊಟ್ಟಿ", "gu": "મિસ્સી રોટી", "hi_en": "Missi Roti",
    },
    "Kulcha": {
        "mr": "कुलचा", "kn": "ಕುಲ್ಚಾ", "gu": "કુલચા", "hi_en": "Kulcha",
    },
    "Roomali Roti": {
        "mr": "रूमाली रोटी", "kn": "ರೂಮಾಲಿ ರೊಟ್ಟಿ", "gu": "રૂમાલી રોટી", "hi_en": "Roomali Roti",
    },
    # === RICE & BIRYANI (39-45) ===
    "Jeera Rice": {
        "mr": "जिरा राईस", "kn": "ಜೀರಾ ರೈಸ್", "gu": "જીરા રાઈસ", "hi_en": "Jeera Rice",
    },
    "Veg Biryani": {
        "mr": "व्हेज बिरयानी", "kn": "ವೆಜ್ ಬಿರಿಯಾನಿ", "gu": "વેજ બિરયાની", "hi_en": "Veg Biryani",
    },
    "Chicken Biryani": {
        "mr": "चिकन बिरयानी", "kn": "ಚಿಕನ್ ಬಿರಿಯಾನಿ", "gu": "ચિકન બિરયાની", "hi_en": "Chicken Biryani",
    },
    "Mutton Biryani": {
        "mr": "मटण बिरयानी", "kn": "ಮಟನ್ ಬಿರಿಯಾನಿ", "gu": "મટન બિરયાની", "hi_en": "Mutton Biryani",
    },
    "Steamed Rice": {
        "mr": "स्टीम्ड राईस", "kn": "ಬೇಯಿಸಿದ ಅನ್ನ", "gu": "સ્ટીમ્ડ રાઈસ", "hi_en": "Steamed Rice",
    },
    "Egg Biryani": {
        "mr": "अंडा बिरयानी", "kn": "ಮೊಟ್ಟೆ ಬಿರಿಯಾನಿ", "gu": "ઈંડા બિરયાની", "hi_en": "Egg Biryani",
    },
    "Veg Pulao": {
        "mr": "व्हेज पुलाव", "kn": "ವೆಜ್ ಪುಲಾವ್", "gu": "વેજ પુલાવ", "hi_en": "Veg Pulao",
    },
    # === BEVERAGES (46-60) ===
    "Masala Chai": {
        "mr": "मसाला चहा", "kn": "ಮಸಾಲ ಚಹಾ", "gu": "મસાલા ચા", "hi_en": "Masala Chai",
    },
    "Cold Coffee": {
        "mr": "कोल्ड कॉफी", "kn": "ಕೋಲ್ಡ್ ಕಾಫಿ", "gu": "કોલ્ડ કોફી", "hi_en": "Cold Coffee",
    },
    "Sweet Lassi": {
        "mr": "गोड लस्सी", "kn": "ಸಿಹಿ ಲಸ್ಸಿ", "gu": "મીઠી લસ્સી", "hi_en": "Sweet Lassi",
    },
    "Mango Shake": {
        "mr": "मँगो शेक", "kn": "ಮ್ಯಾಂಗೋ ಶೇಕ್", "gu": "મેંગો શેક", "hi_en": "Mango Shake",
    },
    "Fresh Lime Soda": {
        "mr": "फ्रेश लाईम सोडा", "kn": "ಫ್ರೆಶ್ ಲೈಮ್ ಸೋಡಾ", "gu": "ફ્રેશ લાઈમ સોડા", "hi_en": "Fresh Lime Soda",
    },
    "Cold Drink": {
        "mr": "कोल्ड ड्रिंक", "kn": "ಕೋಲ್ಡ್ ಡ್ರಿಂಕ್", "gu": "કોલ્ડ ડ્રિંક", "hi_en": "Cold Drink",
    },
    "Buttermilk": {
        "mr": "ताक", "kn": "ಮಜ್ಜಿಗೆ", "gu": "છાશ", "hi_en": "Chaas",
    },
    "Jaljeera": {
        "mr": "जलजीरा", "kn": "ಜಲ್ಜೀರಾ", "gu": "જલજીરા", "hi_en": "Jaljeera",
    },
    "Gulab Jamun": {
        "mr": "गुलाब जामुन", "kn": "ಗುಲಾಬ್ ಜಾಮೂನ್", "gu": "ગુલાબ જાંબુ", "hi_en": "Gulab Jamun",
    },
    "Rasmalai": {
        "mr": "रसमलाई", "kn": "ರಸಮಲಾಯಿ", "gu": "રસમલાઈ", "hi_en": "Rasmalai",
    },
    "Kulfi": {
        "mr": "कुल्फी", "kn": "ಕುಲ್ಫಿ", "gu": "કુલ્ફી", "hi_en": "Kulfi",
    },
    "Jalebi": {
        "mr": "जिलेबी", "kn": "ಜಿಲೇಬಿ", "gu": "જલેબી", "hi_en": "Jalebi",
    },
    "Thandai": {
        "mr": "थंडाई", "kn": "ಠಂಡಾಯಿ", "gu": "ઠંડાઈ", "hi_en": "Thandai",
    },
    "Badam Milk": {
        "mr": "बदाम दूध", "kn": "ಬಾದಾಮಿ ಹಾಲು", "gu": "બદામ દૂધ", "hi_en": "Badam Milk",
    },
    "Paan Shot": {
        "mr": "पान शॉट", "kn": "ಪಾನ್ ಶಾಟ್", "gu": "પાન શોટ", "hi_en": "Paan Shot",
    },
}

# ── Step 4: Apply to database ──
db = SessionLocal()

print("Updating categories...")
for cat in db.query(Category).all():
    t = CATEGORY_TRANSLATIONS.get(cat.name, {})
    if t:
        cat.name_mr = t.get("mr")
        cat.name_kn = t.get("kn")
        cat.name_gu = t.get("gu")
        cat.name_hi_en = t.get("hi_en")
        print(f"  ✅ {cat.name}")

print("\nUpdating menu items...")
updated = 0
for item in db.query(MenuItem).all():
    t = ITEM_TRANSLATIONS.get(item.name, {})
    if t:
        item.name_mr = t.get("mr")
        item.name_kn = t.get("kn")
        item.name_gu = t.get("gu")
        item.name_hi_en = t.get("hi_en")
        updated += 1
        print(f"  ✅ {item.name}")
    else:
        print(f"  ⏭️  {item.name} (no translation defined)")

db.commit()
db.close()

print(f"\n🎉 Done! Updated {updated} menu items and {len(CATEGORY_TRANSLATIONS)} categories.")
print("Languages: English, Hindi, Marathi, Kannada, Gujarati, Hinglish")
