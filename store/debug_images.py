# debug_images.py  -- builds static URLs without using url_for to avoid SERVER_NAME issue
import os
from backend import create_app
from models import db, Product

def main():
    basedir = os.path.dirname(__file__)
    images_dir = os.path.join(basedir, 'static', 'images')
    print("Images folder (FS):", images_dir)
    print("Files in images folder:")
    try:
        files_on_disk = sorted(os.listdir(images_dir))
        for f in files_on_disk:
            print("  ", f)
    except Exception as e:
        print("  Error listing images folder:", e)
        return

    app = create_app()
    with app.app_context():
        prods = Product.query.all()
        if not prods:
            print("No products found in DB.")
            return
        print("\nProducts in DB and image resolution check:")
        for p in prods:
            db_img = p.image
            # Construct static path (relative) and absolute URL for convenience
            rel_url = f"/static/images/{db_img}" if db_img else None
            abs_url = f"http://127.0.0.1:5000/static/images/{db_img}" if db_img else None

            exact_fs_path = os.path.join(images_dir, db_img) if db_img else None
            exists_fs = os.path.exists(exact_fs_path) if exact_fs_path else False

            # case-insensitive lookup
            files_lower = {f.lower(): f for f in files_on_disk}
            ci_match = files_lower.get(db_img.lower()) if db_img else None
            ci_exists = ci_match is not None

            print(f"- id={p.id} title='{p.title}'")
            print(f"    DB image field: {repr(db_img)}")
            print(f"    Expected rel URL: {rel_url}")
            print(f"    Expected abs URL: {abs_url}")
            print(f"    Exact FS path: {exact_fs_path} -> exists: {exists_fs}")
            if not exists_fs:
                if ci_exists:
                    print(f"    Case-insensitive match on disk: {ci_match} (suggest rename or update DB to '{ci_match}')")
                else:
                    print("    No match on disk (file missing).")
        # Print a compact sample JSON for first product (with rel_url)
        first = prods[0]
        sample = {
            'id': first.id,
            'title': first.title,
            'image': f"/static/images/{first.image}" if first.image else None
        }
        import json
        print("\nSample product JSON (first product):")
        print(json.dumps(sample, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
