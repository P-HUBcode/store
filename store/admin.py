import os
from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from models import db, Product
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader

load_dotenv()
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

# 🧩 Cấu hình Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

# 🧠 Hàm kiểm tra đăng nhập
def require_login():
    if not session.get("is_admin"):
        return redirect(url_for("admin.login"))

# 🟢 Đăng nhập
@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password")
        admin_pass = os.getenv("ADMIN_PASSWORD", "admin")
        if password == admin_pass:
            session["is_admin"] = True
            flash("✅ Đăng nhập thành công!", "success")
            return redirect(url_for("admin.index"))
        else:
            flash("❌ Sai mật khẩu!", "danger")
    return render_template("admin/login.html")

# 🔴 Đăng xuất
@admin_bp.route("/logout")
def logout():
    session.pop("is_admin", None)
    flash("👋 Đã đăng xuất!", "info")
    return redirect(url_for("admin.login"))

# 🧩 Danh sách sản phẩm
@admin_bp.route("/")
def index():
    if not session.get("is_admin"):
        return redirect(url_for("admin.login"))
    products = Product.query.order_by(Product.id.desc()).all()
    return render_template("admin/index.html", products=products)

# 🟢 Thêm sản phẩm
@admin_bp.route("/add", methods=["GET", "POST"])
def add_product():
    if not session.get("is_admin"):
        return redirect(url_for("admin.login"))

    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        price = request.form.get("price")
        category = request.form.get("category")
        rating = request.form.get("rating")
        image_file = request.files.get("image")

        image_url = None
        if image_file:
            upload_result = cloudinary.uploader.upload(image_file)
            image_url = upload_result.get("secure_url")

        product = Product(
            title=title,
            description=description,
            price=float(price or 0),
            category=category,
            rating=float(rating or 0),
            image=image_url
        )
        db.session.add(product)
        db.session.commit()
        flash("✅ Đã thêm sản phẩm mới!", "success")
        return redirect(url_for("admin.index"))

    return render_template("admin/add_product.html")

# 🟡 Sửa sản phẩm
@admin_bp.route("/edit/<int:product_id>", methods=["GET", "POST"])
def edit_product(product_id):
    if not session.get("is_admin"):
        return redirect(url_for("admin.login"))

    product = Product.query.get_or_404(product_id)

    if request.method == "POST":
        product.title = request.form.get("title")
        product.description = request.form.get("description")
        product.price = float(request.form.get("price") or 0)
        product.category = request.form.get("category")
        product.rating = float(request.form.get("rating") or 0)

        image_file = request.files.get("image")
        if image_file:
            # 🧠 Nếu sản phẩm đã có ảnh Cloudinary cũ → xóa
            if product.image and product.image.startswith("https://res.cloudinary.com/"):
                try:
                    # Tách public_id từ URL cũ
                    old_public_id = product.image.split("/")[-1].split(".")[0]
                    cloudinary.uploader.destroy(old_public_id)
                    print(f"🗑️ Đã xóa ảnh cũ trên Cloudinary: {old_public_id}")
                except Exception as e:
                    print("⚠️ Không thể xóa ảnh cũ:", e)

            # 🆕 Upload ảnh mới
            upload_result = cloudinary.uploader.upload(image_file)
            product.image = upload_result.get("secure_url")

        db.session.commit()
        flash("✅ Cập nhật sản phẩm thành công!", "success")
        return redirect(url_for("admin.index"))

    return render_template("admin/edit_product.html", product=product)


# 🔴 Xóa sản phẩm
@admin_bp.route("/delete/<int:product_id>")
def delete_product(product_id):
    if not session.get("is_admin"):
        return redirect(url_for("admin.login"))

    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash("🗑️ Đã xóa sản phẩm", "warning")
    return redirect(url_for("admin.index"))
