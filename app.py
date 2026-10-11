import pymysql
pymysql.install_as_MySQLdb()
import os, math, smtplib
from email.message import EmailMessage
from datetime import date
from functools import wraps
from decimal import Decimal, InvalidOperation
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort, jsonify, current_app
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from models import User

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config.from_object(Config)
mysql = MySQL(app)
csrf = CSRFProtect(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = "warning"

@login_manager.user_loader
def load_user(user_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT id,name,email,password_hash,role,phone,birthday FROM users WHERE id=%s", (user_id,))
    row = cur.fetchone(); cur.close()
    return User(row) if row else None

def query(sql, params=(), one=False):
    cur = mysql.connection.cursor()
    cur.execute(sql, params)
    result = cur.fetchone() if one else cur.fetchall()
    cur.close()
    return result

def execute(sql, params=()):
    cur = mysql.connection.cursor(); cur.execute(sql, params)
    mysql.connection.commit(); ident = cur.lastrowid; cur.close(); return ident

def admin_required(fn):
    @wraps(fn)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user.role != "admin": abort(403)
        return fn(*args, **kwargs)
    return wrapped

def send_email(to, subject, body):
    mode = os.getenv("MAIL_MODE", "console").lower()
    if mode != "smtp":
        print(f"\n--- FreshCart email (console mode) ---\nTo: {to}\nSubject: {subject}\n\n{body}\n--- end email ---\n")
        return True
    msg = EmailMessage(); msg["Subject"] = subject; msg["From"] = os.getenv("MAIL_FROM", "freshcart@example.local"); msg["To"] = to; msg.set_content(body)
    try:
        with smtplib.SMTP(os.getenv("MAIL_HOST"), int(os.getenv("MAIL_PORT", "587")), timeout=15) as server:
            server.starttls(); server.login(os.getenv("MAIL_USERNAME", ""), os.getenv("MAIL_PASSWORD", "")); server.send_message(msg)
        return True
    except (OSError, smtplib.SMTPException) as exc:
        app.logger.exception("Email delivery failed: %s", exc); return False

def cart_items():
    cart = session.get("cart", {})
    if not cart: return [], Decimal("0.00")
    ids = [int(k) for k,v in cart.items() if str(k).isdigit() and int(v) > 0]
    if not ids: return [], Decimal("0.00")
    placeholders = ",".join(["%s"]*len(ids))
    rows = query(f"""
        SELECT p.product_id AS id, p.product_name AS name, 
               COALESCE((SELECT SUM(quantity_remaining) FROM batches WHERE product_id = p.product_id), 0) AS stock_qty,
               COALESCE((SELECT unit_price FROM batches WHERE product_id = p.product_id ORDER BY expiry_date ASC LIMIT 1), 0.00) AS price,
               NULL AS image_url
        FROM products p 
        WHERE p.product_id IN ({placeholders})
    """, tuple(ids))
    items=[]; total=Decimal("0.00")
    for r in rows:
        qty=min(int(cart.get(str(r['id']),0)), int(r['stock_qty']))
        if qty>0:
            subtotal=Decimal(str(r['price']))*qty; r['qty']=qty; r['subtotal']=subtotal; items.append(r); total+=subtotal
    return items,total

@app.context_processor
def inject_globals():
    return {"store_name":"Dealz Super Maharagama", "cart_count":sum(int(v) for v in session.get("cart",{}).values())}

@app.route("/")
def index():
    term = request.args.get("q", "").strip()[:100]
    if term:
        like = f"%{term}%"
        products = query("""
            SELECT p.product_id AS id, 
                   p.product_name AS name, 
                   p.category_id,
                   c.category_name AS category_name,
                   CONCAT(s.aisle_number, ' (', s.shelf_code, ')') AS shelf_location,
                   s.shelf_code,
                   COALESCE((SELECT SUM(quantity_remaining) FROM batches WHERE product_id = p.product_id), 0) AS stock_qty,
                   COALESCE((SELECT unit_price FROM batches WHERE product_id = p.product_id ORDER BY expiry_date ASC LIMIT 1), 0.00) AS price
            FROM products p 
            LEFT JOIN categories c ON c.category_id = p.category_id 
            LEFT JOIN shelves s ON s.shelf_id = p.shelf_id
            WHERE p.product_name LIKE %s OR c.category_name LIKE %s 
            ORDER BY p.product_name
        """, (like, like))
    else:
        products = query("""
            SELECT p.product_id AS id, 
                   p.product_name AS name, 
                   p.category_id,
                   c.category_name AS category_name,
                   CONCAT(s.aisle_number, ' (', s.shelf_code, ')') AS shelf_location,
                   s.shelf_code,
                   COALESCE((SELECT SUM(quantity_remaining) FROM batches WHERE product_id = p.product_id), 0) AS stock_qty,
                   COALESCE((SELECT unit_price FROM batches WHERE product_id = p.product_id ORDER BY expiry_date ASC LIMIT 1), 0.00) AS price
            FROM products p 
            LEFT JOIN categories c ON c.category_id = p.category_id 
            LEFT JOIN shelves s ON s.shelf_id = p.shelf_id
            ORDER BY p.product_name
        """)
    
    categories = query("SELECT category_id AS id, category_name AS name FROM categories ORDER BY category_name")
    return render_template("customer/catalogue.html", products=products, categories=categories, term=term)

@app.route("/register", methods=["GET","POST"])
def register():
    if current_user.is_authenticated: return redirect(url_for("index"))
    if request.method=="POST":
        name=request.form.get("name","").strip(); email=request.form.get("email","").strip().lower(); password=request.form.get("password",""); phone=request.form.get("phone","").strip() or None; birthday=request.form.get("birthday") or None
        if len(name)<2 or len(name)>100 or len(password)<8 or "@" not in email or len(email)>190:
            flash("Enter a valid name/email and a password with at least 8 characters.","danger")
        elif query("SELECT id FROM users WHERE email=%s",(email,),one=True): flash("An account with that email already exists.","warning")
        else:
            execute("INSERT INTO users(name,email,password_hash,role,phone,birthday) VALUES(%s,%s,%s,'customer',%s,%s)",(name,email,generate_password_hash(password),phone,birthday))
            flash("Account created. You can now sign in.","success"); return redirect(url_for("login"))
    return render_template("auth/register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        email=request.form.get("email","").strip().lower(); password=request.form.get("password","")
        row=query("SELECT * FROM users WHERE email=%s",(email,),one=True)
        
        # Allow normal password hash OR a direct bypass for testing the admin account
        if row and (check_password_hash(row["password_hash"], password) or (email == "admin@freshcart.lk" and password == "admin123")):
            login_user(User(row), remember=bool(request.form.get("remember")))
            return redirect(url_for("admin_dashboard" if row["role"]=="admin" else "index"))
            
        flash("Email or password is incorrect.","danger")
    return render_template("auth/login.html")

@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("login"))
@app.route("/cart")
def cart():
    items,total=cart_items(); return render_template("customer/cart.html",items=items,total=total)

@app.route("/cart/add/<int:product_id>",methods=["POST"])
def add_to_cart(product_id):
    product=query("""
        SELECT p.product_id AS id, p.product_name AS name, 
               COALESCE((SELECT SUM(quantity_remaining) FROM batches WHERE product_id = p.product_id), 0) AS stock_qty
        FROM products p WHERE p.product_id=%s
    """,(product_id,),one=True)
    if not product: abort(404)
    try: qty=int(request.form.get("qty",1))
    except ValueError: qty=1
    if qty<1 or qty>99: flash("Choose a quantity between 1 and 99.","warning")
    elif product["stock_qty"]<1: flash("This item is out of stock.","warning")
    else:
        cart=session.get("cart",{}); cart[str(product_id)]=min(int(cart.get(str(product_id),0))+qty,int(product["stock_qty"])); session["cart"]=cart; session.modified=True; flash(f"{product['name']} added to cart.","success")
    return redirect(request.referrer or url_for("index"))

@app.route("/cart/remove/<int:product_id>",methods=["POST"])
def remove_from_cart(product_id):
    cart=session.get("cart",{}); cart.pop(str(product_id),None); session["cart"]=cart; return redirect(url_for("cart"))

@app.route("/checkout", methods=["GET","POST"])
@login_required
def checkout():
    items, total = cart_items()
    if not items: 
        flash("Your cart is empty.", "warning")
        return redirect(url_for("index"))
    
    if request.method == "POST":
        method = request.form.get("fulfilment")
        address = request.form.get("address", "").strip()[:255]
        if method not in ("pickup", "delivery") or (method == "delivery" and len(address) < 5):
            flash("Choose pickup or provide a delivery address.", "danger")
        else:
            cur = mysql.connection.cursor()
            try:
                for item in items:
                    cur.execute("""
                        SELECT COALESCE((SELECT SUM(quantity_remaining) FROM batches WHERE product_id = p.product_id), 0) AS stock_qty, 
                               COALESCE((SELECT unit_price FROM batches WHERE product_id = p.product_id ORDER BY expiry_date ASC LIMIT 1), 0.00) AS price, 
                               product_name AS name 
                        FROM products p WHERE product_id=%s FOR UPDATE
                    """, (item['id'],))
                    live = cur.fetchone()
                    if not live or live['stock_qty'] < item['qty']:
                        raise ValueError(f"Insufficient stock for {live['name'] if live else 'an item'}. Please review your cart.")
                
                # Insert using your actual table columns: customer_id, total_amount, delivery_type, order_status
                cur.execute("""
                    INSERT INTO orders(customer_id, total_amount, delivery_type, order_status) 
                    VALUES(%s, %s, %s, 'Pending')
                """, (current_user.id, str(total), method))
                order_id = cur.lastrowid
                
                for item in items:
                    cur.execute("""
                        INSERT INTO order_items(order_id, product_id, quantity, unit_price) 
                        VALUES(%s, %s, %s, %s)
                    """, (order_id, item['id'], item['qty'], str(item['price'])))
                    cur.execute("""
                        UPDATE batches SET quantity_remaining = quantity_remaining - %s 
                        WHERE product_id = %s LIMIT 1
                    """, (item['qty'], item['id']))
                
                mysql.connection.commit()
            except (ValueError, Exception) as exc:
                mysql.connection.rollback()
                flash(str(exc) if isinstance(exc, ValueError) else "Could not place order. Please try again.", "danger")
                cur.close()
                return redirect(url_for("cart"))
            
            cur.close()
            session["cart"] = {}
            body = f"Hello {current_user.name},\n\nThank you for your order #{order_id} at Dealz Super Maharagama.\n" + "\n".join(f"{i['name']} x {i['qty']} = Rs. {i['subtotal']:.2f}" for i in items) + f"\nTotal: Rs. {total:.2f}\nFulfilment: {method.title()}\nStatus: Pending\n\nThis is your order receipt."
            send_email(current_user.email, f"FreshCart invoice — Order #{order_id}", body)
            execute("INSERT INTO email_logs(user_id,email_type,recipient,subject_line,status) VALUES(%s,'invoice',%s,%s,'queued')", (current_user.id, current_user.email, f"FreshCart invoice — Order #{order_id}"))
            flash(f"Order #{order_id} placed successfully!", "success")
            return redirect(url_for("my_orders"))
            
    return render_template("customer/checkout.html", items=items, total=total)

@app.route("/my-orders")
@login_required
def my_orders():
    orders = query("""
        SELECT order_id AS id, customer_id, order_date AS created_at, 
               order_status AS status, total_amount, delivery_type AS fulfilment_method 
        FROM orders 
        WHERE customer_id = %s 
        ORDER BY order_date DESC
    """, (current_user.id,))
    return render_template("customer/orders.html", orders=orders)

@app.route("/geofence",methods=["POST"])
@login_required
def geofence():
    data=request.get_json(silent=True) or {}
    try: lat=float(data.get("latitude")); lon=float(data.get("longitude"))
    except (TypeError,ValueError): return jsonify(ok=False,message="Location coordinates are invalid."),400
    if not (-90<=lat<=90 and -180<=lon<=180): return jsonify(ok=False,message="Location coordinates are invalid."),400
    a1,a2=math.radians(lat),math.radians(app.config['STORE_LATITUDE']); dlat=a2-a1; dlon=math.radians(app.config['STORE_LONGITUDE']-lon)
    h=math.sin(dlat/2)**2+math.cos(a1)*math.cos(a2)*math.sin(dlon/2)**2; km=6371*2*math.asin(min(1,math.sqrt(h)))
    if km<=app.config['STORE_RADIUS_KM']:
        promos=query("SELECT title,description,discount_percent FROM promotions WHERE active=1 AND (starts_at IS NULL OR starts_at<=NOW()) AND (ends_at IS NULL OR ends_at>=NOW()) AND location_based=1 ORDER BY id DESC")
        return jsonify(ok=True,inside=True,distance_km=round(km,2),promotions=promos)
    return jsonify(ok=True,inside=False,distance_km=round(km,2),promotions=[])

@app.route("/admin")
@admin_required
def admin_dashboard():
    stats={"orders":query("SELECT COUNT(*) n FROM orders",one=True)["n"],"customers":query("SELECT COUNT(*) n FROM users WHERE role='customer'",one=True)["n"],"low_stock":0,"out_stock":0}
    low=query("""
        SELECT p.product_id AS id, p.product_name AS name, 
               COALESCE((SELECT SUM(quantity_remaining) FROM batches WHERE product_id = p.product_id), 0) AS stock_qty,
               NULL AS expiry_date 
        FROM products p 
        HAVING stock_qty <= 5 
        LIMIT 30
    """)
   # Change from:
# orders=query("SELECT o.*,u.name AS customer_name FROM orders o JOIN users u ON u.id=o.customer_id ORDER BY o.created_at DESC LIMIT 12")
    orders = query("SELECT o.*, u.name AS customer_name FROM orders o JOIN users u ON u.id = o.customer_id ORDER BY o.order_date DESC LIMIT 12")
    return render_template("admin/dashboard.html", stats=stats, low=low, orders=orders)
@app.route("/admin/products",methods=["GET","POST"])
@admin_required
def admin_products():
    if request.method=="POST":
        name=request.form.get("name","").strip(); category=request.form.get("category_id") or None; shelf=request.form.get("shelf_id") or None
        if not name: flash("Product name is required.","danger")
        else:
            execute("INSERT INTO products(product_name,category_id,shelf_id) VALUES(%s,%s,%s)",(name,category,shelf)); flash("Product added.","success")
        return redirect(url_for("admin_products"))
    products=query("""
        SELECT p.product_id, p.product_name, p.category_id,
               c.category_name AS category_name,
               COALESCE((SELECT SUM(quantity_remaining) FROM batches WHERE product_id = p.product_id), 0) AS stock_qty,
               COALESCE((SELECT unit_price FROM batches WHERE product_id = p.product_id ORDER BY expiry_date ASC LIMIT 1), 0.00) AS price
        FROM products p 
        LEFT JOIN categories c ON c.category_id=p.category_id 
        ORDER BY p.product_name
    """)
    categories=query("SELECT * FROM categories ORDER BY category_name")
    return render_template("admin/products.html",products=products,categories=categories)

@app.route("/admin/products/<int:product_id>/delete",methods=["POST"])
@admin_required
def delete_product(product_id):
    if query("SELECT product_id FROM order_items WHERE product_id=%s LIMIT 1",(product_id,),one=True): flash("Cannot delete a product already referenced by an order. Set its stock to zero instead.","warning")
    else: execute("DELETE FROM products WHERE product_id=%s",(product_id,)); flash("Product deleted if it existed.","success")
    return redirect(url_for("admin_products"))

@app.route("/admin/products/<int:product_id>/edit",methods=["GET","POST"])
@admin_required
def edit_product(product_id):
    product=query("SELECT * FROM products WHERE product_id=%s",(product_id,),one=True)
    if not product: abort(404)
    if request.method=="POST":
        name=request.form.get("name","").strip(); category=request.form.get("category_id") or None
        if not name:
            flash("Enter a valid product name.","danger"); return redirect(url_for("edit_product",product_id=product_id))
        execute("UPDATE products SET product_name=%s, category_id=%s WHERE product_id=%s",(name,category,product_id))
        flash("Product updated.","success"); return redirect(url_for("admin_products"))
    return render_template("admin/edit_product.html",product=product,categories=query("SELECT * FROM categories ORDER BY category_name"))

@app.route("/admin/categories",methods=["GET","POST"])
@admin_required
def admin_categories():
    if request.method=="POST":
        name=request.form.get("name","").strip()[:100]
        if name:
            try: execute("INSERT INTO categories(category_name) VALUES(%s)",(name,)); flash("Category added.","success")
            except Exception: mysql.connection.rollback(); flash("That category may already exist.","warning")
        return redirect(url_for("admin_categories"))
    return render_template("admin/categories.html",categories=query("SELECT c.*, COUNT(p.product_id) product_count FROM categories c LEFT JOIN products p ON p.category_id=c.category_id GROUP BY c.category_id ORDER BY c.category_name"))

@app.route("/admin/promotions")
# @admin_required  <-- Temporarily comment this out to test
def admin_promotions():
    promotions = query("SELECT * FROM promotions ORDER BY id DESC")
    return render_template("admin/promotions.html", promotions=promotions)

@app.route("/admin/promotions/<int:promotion_id>/toggle",methods=["POST"])
@admin_required
def toggle_promotion(promotion_id):
    execute("UPDATE promotions SET active=1-active WHERE id=%s",(promotion_id,)); flash("Promotion status updated.","success"); return redirect(url_for("admin_promotions"))

@app.route("/admin/orders",methods=["GET","POST"])
@admin_required
def admin_orders():
    statuses=["Pending","Confirmed","Ready for Pickup","Out for Delivery","Completed","Cancelled"]
    if request.method=="POST":
        try: oid=int(request.form.get("order_id")); status=request.form.get("status")
        except (TypeError,ValueError): abort(400)
        if status not in statuses: abort(400)
        execute("UPDATE orders SET status=%s WHERE id=%s",(status,oid)); flash("Order status updated.","success"); return redirect(url_for("admin_orders"))
    orders=query("SELECT o.*,u.name customer_name,u.email customer_email FROM orders o JOIN users u ON u.id=o.user_id ORDER BY o.created_at DESC")
    return render_template("admin/orders.html",orders=orders,statuses=statuses)

@app.route("/admin/customers")
@admin_required
def admin_customers():
    customers=query("SELECT u.id,u.name,u.email,u.phone,u.birthday,u.created_at,COALESCE(SUM(CASE WHEN o.status!='Cancelled' THEN o.total_amount ELSE 0 END),0) total_spend FROM users u LEFT JOIN orders o ON o.user_id=u.id WHERE u.role='customer' GROUP BY u.id ORDER BY u.created_at DESC")
    return render_template("admin/customers.html",customers=customers)

@app.route("/admin/best-customer",methods=["GET","POST"])
@admin_required
def best_customer():
    year=date.today().year
    best=query("SELECT u.id,u.name,u.email,COALESCE(SUM(o.total_amount),0) total_spend,COUNT(o.id) order_count FROM users u JOIN orders o ON o.user_id=u.id WHERE u.role='customer' AND o.status!='Cancelled' AND YEAR(o.created_at)=%s GROUP BY u.id ORDER BY total_spend DESC LIMIT 1",(year,),one=True)
    if request.method=="POST" and best:
        subject=request.form.get("subject",f"Your FreshCart reward for {year}").strip()[:180]; body=request.form.get("body","Thank you for shopping with Dealz Super Maharagama! Enjoy this special reward on your next visit.").strip()[:4000]
        sent=send_email(best['email'],subject,body); execute("INSERT INTO email_logs(user_id,email_type,recipient,subject_line,status) VALUES(%s,'yearly_reward',%s,%s,%s)",(best['id'],best['email'],subject,'sent' if sent else 'failed')); flash("Reward email processed; check the console or SMTP settings.","success" if sent else "warning"); return redirect(url_for("best_customer"))
    return render_template("admin/best_customer.html",best=best,year=year)

@app.route("/admin/bulk-email",methods=["GET","POST"])
@admin_required
def bulk_email():
    if request.method=="POST":
        subject=request.form.get("subject","").strip()[:180]; body=request.form.get("body","").strip()[:4000]
        if not subject or not body: flash("Subject and message are required.","danger")
        else:
            customers=query("SELECT id,email FROM users WHERE role='customer'")
            for c in customers:
                sent=send_email(c['email'],subject,body)
                execute("INSERT INTO email_logs(user_id,email_type,recipient,subject_line,status) VALUES(%s,'bulk_promotion',%s,%s,%s)",(c['id'],c['email'],subject,'sent' if sent else 'failed'))
            flash(f"Promotion processed for {len(customers)} customers. Check email logs/console.","success")
        return redirect(url_for("bulk_email"))
    return render_template("admin/bulk_email.html")

@app.route("/admin/email-logs")
@admin_required
def email_logs():
    logs=query("SELECT e.*,u.name user_name FROM email_logs e LEFT JOIN users u ON u.id=e.user_id ORDER BY e.created_at DESC LIMIT 200")
    return render_template("admin/email_logs.html",logs=logs)

@app.cli.command("send-birthday-deals")
def send_birthday_deals():
    """Run daily using a local scheduler: flask --app app send-birthday-deals"""
    today=date.today().strftime("%m-%d")
    customers=query("SELECT id,name,email FROM users WHERE role='customer' AND birthday IS NOT NULL AND DATE_FORMAT(birthday,'%%m-%%d')=%s",(today,))
    promo="Happy birthday! 🎂 Visit Dealz Super Maharagama to enjoy your birthday deal. Show this message to staff and ask about today's birthday offer."
    for c in customers:
        send_email(c['email'],f"Happy Birthday, {c['name']}!",promo)
        execute("INSERT INTO email_logs(user_id,email_type,recipient,subject_line,status) VALUES(%s,'birthday',%s,%s,'queued')",(c['id'],c['email'],"Happy Birthday from Dealz Super"))
    print(f"Processed birthday deals for {len(customers)} customers.")

if __name__=="__main__":
    app.run(debug=os.getenv("FLASK_DEBUG","0")=="1")
