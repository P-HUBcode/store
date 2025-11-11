from backend import create_app
from models import db, Product

app = create_app()
with app.app_context():
    db.drop_all()
    db.create_all()

    sample = [
        {"title": "Áo Thun Basic", "description": "Áo thun cotton thoáng mát, phù hợp mặc hàng ngày", "price": 159.000, "category": "Áo", "rating": 4.4, "image": "a1.jpg"},
        {"title": "Áo Hoodie Form Rộng", "description": "Hoodie nỉ form rộng phong cách streetwear", "price": 349.000, "category": "Áo", "rating": 4.7, "image": "a2.jpg"},
        {"title": "Quần Jean Slimfit", "description": "Quần jean co giãn nhẹ, tôn dáng", "price": 420.000, "category": "Quần", "rating": 4.6, "image": "a3.jpg"},
        {"title": "Quần Jogger Nỉ", "description": "Chất nỉ dày, bo ống, thoải mái khi vận động", "price": 299.000, "category": "Quần", "rating": 4.3, "image": "a4.jpg"},
        {"title": "Áo Sơ Mi Linen", "description": "Sơ mi linen sang trọng, nhẹ và thoáng", "price": 289.000, "category": "Áo", "rating": 4.5, "image": "a5.jpg"},
        {"title": "Áo Khoác Bomber", "description": "Bomber phong cách Hàn Quốc, bền đẹp", "price": 520.000, "category": "Áo khoác", "rating": 4.8, "image": "a6.jpg"},
        {"title": "Váy Baby Doll", "description": "Dễ thương, trẻ trung, phù hợp đi chơi", "price": 350.000, "category": "Váy", "rating": 4.4, "image": "a7.jpg"},
        {"title": "Đầm Dạ Hội Dài", "description": "Thanh lịch, sang trọng, phù hợp sự kiện", "price": 890.000, "category": "Váy", "rating": 4.7, "image": "a8.jpg"},
    ]

    for s in sample:
        db.session.add(Product(**s))
    db.session.commit()
    print("✅ Seeded clothing products successfully!")
