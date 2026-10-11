# FreshCart — Dealz Super Maharagama

A local Flask + MySQL supermarket management prototype for a university DBMS project. Includes customer catalogue/cart/checkout, order invoices (console or SMTP), role-protected admin pages, stock and expiry visibility, promotions, customer reporting, best customer reward, email logs, birthday job, and browser-based 2 km geofence promotions.

## Requirements
- Python 3.10+
- MySQL Server 8.0+ running locally
- Windows PowerShell or terminal

## 1. Create a virtual environment
```powershell
cd freshcart
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```
If `mysqlclient` fails to install on Windows, install the matching MySQL/MariaDB development build tools or use a Python version for which a wheel is available. The application uses Flask-MySQLdb/mysqlclient.

## 2. Create database and local database user
Open MySQL Workbench and run:
```sql
CREATE DATABASE freshcart CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'freshcart_user'@'localhost' IDENTIFIED BY 'change_me';
GRANT ALL PRIVILEGES ON freshcart.* TO 'freshcart_user'@'localhost';
FLUSH PRIVILEGES;
```
Then import `database/schema.sql` in Workbench (or run `mysql -u root -p < database/schema.sql`). The SQL contains categories, sample products, promotions, store settings and geofence seed data.

## 3. Configure environment
Copy `.env.example` to `.env`. Set `SECRET_KEY` to a long random value and update the MySQL credentials. The supplied store coordinates are approximate demo coordinates for Maharagama; confirm them against the real store before using geofencing in a presentation or deployment.

Email defaults to `MAIL_MODE=console`, so invoices and promotions are printed in the Flask terminal for offline testing. For SMTP testing, set `MAIL_MODE=smtp` and fill in Mailtrap SMTP host, port, username, password and sender. SMTP requires internet access to the test mail service, so console mode is the fully offline option.

## 4. Create demo login accounts
```powershell
flask --app app seed-demo
```
Demo accounts (change these passwords before any real use):
- Admin: `admin@freshcart.local` / `Admin123!`
- Customer: `customer@freshcart.local` / `Customer123!`

Passwords are stored only as Werkzeug password hashes. The SQL seed deliberately does not insert default account passwords.

## 5. Run
```powershell
flask --app app run --debug
```
Open http://127.0.0.1:5000. Customer registration is available. Admin pages require the seeded admin account. Do not expose Flask's development server to a public network.

## Features and routes
- `/` catalogue, search, stock and shelf locations
- `/register`, `/login`, `/logout`
- `/cart`, `/checkout`, `/my-orders`
- `/admin` dashboard; `/admin/products`, `/admin/categories`, `/admin/promotions`, `/admin/orders`, `/admin/customers`, `/admin/best-customer`, `/admin/bulk-email`, `/admin/email-logs`
- Geofence prompt uses browser geolocation and sends coordinates only after the signed-in customer clicks the button. Browsers generally allow geolocation on `localhost`.
- Birthday campaign job: run `flask --app app send-birthday-deals` daily using Windows Task Scheduler. It sends a generic birthday offer to matching registered customers.

## Security notes / project scope
- Forms use Flask-WTF's global CSRF protection; SQL statements use parameter placeholders; passwords use `generate_password_hash` and `check_password_hash`; admin routes use `@admin_required` on top of Flask-Login.
- Cart quantities and stock are rechecked in a transaction at checkout. Never trust prices or totals from the browser.
- The demo uses remote Unsplash image URLs for convenient catalogue thumbnails; replace with local images for a strictly offline visual demo. All application logic and database services run locally.
- This is a teaching prototype, not a security-audited production system. Before production, add rate limiting, password reset and email verification, secure HTTPS cookies, audit logs, migration management, stricter validation, backup/restore, SMTP retry handling, and comprehensive automated tests. Add a separate stock-batch table if multiple expiry dates per product must be tracked accurately.
- Owner/admin can view inventory, low/out-of-stock and near-expiry items, create products/categories/promotions, update order status, view customers and email logs, calculate the top spender for the current year, and send the selected reward or bulk promotions.
