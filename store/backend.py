import os
from decimal import Decimal
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from dotenv import load_dotenv
from flask import Flask, session
from flask_session import Session
import redis


# load .env
load_dotenv()

# IMPORTS: models provides db, Product, Order
from models import db, Product, Order
from forms import CheckoutForm

# PayPal SDK
from paypalcheckoutsdk.core import PayPalHttpClient, SandboxEnvironment
from paypalcheckoutsdk.orders import OrdersCreateRequest, OrdersCaptureRequest

# Flask-Migrate import
from flask_migrate import Migrate

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'

# Cấu hình Redis làm nơi lưu session
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

app.config["SESSION_TYPE"] = "redis"
app.config["SESSION_REDIS"] = redis.from_url(redis_url)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = True
Session(app)

# ----- App factory / init -----
def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "dev-secret")
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "sqlite:///store.db")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SESSION_PERMANENT'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 1 ngày


    db.init_app(app)
    return app

app = create_app()
migrate = Migrate(app, db)
from admin import admin_bp
app.register_blueprint(admin_bp)



# ----- PayPal client factory -----
def paypal_client():
    client_id = os.getenv("PAYPAL_CLIENT_ID")
    client_secret = os.getenv("PAYPAL_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("PAYPAL CLIENT ID / SECRET missing")
    environment = SandboxEnvironment(client_id=client_id, client_secret=client_secret)
    return PayPalHttpClient(environment)


# ----- Helpers -----
def _cart_summary_from_session():
    """
    Return dict { items: [...], total: float, count: int }
    Items: { id, title, price (float), qty (int), subtotal (float), image }
    """
    cart = session.get("cart", {}) or {}
    items = []
    total = 0.0
    count = 0
    for pid_str, qty in cart.items():
        try:
            pid = int(pid_str)
            qty_i = int(qty)
        except Exception:
            continue
        product = Product.query.get(pid)
        if not product:
            continue
        # ensure numeric price
        try:
            price = float(product.price)
        except Exception:
            price = 0.0
        subtotal = price * qty_i
        total += subtotal
        count += qty_i
        items.append({
            "id": product.id,
            "title": getattr(product, "title", None) or getattr(product, "name", ""),
            "price": price,
            "qty": qty_i,
            "subtotal": subtotal,
            "image": getattr(product, "image", "") or ""
        })
    return {"items": items, "total": total, "count": count}


# ----- Routes: UI -----
@app.route("/")
def index():
    return redirect(url_for("products"))


@app.route("/products")
def products():
    # the template + products.js will call /api/products to fetch JSON
    return render_template("products.html")


@app.route("/cart")
def view_cart():
    cart = session.get("cart", {}) or {}
    items_for_template = []
    total = 0.0
    for pid_str, qty in cart.items():
        try:
            pid = int(pid_str)
            qty_i = int(qty)
        except Exception:
            continue
        product = Product.query.get(pid)
        if not product:
            continue
        price = float(product.price)
        total += price * qty_i
        items_for_template.append({"product": product, "qty": qty_i})

    paypal_client_id = os.getenv("PAYPAL_CLIENT_ID")

    return render_template("cart.html", items=items_for_template, total=total, paypal_client_id=paypal_client_id)




@app.route("/product/<int:product_id>")
def product_detail_page(product_id):
    # keep for potential direct HTML product pages
    p = Product.query.get_or_404(product_id)
    return render_template("product_detail.html", product=p)


# ----- API: products (with pagination) -----
@app.route("/api/products")
def api_products():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 9, type=int)
    q = request.args.get("q", type=str)
    category = request.args.get("category", type=str)
    price_min = request.args.get("price_min", type=float)
    price_max = request.args.get("price_max", type=float)
    sort = request.args.get("sort", type=str)

    query = Product.query

    # basic filters (if model has fields)
    if q:
        # search title or description (simple)
        query = query.filter(
            (Product.title.ilike(f"%{q}%")) | (Product.description.ilike(f"%{q}%"))
        )
    if category:
        # if Product has category attribute
        if hasattr(Product, "category"):
            query = query.filter(Product.category == category)
    if price_min is not None:
        query = query.filter(Product.price >= price_min)
    if price_max is not None:
        query = query.filter(Product.price <= price_max)

    # simple sort options
    if sort == "price_asc":
        query = query.order_by(Product.price.asc())
    elif sort == "price_desc":
        query = query.order_by(Product.price.desc())
    else:
        # default order by id desc
        query = query.order_by(Product.id.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    items = []
    for p in pagination.items:
        # ensure numeric price and default values JS expects
        try:
            price_val = float(p.price)
        except Exception:
            price_val = 0.0
        items.append({
            "id": p.id,
            "title": getattr(p, "title", None) or getattr(p, "name", ""),
            "description": getattr(p, "description", "") or "",
            "price": price_val,
            "currency": getattr(p, "currency", "USD") or "USD",
            "image": getattr(p, "image", "") or "",
            # optional fields used by frontend
            "rating": float(getattr(p, "rating", 0) or 0),
            "category": getattr(p, "category", "") or ""
        })

    return jsonify({
        "products": items,
        "total": pagination.total,
        "page": pagination.page,
        "pages": pagination.pages,
        "per_page": pagination.per_page
    })


# API single product JSON used by modal
@app.route("/api/products/<int:product_id>")
def api_product_detail(product_id):
    p = Product.query.get_or_404(product_id)
    try:
        price_val = float(p.price)
    except Exception:
        price_val = 0.0
    return jsonify({
        "id": p.id,
        "title": getattr(p, "title", None) or getattr(p, "name", ""),
        "description": getattr(p, "description", "") or "",
        "price": price_val,
        "currency": getattr(p, "currency", "USD") or "USD",
        "image": getattr(p, "image", "") or "",
        "rating": float(getattr(p, "rating", 0) or 0),
        "category": getattr(p, "category", "") or ""
    })


# ----- API: cart endpoints (JS expects /api/cart for GET, but /cart/add & /cart/update for actions) -----

@app.route("/api/cart")
def api_get_cart():
    summary = _cart_summary_from_session()
    # totals already numeric
    return jsonify(summary)


# Accepts either JSON or form-encoded body (URLSearchParams)
@app.route("/cart/add", methods=["POST"])
def cart_add():
    # support JSON body or form body
    if request.is_json:
        data = request.get_json()
        product_id = data.get("product_id")
        qty = int(data.get("qty", 1))
    else:
        product_id = request.form.get("product_id") or request.values.get("product_id")
        qty = int(request.form.get("qty", request.values.get("qty", 1)))

    try:
        pid = int(product_id)
    except Exception:
        return jsonify({"success": False, "error": "invalid product_id"}), 400

    product = Product.query.get(pid)
    if not product:
        return jsonify({"success": False, "error": "product not found"}), 404

    cart = session.get("cart", {}) or {}
    cart[str(pid)] = cart.get(str(pid), 0) + qty
    session["cart"] = cart
    session.modified = True

    summary = _cart_summary_from_session()
    return jsonify({"success": True, "cart": summary})


@app.route("/cart/update", methods=["POST"])
def cart_update():
    # support JSON or form-encoded
    if request.is_json:
        data = request.get_json()
        product_id = data.get("product_id")
        qty = data.get("qty")
    else:
        product_id = request.form.get("product_id") or request.values.get("product_id")
        qty = request.form.get("qty", request.values.get("qty", None))

    if product_id is None:
        return jsonify({"success": False, "error": "product_id required"}), 400

    try:
        pid = int(product_id)
    except Exception:
        return jsonify({"success": False, "error": "invalid product_id"}), 400

    cart = session.get("cart", {}) or {}

    # if qty is None treat as toggle or error
    if qty is None:
        return jsonify({"success": False, "error": "qty required"}), 400

    try:
        qty_i = int(qty)
    except Exception:
        return jsonify({"success": False, "error": "invalid qty"}), 400

    if qty_i <= 0:
        cart.pop(str(pid), None)
    else:
        # ensure product exists
        product = Product.query.get(pid)
        if not product:
            return jsonify({"success": False, "error": "product not found"}), 404
        cart[str(pid)] = qty_i

    session["cart"] = cart
    session.modified = True
    summary = _cart_summary_from_session()
    return jsonify({"success": True, "cart": summary})


# (optional) keep older api endpoints for compatibility
@app.route("/api/cart/add", methods=["POST"])
def api_cart_add_compat():
    # alias to /cart/add but accepts JSON
    if request.is_json:
        data = request.get_json()
        product_id = data.get("product_id")
        qty = int(data.get("qty", 1))
        # reuse logic
        return cart_add()
    else:
        return cart_add()


@app.route("/api/cart/remove", methods=["POST"])
def api_cart_remove_compat():
    # body: product_id
    if request.is_json:
        data = request.get_json()
        pid = data.get("product_id")
    else:
        pid = request.form.get("product_id") or request.values.get("product_id")
    if pid is None:
        return jsonify({"success": False, "error": "product_id required"}), 400
    cart = session.get("cart", {}) or {}
    cart.pop(str(pid), None)
    session["cart"] = cart
    session.modified = True
    return jsonify({"success": True, "cart": _cart_summary_from_session()})


# ----- PayPal endpoints (unchanged) -----
@app.route("/api/create-paypal-order", methods=["POST"])
def create_paypal_order():
    data = request.json or {}
    purchase_units = data.get("purchase_units")
    if not purchase_units:
        return jsonify({"error": "purchase_units required"}), 400

    request_order = OrdersCreateRequest()
    request_order.prefer('return=representation')
    request_order.request_body({"intent": "CAPTURE", "purchase_units": purchase_units})

    response = paypal_client().execute(request_order)
    return jsonify({"orderID": response.result.id})


from models import Order

@app.route("/api/capture-paypal-order/<order_id>", methods=["POST"])
def capture_paypal_order(order_id):
    request_capture = OrdersCaptureRequest(order_id)
    resp = paypal_client().execute(request_capture)
    result = resp.result
    amount = result.purchase_units[0].payments.captures[0].amount.value

    # Lưu đơn hàng
    order = Order(
        fullname="Khách hàng PayPal",
        email="paypal@example.com",
        address="Thanh toán qua PayPal",
        total_amount=amount,
        paypal_order_id=order_id
    )
    db.session.add(order)
    db.session.commit()

    return jsonify({"status": "success", "capture": result.__dict__})



# ----- Run -----
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)
