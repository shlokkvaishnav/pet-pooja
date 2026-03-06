"""
seed_more_items.py — Add condiments, drinks, soups, street food, desserts, Indo-Chinese items
with translations in all 6 languages and realistic pricing.
"""
import sys
sys.path.insert(0, ".")

from database import SessionLocal
from models import MenuItem, Category

db = SessionLocal()

# ── Helper: get or create category ──
def get_or_create_cat(name, name_hi, name_mr, name_kn, name_gu, name_hi_en, order):
    cat = db.query(Category).filter(Category.name == name).first()
    if not cat:
        cat = Category(
            name=name, name_hi=name_hi, name_mr=name_mr,
            name_kn=name_kn, name_gu=name_gu, name_hi_en=name_hi_en,
            display_order=order, is_active=True,
        )
        db.add(cat)
        db.flush()
        print(f"  ✅ Created category: {name}")
    else:
        print(f"  ⏭️  Category exists: {name}")
    return cat


def add_item(cat_id, name, name_hi, name_mr, name_kn, name_gu, name_hi_en,
             price, cost, aliases="", is_veg=True, is_bestseller=False, tags=None):
    exists = db.query(MenuItem).filter(MenuItem.name == name).first()
    if exists:
        return
    item = MenuItem(
        name=name, name_hi=name_hi, name_mr=name_mr,
        name_kn=name_kn, name_gu=name_gu, name_hi_en=name_hi_en,
        category_id=cat_id, selling_price=price, food_cost=cost,
        aliases=aliases, is_veg=is_veg, is_available=True,
        is_bestseller=is_bestseller, tags=tags or [],
    )
    db.add(item)


# ══════════════════════════════════════════
#  CATEGORIES
# ══════════════════════════════════════════

cat_soups = get_or_create_cat(
    "Soups & Salads", "सूप और सलाद", "सूप आणि सॅलड", "ಸೂಪ್ ಮತ್ತು ಸಲಾಡ್", "સૂપ અને સલાડ", "Soups & Salads", 7
)
cat_street = get_or_create_cat(
    "Street Food & Snacks", "स्ट्रीट फूड और स्नैक्स", "स्ट्रीट फूड आणि स्नॅक्स",
    "ಸ್ಟ್ರೀಟ್ ಫುಡ್ ಮತ್ತು ಸ್ನ್ಯಾಕ್ಸ್", "સ્ટ્રીટ ફૂડ અને સ્નેક્સ", "Street Food & Snacks", 8
)
cat_chinese = get_or_create_cat(
    "Indo-Chinese", "इंडो-चाइनीज़", "इंडो-चायनीज", "ಇಂಡೋ-ಚೈನೀಸ್", "ઇન્ડો-ચાઇનીઝ", "Indo-Chinese", 9
)
cat_condiments = get_or_create_cat(
    "Condiments & Extras", "चटनी और एक्स्ट्रा", "चटणी आणि एक्स्ट्रा",
    "ಚಟ್ನಿ ಮತ್ತು ಎಕ್ಸ್ಟ್ರಾ", "ચટણી અને એક્સ્ટ્રા", "Condiments & Extras", 10
)
cat_desserts = get_or_create_cat(
    "Desserts", "मिठाई", "गोड पदार्थ", "ಸಿಹಿ ತಿಂಡಿ", "મિઠાઈ", "Desserts", 11
)

# Get existing category IDs
cat_starters = db.query(Category).filter(Category.name == "Starters").first()
cat_veg = db.query(Category).filter(Category.name == "Main Course Veg").first()
cat_nonveg = db.query(Category).filter(Category.name == "Main Course Non-Veg").first()
cat_breads = db.query(Category).filter(Category.name == "Breads").first()
cat_rice = db.query(Category).filter(Category.name == "Rice & Biryani").first()
cat_bev = db.query(Category).filter(Category.name == "Beverages").first()

print("\n── Adding new menu items ──\n")

# ══════════════════════════════════════════
#  SOUPS & SALADS
# ══════════════════════════════════════════
print("Soups & Salads...")
add_item(cat_soups.id, "Tomato Soup", "टमाटर सूप", "टोमॅटो सूप", "ಟೊಮೇಟೊ ಸೂಪ್", "ટમેટા સૂપ", "Tomato Soup",
         120, 30, "tomato soup|tamatar soup|tamatar ka soup", tags=["soup", "veg"])
