"""
Database Seed Script
====================
Populates the database with initial data:
- Admin user
- Sample categories
- Sample handicraft products

Run with: python seed.py
"""

from .database import SessionLocal, create_tables
from .models.user import User, UserRole
from .models.product import Product, Category
from .security import hash_password


def seed_database():
    create_tables()
    db = SessionLocal()

    try:
        # ─── Create Admin User ───────────────────────
        admin_email = "admin@nepalihandicrafts.com"
        if not db.query(User).filter(User.email == admin_email).first():
            admin = User(
                full_name="Admin User",
                email=admin_email,
                hashed_password=hash_password("Admin@123"),
                role=UserRole.ADMIN,
                is_active=True,
                phone="+977-1-4567890",
                city="Kathmandu",
                country="Nepal",
            )
            db.add(admin)
            print(f"✅ Admin created: {admin_email} / Admin@123")

        # ─── Create Test User ───────────────────────
        test_email = "test@example.com"
        if not db.query(User).filter(User.email == test_email).first():
            test_user = User(
                full_name="Test User",
                email=test_email,
                hashed_password=hash_password("Test@1234"),
                role=UserRole.USER,
                is_active=True,
                phone="+977-9841234567",
                city="Pokhara",
                country="Nepal",
            )
            db.add(test_user)
            print(f"✅ Test user created: {test_email} / Test@1234")

        db.commit()

        # ─── Create Categories ───────────────────────
        categories_data = [
            {"name": "Pashmina & Shawls", "slug": "pashmina-shawls",
             "description": "Luxurious hand-woven pashmina products from Nepal"},
            {"name": "Thangka Paintings", "slug": "thangka-paintings",
             "description": "Traditional Tibetan Buddhist scroll paintings"},
            {"name": "Wooden Crafts", "slug": "wooden-crafts",
             "description": "Hand-carved wooden items from Newari artisans"},
            {"name": "Singing Bowls", "slug": "singing-bowls",
             "description": "Himalayan singing bowls for meditation and healing"},
            {"name": "Jewelry & Accessories", "slug": "jewelry-accessories",
             "description": "Traditional Nepali silver and gemstone jewelry"},
            {"name": "Carpets & Rugs", "slug": "carpets-rugs",
             "description": "Handmade Tibetan and Nepali wool carpets"},
            {"name": "Pottery & Ceramics", "slug": "pottery-ceramics",
             "description": "Traditional Bhaktapur pottery and ceramics"},
        ]

        categories = {}
        for cat_data in categories_data:
            existing = db.query(Category).filter(Category.slug == cat_data["slug"]).first()
            if not existing:
                category = Category(**cat_data)
                db.add(category)
                db.commit()
                db.refresh(category)
                categories[cat_data["slug"]] = category
                print(f"✅ Category: {cat_data['name']}")
            else:
                categories[cat_data["slug"]] = existing

        # ─── Create Products ───────────────────────
        products_data = [
            {
                "name": "Premium Cashmere Pashmina Shawl",
                "slug": "premium-cashmere-pashmina-shawl",
                "description": "Authentic hand-woven 100% cashmere pashmina from the highlands of Nepal. "
                               "Each shawl is meticulously crafted by skilled artisans in Kathmandu Valley, "
                               "following centuries-old weaving traditions.",
                "short_description": "Authentic 100% cashmere, hand-woven in Nepal",
                "price_npr": 8500.0,
                "price_usd": 63.75,
                "discount_percent": 10.0,
                "stock_quantity": 50,
                "sku": "PSH-001",
                "material": "100% Cashmere",
                "origin": "Kathmandu",
                "weight_grams": 250.0,
                "dimensions": "200x70 cm",
                "is_featured": True,
                "category_slug": "pashmina-shawls",
            },
            {
                "name": "Traditional Thangka - Green Tara",
                "slug": "thangka-green-tara",
                "description": "Hand-painted traditional Thangka depicting Green Tara, "
                               "the female Bodhisattva of compassion. Painted with natural mineral pigments "
                               "on cotton canvas by a master thangka artist from Patan.",
                "short_description": "Hand-painted by master artists, natural mineral pigments",
                "price_npr": 25000.0,
                "price_usd": 187.5,
                "discount_percent": 0.0,
                "stock_quantity": 10,
                "sku": "TKA-001",
                "material": "Natural Mineral Pigments on Cotton Canvas",
                "origin": "Patan",
                "weight_grams": 500.0,
                "dimensions": "45x35 cm",
                "is_featured": True,
                "category_slug": "thangka-paintings",
            },
            {
                "name": "Hand-carved Wooden Elephant Set",
                "slug": "hand-carved-wooden-elephant-set",
                "description": "Set of 3 hand-carved wooden elephants in different sizes, "
                               "crafted from sustainable sal wood. Each piece is uniquely painted "
                               "by Newari craftsmen from Bhaktapur.",
                "short_description": "Set of 3, sustainable sal wood, hand-painted",
                "price_npr": 3500.0,
                "price_usd": 26.25,
                "discount_percent": 15.0,
                "stock_quantity": 35,
                "sku": "WOD-001",
                "material": "Sal Wood",
                "origin": "Bhaktapur",
                "weight_grams": 800.0,
                "is_featured": False,
                "category_slug": "wooden-crafts",
            },
            {
                "name": "Himalayan Singing Bowl Set - 7 Chakra",
                "slug": "himalayan-singing-bowl-7-chakra",
                "description": "Authentic 7-metal Himalayan singing bowl handcrafted in Nepal. "
                               "Each bowl is tuned to correspond to one of the 7 chakras. "
                               "Includes mallet, cushion, and a guide to chakra meditation.",
                "short_description": "7-metal, hand-hammered, includes accessories",
                "price_npr": 6000.0,
                "price_usd": 45.0,
                "discount_percent": 0.0,
                "stock_quantity": 25,
                "sku": "SBO-001",
                "material": "7 Metals (Brass, Copper, Tin, Iron, Lead, Silver, Gold)",
                "origin": "Kathmandu",
                "weight_grams": 600.0,
                "dimensions": "15 cm diameter",
                "is_featured": True,
                "category_slug": "singing-bowls",
            },
            {
                "name": "Tibetan Silver Om Necklace",
                "slug": "tibetan-silver-om-necklace",
                "description": "Sterling silver necklace featuring the sacred Om symbol, "
                               "handcrafted by Tibetan silversmiths. Comes with a 18-inch chain. "
                               "Perfect for meditation practitioners.",
                "short_description": "925 Sterling Silver, handcrafted by Tibetan artisans",
                "price_npr": 2800.0,
                "price_usd": 21.0,
                "discount_percent": 0.0,
                "stock_quantity": 60,
                "sku": "JWL-001",
                "material": "925 Sterling Silver",
                "origin": "Kathmandu",
                "weight_grams": 25.0,
                "is_featured": False,
                "category_slug": "jewelry-accessories",
            },
            {
                "name": "Tibetan Dragon Wool Carpet",
                "slug": "tibetan-dragon-wool-carpet",
                "description": "Premium hand-knotted Tibetan carpet featuring a traditional dragon design. "
                               "Made from 100% Himalayan wool with natural dyes. "
                               "80 knots per square inch for exceptional durability.",
                "short_description": "100% Himalayan wool, natural dyes, 80 knots/sq inch",
                "price_npr": 45000.0,
                "price_usd": 337.5,
                "discount_percent": 5.0,
                "stock_quantity": 8,
                "sku": "CAR-001",
                "material": "100% Himalayan Wool with Natural Dyes",
                "origin": "Kathmandu",
                "weight_grams": 3500.0,
                "dimensions": "150x90 cm",
                "is_featured": True,
                "category_slug": "carpets-rugs",
            },
            {
                "name": "Bhaktapur Pottery Vase",
                "slug": "bhaktapur-pottery-vase",
                "description": "Traditional hand-thrown pottery vase from Bhaktapur's master potters. "
                               "Made using ancient techniques passed down for generations. "
                               "Each piece is unique with slight natural variations.",
                "short_description": "Hand-thrown, traditional Bhaktapur craft",
                "price_npr": 1800.0,
                "price_usd": 13.5,
                "discount_percent": 0.0,
                "stock_quantity": 40,
                "sku": "POT-001",
                "material": "Natural Clay",
                "origin": "Bhaktapur",
                "weight_grams": 700.0,
                "dimensions": "25 cm height",
                "is_featured": False,
                "category_slug": "pottery-ceramics",
            },
        ]

        for prod_data in products_data:
            cat_slug = prod_data.pop("category_slug")
            category = categories.get(cat_slug)

            if not db.query(Product).filter(Product.slug == prod_data["slug"]).first():
                product = Product(
                    **prod_data,
                    category_id=category.id if category else None,
                    is_active=True,
                )
                db.add(product)
                print(f"✅ Product: {prod_data['name']}")

        db.commit()
        print("\n🎉 Database seeded successfully!")
        print("\n📋 Login Credentials:")
        print("   Admin:     admin@nepalihandicrafts.com / Admin@123")
        print("   Test User: test@example.com / Test@1234")

    finally:
        db.close()


if __name__ == "__main__":
    seed_database()