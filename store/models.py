# models.py
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Numeric(10,2), nullable=False)
    currency = db.Column(db.String(3), default="USD")
    image = db.Column(db.String(500), nullable=True)

    # NEW fields
    category = db.Column(db.String(100), nullable=True)
    rating = db.Column(db.Float, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "price": str(self.price),
            "currency": self.currency,
            "image": self.image,
            "category": self.category,
            "rating": self.rating
        }

class Order(db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    address = db.Column(db.String(400), nullable=False)
    total_amount = db.Column(db.Numeric(10,2), nullable=False)
    currency = db.Column(db.String(3), default="USD")
    paypal_order_id = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "fullname": self.fullname,
            "email": self.email,
            "address": self.address,
            "total_amount": str(self.total_amount),
            "currency": self.currency,
            "paypal_order_id": self.paypal_order_id,
            "created_at": self.created_at.isoformat()
        }