add_item(cat_soups.id, "Sweet Corn Soup", "स्वीट कॉर्न सूप", "स्वीट कॉर्न सूप", "ಸ್ವೀಟ್ ಕಾರ್ನ್ ಸೂಪ್", "સ્વીટ કોર્ન સૂપ", "Sweet Corn Soup",
         130, 35, "corn soup|makai soup|sweet corn", tags=["soup", "veg"])
add_item(cat_soups.id, "Manchow Soup", "मंचाऊ सूप", "मंचाऊ सूप", "ಮಂಚೋ ಸೂಪ್", "મંચાઉ સૂપ", "Manchow Soup",
         140, 35, "manchow|man chow soup", tags=["soup", "veg", "indo-chinese"])
add_item(cat_soups.id, "Hot & Sour Soup", "हॉट एंड सॉर सूप", "हॉट अँड सॉर सूप", "ಹಾಟ್ ಅಂಡ್ ಸೌರ್ ಸೂಪ್", "હોટ એન્ડ સાર સૂપ", "Hot & Sour Soup",
         140, 35, "hot n sour|hot sour soup", tags=["soup", "veg", "spicy"])
add_item(cat_soups.id, "Chicken Soup", "चिकन सूप", "चिकन सूप", "ಚಿಕನ್ ಸೂಪ್", "ચિકન સૂપ", "Chicken Soup",
         160, 50, "chicken soup|murgh soup", is_veg=False, tags=["soup", "non-veg"])
add_item(cat_soups.id, "Green Salad", "हरा सलाद", "हिरवा सॅलड", "ಹಸಿರು ಸಲಾಡ್", "લીલું સલાડ", "Green Salad",
         80, 20, "green salad|salad|fresh salad|kachumber", tags=["salad", "healthy"])
add_item(cat_soups.id, "Russian Salad", "रशियन सलाद", "रशियन सॅलड", "ರಷ್ಯನ್ ಸಲಾಡ್", "રશિયન સલાડ", "Russian Salad",
         150, 40, "russian salad|mayo salad", tags=["salad"])
add_item(cat_soups.id, "Caesar Salad", "सीज़र सलाद", "सीझर सॅलड", "ಸೀಸರ್ ಸಲಾಡ್", "સીઝર સલાડ", "Caesar Salad",
         180, 50, "caesar salad|cesur salad", tags=["salad", "premium"])

# ══════════════════════════════════════════
#  STREET FOOD & SNACKS
# ══════════════════════════════════════════
print("Street Food & Snacks...")
add_item(cat_street.id, "Pav Bhaji", "पाव भाजी", "पाव भाजी", "ಪಾವ್ ಭಾಜಿ", "પાઉં ભાજી", "Pav Bhaji",
         160, 45, "pav bhaji|pao bhaji|pau bhaji", is_bestseller=True, tags=["street-food", "veg", "mumbai"])
add_item(cat_street.id, "Vada Pav", "वडा पाव", "वडा पाव", "ವಡಾ ಪಾವ್", "વડા પાઉં", "Vada Pav",
         50, 12, "vada pav|wada pav|batata vada", tags=["street-food", "veg", "mumbai"])
add_item(cat_street.id, "Samosa", "समोसा", "समोसा", "ಸಮೋಸಾ", "સમોસા", "Samosa",
         40, 10, "samosa|samose|aloo samosa", tags=["street-food", "veg", "snack"])
add_item(cat_street.id, "Pani Puri", "पानी पूरी", "पाणी पुरी", "ಪಾನಿ ಪೂರಿ", "પાણી પૂરી", "Pani Puri",
         80, 18, "pani puri|gol gappe|golgappa|puchka", tags=["street-food", "veg"])
add_item(cat_street.id, "Dahi Puri", "दही पूरी", "दही पुरी", "ಮೊಸರು ಪೂರಿ", "દહીં પૂરી", "Dahi Puri",
         100, 25, "dahi puri|dahi batata puri", tags=["street-food", "veg"])
add_item(cat_street.id, "Sev Puri", "सेव पूरी", "शेव पुरी", "ಸೇವ್ ಪೂರಿ", "સેવ પૂરી", "Sev Puri",
         90, 22, "sev puri|sev puri chaat", tags=["street-food", "veg"])
add_item(cat_street.id, "Bhel Puri", "भेल पूरी", "भेळ पुरी", "ಭೇಲ್ ಪೂರಿ", "ભેળ પૂરી", "Bhel Puri",
         80, 18, "bhel puri|bhel|bhelpuri", tags=["street-food", "veg"])
add_item(cat_street.id, "Aloo Tikki", "आलू टिक्की", "आलू टिक्की", "ಆಲೂ ಟಿಕ್ಕಿ", "બટાકા ટિક્કી", "Aloo Tikki",
         80, 20, "aloo tikki|aloo ki tikki|tikki", tags=["street-food", "veg"])
add_item(cat_street.id, "Masala Dosa", "मसाला डोसा", "मसाला डोसा", "ಮಸಾಲ ದೋಸೆ", "મસાલા દોસા", "Masala Dosa",
         140, 35, "masala dosa|dosa|plain dosa", is_bestseller=True, tags=["south-indian", "veg"])
add_item(cat_street.id, "Idli Sambhar", "इडली सांभर", "इडली सांबार", "ಇಡ್ಲಿ ಸಾಂಬಾರ್", "ઈડલી સાંભાર", "Idli Sambhar",
         100, 25, "idli sambar|idli sambhar|idly", tags=["south-indian", "veg"])
add_item(cat_street.id, "Medu Vada", "मेदू वड़ा", "मेदू वडा", "ಮೆದು ವಡೆ", "મેદૂ વડા", "Medu Vada",
         90, 22, "medu vada|vada sambar|medu wada", tags=["south-indian", "veg"])
add_item(cat_street.id, "Uttapam", "उत्तपम", "उत्तपम", "ಉತ್ತಪ", "ઉત્તપમ", "Uttapam",
         130, 30, "uttapam|utappa|uthappam", tags=["south-indian", "veg"])
add_item(cat_street.id, "Dabeli", "दाबेली", "दाबेली", "ದಾಬೇಲಿ", "દાબેલી", "Dabeli",
         50, 12, "dabeli|kutchi dabeli|dabeli pav", tags=["street-food", "veg", "gujarati"])
add_item(cat_street.id, "Misal Pav", "मिसल पाव", "मिसळ पाव", "ಮಿಸಲ್ ಪಾವ್", "મિસળ પાઉં", "Misal Pav",
         120, 30, "misal pav|misal|missal pav", tags=["street-food", "veg", "maharashtrian"])

# ══════════════════════════════════════════
#  INDO-CHINESE
# ══════════════════════════════════════════
print("Indo-Chinese...")
add_item(cat_chinese.id, "Veg Manchurian", "वेज मंचूरियन", "व्हेज मंचुरियन", "ವೆಜ್ ಮಂಚೂರಿಯನ್", "વેજ મંચુરિયન", "Veg Manchurian",
         180, 45, "veg manchurian|manchurian|gobi manchurian", tags=["indo-chinese", "veg"])
add_item(cat_chinese.id, "Chicken Manchurian", "चिकन मंचूरियन", "चिकन मंचुरियन", "ಚಿಕನ್ ಮಂಚೂರಿಯನ್", "ચિકન મંચુરિયન", "Chicken Manchurian",
         220, 70, "chicken manchurian|chkn manchurian", is_veg=False, tags=["indo-chinese", "non-veg"])
add_item(cat_chinese.id, "Veg Fried Rice", "वेज फ्राइड राइस", "व्हेज फ्राईड राईस", "ವೆಜ್ ಫ್ರೈಡ್ ರೈಸ್", "વેજ ફ્રાઈડ રાઈસ", "Veg Fried Rice",
         160, 40, "veg fried rice|fried rice|chinese rice", tags=["indo-chinese", "veg"])
add_item(cat_chinese.id, "Chicken Fried Rice", "चिकन फ्राइड राइस", "चिकन फ्राईड राईस", "ಚಿಕನ್ ಫ್ರೈಡ್ ರೈಸ್", "ચિકન ફ્રાઈડ રાઈસ", "Chicken Fried Rice",
         200, 60, "chicken fried rice|chkn fried rice", is_veg=False, tags=["indo-chinese", "non-veg"])
add_item(cat_chinese.id, "Veg Hakka Noodles", "वेज हक्का नूडल्स", "व्हेज हक्का नूडल्स", "ವೆಜ್ ಹಕ್ಕಾ ನೂಡಲ್ಸ್", "વેજ હક્કા નૂડલ્સ", "Veg Hakka Noodles",
         160, 40, "veg noodles|hakka noodles|chowmein", tags=["indo-chinese", "veg"])
add_item(cat_chinese.id, "Chicken Hakka Noodles", "चिकन हक्का नूडल्स", "चिकन हक्का नूडल्स", "ಚಿಕನ್ ಹಕ್ಕಾ ನೂಡಲ್ಸ್", "ચિકન હક્કા નૂડલ્સ", "Chicken Hakka Noodles",
         200, 60, "chicken noodles|chkn noodles|chkn chowmein", is_veg=False, tags=["indo-chinese", "non-veg"])
add_item(cat_chinese.id, "Paneer Chilli", "पनीर चिल्ली", "पनीर चिल्ली", "ಪನೀರ್ ಚಿಲ್ಲಿ", "પનીર ચિલ્લી", "Paneer Chilli",
         200, 55, "paneer chilli|chilli paneer|panir chili", tags=["indo-chinese", "veg", "spicy"])
add_item(cat_chinese.id, "Chicken 65", "चिकन 65", "चिकन 65", "ಚಿಕನ್ 65", "ચિકન 65", "Chicken 65",
         240, 75, "chicken 65|chkn 65|chicken sixtyfive", is_veg=False, tags=["indo-chinese", "non-veg", "spicy"])
add_item(cat_chinese.id, "Gobi 65", "गोभी 65", "गोबी 65", "ಗೋಬಿ 65", "ગોબી 65", "Gobi 65",
         180, 40, "gobi 65|cauliflower 65|gobi sixtyfive", tags=["indo-chinese", "veg", "spicy"])
add_item(cat_chinese.id, "Schezwan Fried Rice", "शेजवान फ्राइड राइस", "शेझवान फ्राईड राईस", "ಶೆಜ್ವಾನ್ ಫ್ರೈಡ್ ರೈಸ್", "શેઝવાન ફ્રાઈડ રાઈસ", "Schezwan Fried Rice",
         180, 45, "schezwan rice|szechuan rice|schezwan fry rice", tags=["indo-chinese", "veg", "spicy"])
add_item(cat_chinese.id, "Veg Spring Roll (Chinese)", "वेज स्प्रिंग रोल (चाइनीज)", "व्हेज स्प्रिंग रोल (चायनीज)", "ವೆಜ್ ಸ್ಪ್ರಿಂಗ್ ರೋಲ್ (ಚೈನೀಸ್)", "વેજ સ્પ્રિંગ રોલ (ચાઇનીઝ)", "Veg Spring Roll (Chinese)",
         150, 35, "chinese spring roll|crispy spring roll", tags=["indo-chinese", "veg"])

# ══════════════════════════════════════════
#  CONDIMENTS & EXTRAS
# ══════════════════════════════════════════
print("Condiments & Extras...")
add_item(cat_condiments.id, "Raita", "रायता", "रायते", "ರೈತಾ", "રાયતું", "Raita",
         60, 15, "raita|boondi raita|mix raita|dahi raita", tags=["condiment", "veg"])
add_item(cat_condiments.id, "Papad", "पापड़", "पापड", "ಪಾಪಡ್", "પાપડ", "Papad",
         30, 5, "papad|papadum|papad fry|roasted papad", tags=["condiment", "veg"])
add_item(cat_condiments.id, "Masala Papad", "मसाला पापड़", "मसाला पापड", "ಮಸಾಲ ಪಾಪಡ್", "મસાલા પાપડ", "Masala Papad",
         50, 10, "masala papad|masala papadum", tags=["condiment", "veg"])
add_item(cat_condiments.id, "Green Chutney", "हरी चटनी", "हिरवी चटणी", "ಹಸಿರು ಚಟ್ನಿ", "લીલી ચટણી", "Hari Chutney",
         20, 5, "green chutney|hari chutney|pudina chutney|mint chutney", tags=["condiment", "veg"])
add_item(cat_condiments.id, "Tamarind Chutney", "इमली की चटनी", "चिंचेची चटणी", "ಹುಣಸೆ ಚಟ್ನಿ", "આમલીની ચટણી", "Imli Chutney",
         20, 5, "tamarind chutney|imli chutney|meethi chutney|khajur chutney", tags=["condiment", "veg"])
add_item(cat_condiments.id, "Pickle (Achar)", "अचार", "लोणचे", "ಉಪ್ಪಿನಕಾಯಿ", "અથાણું", "Achar",
         30, 8, "pickle|achar|mango pickle|aam ka achar|mixed pickle", tags=["condiment", "veg"])
add_item(cat_condiments.id, "Onion Salad", "प्याज़ सलाद", "कांदा सॅलड", "ಈರುಳ್ಳಿ ಸಲಾಡ್", "ડુંગળી સલાડ", "Onion Salad",
         30, 5, "onion salad|pyaaz salad|kanda salad|laccha pyaaz", tags=["condiment", "veg"])
add_item(cat_condiments.id, "Extra Gravy", "एक्स्ट्रा ग्रेवी", "एक्स्ट्रा ग्रेव्ही", "ಎಕ್ಸ್ಟ್ರಾ ಗ್ರೇವಿ", "એક્સ્ટ્રા ગ્રેવી", "Extra Gravy",
         40, 12, "extra gravy|gravy|side gravy", tags=["condiment"])
add_item(cat_condiments.id, "Curd (Bowl)", "दही (कटोरी)", "दही (वाटी)", "ಮೊಸರು (ಬೌಲ್)", "દહીં (વાટકી)", "Dahi Bowl",
         40, 10, "curd|dahi|plain curd|dahi bowl", tags=["condiment", "veg"])
add_item(cat_condiments.id, "Butter (Extra)", "मक्खन (एक्स्ट्रा)", "लोणी (एक्स्ट्रा)", "ಬೆಣ್ಣೆ (ಎಕ್ಸ್ಟ್ರಾ)", "માખણ (એક્સ્ટ્રા)", "Extra Butter",
         20, 6, "butter|extra butter|makhan", tags=["condiment", "veg"])
add_item(cat_condiments.id, "Ghee (Extra)", "घी (एक्स्ट्रा)", "तूप (एक्स्ट्रा)", "ತುಪ್ಪ (ಎಕ್ಸ್ಟ್ರಾ)", "ઘી (એક્સ્ટ્રા)", "Extra Ghee",
         30, 12, "ghee|extra ghee|desi ghee", tags=["condiment", "veg"])

# ══════════════════════════════════════════
#  MORE BEVERAGES & DRINKS
# ══════════════════════════════════════════
print("More Beverages...")
add_item(cat_bev.id, "Virgin Mojito", "वर्जिन मोजिटो", "व्हर्जिन मोजिटो", "ವರ್ಜಿನ್ ಮೊಜಿಟೊ", "વર્જિન મોજીટો", "Virgin Mojito",
         180, 40, "mojito|virgin mojito|lime mojito|mint mojito", tags=["drink", "mocktail"])
add_item(cat_bev.id, "Blue Lagoon", "ब्लू लैगून", "ब्लू लगून", "ಬ್ಲೂ ಲಗೂನ್", "બ્લુ લગૂન", "Blue Lagoon",
         180, 40, "blue lagoon|blue mocktail", tags=["drink", "mocktail"])
add_item(cat_bev.id, "Watermelon Juice", "तरबूज़ जूस", "कलिंगड ज्यूस", "ಕಲ್ಲಂಗಡಿ ಜ್ಯೂಸ್", "તરબૂચ જ્યૂસ", "Watermelon Juice",
         120, 25, "watermelon juice|tarbooz juice|tarbooj", tags=["drink", "fresh", "healthy"])
add_item(cat_bev.id, "Sugarcane Juice", "गन्ने का रस", "उसाचा रस", "ಕಬ್ಬಿನ ಜ್ಯೂಸ್", "શેરડીનો રસ", "Ganne Ka Juice",
         80, 15, "sugarcane juice|ganne ka ras|ganna juice", tags=["drink", "fresh"])
add_item(cat_bev.id, "Kokum Sharbat", "कोकम शरबत", "कोकम सरबत", "ಕೊಕಂ ಶರ್ಬತ್", "કોકમ શરબત", "Kokum Sharbat",
         80, 15, "kokum sharbat|kokum juice|sol kadhi", tags=["drink", "konkan"])
add_item(cat_bev.id, "Rose Sharbat", "रूह अफ़ज़ा", "गुलाब सरबत", "ರೋಸ್ ಶರ್ಬತ್", "ગુલાબ શરબત", "Rose Sharbat",
         70, 12, "rose sharbat|rooh afza|gulab sharbat", tags=["drink"])
add_item(cat_bev.id, "Filter Coffee", "फ़िल्टर कॉफ़ी", "फिल्टर कॉफी", "ಫಿಲ್ಟರ್ ಕಾಫಿ", "ફિલ્ટર કોફી", "Filter Coffee",
         80, 15, "filter coffee|south indian coffee|kaapi", tags=["drink", "hot", "south-indian"])
add_item(cat_bev.id, "Hot Chocolate", "हॉट चॉकलेट", "हॉट चॉकलेट", "ಹಾಟ್ ಚಾಕಲೇಟ್", "હોટ ચોકલેટ", "Hot Chocolate",
         150, 35, "hot chocolate|hot choco|cocoa", tags=["drink", "hot"])
add_item(cat_bev.id, "Iced Tea", "आइस्ड टी", "आईस्ड टी", "ಐಸ್ಡ್ ಟೀ", "આઈસ્ડ ટી", "Iced Tea",
         120, 25, "iced tea|ice tea|lemon iced tea", tags=["drink", "cold"])
add_item(cat_bev.id, "Nimbu Pani", "नींबू पानी", "लिंबू पाणी", "ನಿಂಬೆ ಪಾನಿ", "લીંબુ પાણી", "Nimbu Pani",
         50, 8, "nimbu pani|nimbu paani|lemon water|shikanji", tags=["drink", "fresh"])
add_item(cat_bev.id, "Oreo Shake", "ओरियो शेक", "ओरिओ शेक", "ಓರಿಯೋ ಶೇಕ್", "ઓરિયો શેક", "Oreo Shake",
         180, 45, "oreo shake|oreo milkshake|cookies shake", tags=["drink", "shake"])
add_item(cat_bev.id, "Banana Shake", "बनाना शेक", "केळी शेक", "ಬಾಳೆಹಣ್ಣು ಶೇಕ್", "કેળા શેક", "Banana Shake",
         120, 25, "banana shake|banana milkshake|kela shake", tags=["drink", "shake"])
add_item(cat_bev.id, "Strawberry Shake", "स्ट्रॉबेरी शेक", "स्ट्रॉबेरी शेक", "ಸ್ಟ್ರಾಬೆರಿ ಶೇಕ್", "સ્ટ્રોબેરી શેક", "Strawberry Shake",
         150, 35, "strawberry shake|strawberry milkshake", tags=["drink", "shake"])
add_item(cat_bev.id, "Salted Lassi", "नमकीन लस्सी", "मठ्ठा", "ಉಪ್ಪಿನ ಲಸ್ಸಿ", "ખારી લસ્સી", "Salted Lassi",
         80, 15, "salted lassi|namkeen lassi|salt lassi|mattha", tags=["drink", "veg"])

# ══════════════════════════════════════════
#  DESSERTS (new items)
# ══════════════════════════════════════════
print("Desserts...")
add_item(cat_desserts.id, "Gajar Ka Halwa", "गाजर का हलवा", "गाजर हलवा", "ಕ್ಯಾರೆಟ್ ಹಲ್ವಾ", "ગાજરનો હલવો", "Gajar Ka Halwa",
         120, 35, "gajar halwa|carrot halwa|gajar ka halwa", tags=["dessert", "veg", "winter-special"])
add_item(cat_desserts.id, "Kheer", "खीर", "खीर", "ಕೀರ್", "ખીર", "Kheer",
         100, 25, "kheer|rice kheer|chawal ki kheer|payasam", tags=["dessert", "veg"])
add_item(cat_desserts.id, "Shahi Tukda", "शाही टुकड़ा", "शाही तुकडा", "ಶಾಹಿ ತುಕ್ಡಾ", "શાહી ટુકડા", "Shahi Tukda",
         140, 40, "shahi tukda|shahi tukra|double ka meetha", tags=["dessert", "veg", "mughlai"])
add_item(cat_desserts.id, "Rabri", "रबड़ी", "रबडी", "ರಬ್ರಿ", "રબડી", "Rabri",
         100, 30, "rabri|rabdi|malai rabri", tags=["dessert", "veg"])
add_item(cat_desserts.id, "Moong Dal Halwa", "मूंग दाल हलवा", "मूग डाळ हलवा", "ಮೂಂಗ್ ದಾಲ್ ಹಲ್ವಾ", "મૂંગ દાળ હલવો", "Moong Dal Halwa",
         130, 40, "moong dal halwa|moong halwa", tags=["dessert", "veg", "winter-special"])
add_item(cat_desserts.id, "Ice Cream (Scoop)", "आइसक्रीम (स्कूप)", "आईस्क्रीम (स्कूप)", "ಐಸ್ ಕ್ರೀಮ್ (ಸ್ಕೂಪ್)", "આઈસક્રીમ (સ્કૂપ)", "Ice Cream Scoop",
         80, 20, "ice cream|icecream|scoop|vanilla|chocolate ice cream", tags=["dessert"])
add_item(cat_desserts.id, "Brownie with Ice Cream", "ब्राउनी विथ आइसक्रीम", "ब्राउनी विथ आईस्क्रीम", "ಬ್ರೌನಿ ವಿತ್ ಐಸ್ ಕ್ರೀಮ್", "બ્રાઉની વિથ આઈસક્રીમ", "Brownie with Ice Cream",
         180, 50, "brownie|brownie ice cream|chocolate brownie", tags=["dessert", "premium"])
add_item(cat_desserts.id, "Phirni", "फिरनी", "फिरनी", "ಫಿರ್ನಿ", "ફિરની", "Phirni",
         90, 22, "phirni|firni|rice pudding", tags=["dessert", "veg", "mughlai"])

# ══════════════════════════════════════════
#  MORE STARTERS
# ══════════════════════════════════════════
print("More Starters...")
add_item(cat_starters.id, "Paneer 65", "पनीर 65", "पनीर 65", "ಪನೀರ್ 65", "પનીર 65", "Paneer 65",
         220, 60, "paneer 65|paneer sixtyfive|pnr 65", tags=["starter", "veg", "spicy"])
add_item(cat_starters.id, "Crispy Corn", "क्रिस्पी कॉर्न", "क्रिस्पी कॉर्न", "ಕ್ರಿಸ್ಪಿ ಕಾರ್ನ್", "ક્રિસ્પી કોર્ન", "Crispy Corn",
         180, 40, "crispy corn|corn pepper salt|corn golden fry", tags=["starter", "veg"])
add_item(cat_starters.id, "Chicken Lollipop", "चिकन लॉलीपॉप", "चिकन लॉलीपॉप", "ಚಿಕನ್ ಲಾಲಿಪಾಪ್", "ચિકન લોલીપોપ", "Chicken Lollipop",
         260, 85, "chicken lollipop|lollypop|chkn lollipop", is_veg=False, is_bestseller=True, tags=["starter", "non-veg"])
add_item(cat_starters.id, "Chicken Wings", "चिकन विंग्स", "चिकन विंग्ज", "ಚಿಕನ್ ವಿಂಗ್ಸ್", "ચિકન વિંગ્સ", "Chicken Wings",
         280, 90, "chicken wings|hot wings|buffalo wings", is_veg=False, tags=["starter", "non-veg", "spicy"])
add_item(cat_starters.id, "Tandoori Paneer Tikka", "तंदूरी पनीर टिक्का", "तंदूरी पनीर टिक्का", "ತಂದೂರಿ ಪನೀರ್ ಟಿಕ್ಕಾ", "તંદૂરી પનીર ટિક્કા", "Tandoori Paneer Tikka",
         240, 65, "tandoori paneer|achari paneer tikka|paneer tandoori", tags=["starter", "veg", "tandoor"])
add_item(cat_starters.id, "Fish Finger", "फिश फिंगर", "फिश फिंगर", "ಫಿಶ್ ಫಿಂಗರ್", "ફિશ ફિંગર", "Fish Finger",
         260, 80, "fish finger|fish fingers|fish fry", is_veg=False, tags=["starter", "non-veg"])

# ══════════════════════════════════════════
#  MORE MAIN COURSE
# ══════════════════════════════════════════
print("More Mains...")
add_item(cat_veg.id, "Paneer Do Pyaza", "पनीर दो प्याज़ा", "पनीर दो प्याजा", "ಪನೀರ್ ದೋ ಪ್ಯಾಜಾ", "પનીર દો પ્યાઝા", "Paneer Do Pyaza",
         260, 70, "paneer do pyaza|paneer do pyaaza|pnr do pyaza", tags=["main", "veg"])
add_item(cat_veg.id, "Methi Malai Matar", "मेथी मलाई मटर", "मेथी मलाई मटर", "ಮೆಥಿ ಮಲಾಯಿ ಮಟರ್", "મેથી મલાઈ મટર", "Methi Malai Matar",
         240, 60, "methi malai matar|methi matar malai", tags=["main", "veg"])
add_item(cat_veg.id, "Baingan Bharta", "बैंगन भर्ता", "वांग्याचे भरीत", "ಬದನೆ ಭರ್ತಾ", "રીંગણ ભર્થું", "Baingan Bharta",
         200, 45, "baingan bharta|baigan bharta|brinjal bharta|vangyache bharit", tags=["main", "veg"])
add_item(cat_nonveg.id, "Chicken Do Pyaza", "चिकन दो प्याज़ा", "चिकन दो प्याजा", "ಚಿಕನ್ ದೋ ಪ್ಯಾಜಾ", "ચિકન દો પ્યાઝા", "Chicken Do Pyaza",
         300, 95, "chicken do pyaza|chkn do pyaza", is_veg=False, tags=["main", "non-veg"])
add_item(cat_nonveg.id, "Mutton Nihari", "मटन निहारी", "मटण निहारी", "ಮಟನ್ ನಿಹಾರಿ", "મટન નિહારી", "Mutton Nihari",
         380, 130, "mutton nihari|nihari|nalli nihari", is_veg=False, tags=["main", "non-veg", "mughlai"])
add_item(cat_nonveg.id, "Tandoori Prawns", "तंदूरी प्रॉन्स", "तंदूरी कोळंबी", "ತಂದೂರಿ ಸಿಗಡಿ", "તંદૂરી ઝીંગા", "Tandoori Prawns",
         400, 150, "tandoori prawns|prawn tandoori|jhinga tandoori", is_veg=False, tags=["main", "non-veg", "seafood", "premium"])

# ══════════════════════════════════════════
#  MORE BREADS
# ══════════════════════════════════════════
print("More Breads...")
add_item(cat_breads.id, "Stuffed Naan", "स्टफ्ड नान", "स्टफ्ड नान", "ಸ್ಟಫ್ಡ್ ನಾನ್", "સ્ટફ્ડ નાન", "Stuffed Naan",
         70, 20, "stuffed naan|aloo naan|paneer naan|keema naan", tags=["bread"])
add_item(cat_breads.id, "Pudina Paratha", "पुदीना पराठा", "पुदीना पराठा", "ಪುದೀನ ಪರಾಠಾ", "ફુદીનો પરાઠો", "Pudina Paratha",
         60, 15, "pudina paratha|mint paratha", tags=["bread", "veg"])
add_item(cat_breads.id, "Aloo Paratha", "आलू पराठा", "आलू पराठा", "ಆಲೂ ಪರಾಠಾ", "બટાકા પરાઠો", "Aloo Paratha",
         70, 18, "aloo paratha|stuffed paratha|aloo ka paratha", tags=["bread", "veg"])
add_item(cat_breads.id, "Puri", "पूरी", "पुरी", "ಪೂರಿ", "પૂરી", "Puri",
         50, 12, "puri|poori|fried puri", tags=["bread", "veg"])

# Commit all
db.commit()

# Count
total_new = db.query(MenuItem).count()
print(f"\n🎉 Done! Total menu items now: {total_new}")
print(f"   Categories: {db.query(Category).count()}")
db.close()
