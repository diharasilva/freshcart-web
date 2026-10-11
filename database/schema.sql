CREATE DATABASE IF NOT EXISTS freshcart CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE freshcart;
CREATE TABLE IF NOT EXISTS users (
 id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(100) NOT NULL, email VARCHAR(190) NOT NULL UNIQUE,
 password_hash VARCHAR(255) NOT NULL, role ENUM('customer','admin') NOT NULL DEFAULT 'customer', phone VARCHAR(30), birthday DATE,
 created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS categories (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(100) NOT NULL UNIQUE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS products (
 id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(150) NOT NULL, price DECIMAL(10,2) NOT NULL DEFAULT 0 CHECK(price>=0), stock_qty INT NOT NULL DEFAULT 0 CHECK(stock_qty>=0),
 shelf_location VARCHAR(50), aisle VARCHAR(100), expiry_date DATE, category_id INT, image_url VARCHAR(500), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE SET NULL, INDEX idx_products_name(name), INDEX idx_products_stock(stock_qty)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS orders (
 id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL, total_amount DECIMAL(12,2) NOT NULL, fulfilment_method ENUM('pickup','delivery') NOT NULL,
 delivery_address VARCHAR(255), status ENUM('Pending','Confirmed','Ready for Pickup','Out for Delivery','Completed','Cancelled') NOT NULL DEFAULT 'Pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(user_id) REFERENCES users(id), INDEX idx_orders_created(created_at), INDEX idx_orders_user(user_id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS order_items (
 id INT AUTO_INCREMENT PRIMARY KEY, order_id INT NOT NULL, product_id INT NOT NULL, quantity INT NOT NULL CHECK(quantity>0), unit_price DECIMAL(10,2) NOT NULL,
 FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE, FOREIGN KEY(product_id) REFERENCES products(id), INDEX idx_order_items_product(product_id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS promotions (
 id INT AUTO_INCREMENT PRIMARY KEY, title VARCHAR(150) NOT NULL, description TEXT, discount_percent DECIMAL(5,2), starts_at DATETIME, ends_at DATETIME,
 active BOOLEAN NOT NULL DEFAULT TRUE, location_based BOOLEAN NOT NULL DEFAULT FALSE, created_by INT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS email_logs (
 id INT AUTO_INCREMENT PRIMARY KEY, user_id INT, email_type VARCHAR(50) NOT NULL, recipient VARCHAR(190) NOT NULL, subject_line VARCHAR(255) NOT NULL,
 status ENUM('queued','sent','failed') NOT NULL DEFAULT 'queued', error_message VARCHAR(500), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL, INDEX idx_email_created(created_at)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS notifications (
 id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL, title VARCHAR(150) NOT NULL, message TEXT NOT NULL, read_at DATETIME, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS geofence (
 id INT AUTO_INCREMENT PRIMARY KEY, store_name VARCHAR(150) NOT NULL, address VARCHAR(255) NOT NULL, latitude DECIMAL(10,7) NOT NULL, longitude DECIMAL(10,7) NOT NULL, radius_km DECIMAL(5,2) NOT NULL DEFAULT 2.00
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS store_settings (
 setting_key VARCHAR(100) PRIMARY KEY, setting_value TEXT NOT NULL, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Demo account password hashes are created by seed.py, not stored as plaintext in this SQL file.
INSERT IGNORE INTO categories(id,name) VALUES (1,'Dairy & Refrigerated'),(2,'Beverages'),(3,'Biscuits & Snacks'),(4,'Rice & Grains'),(5,'Fresh Produce'),(6,'Household');
INSERT IGNORE INTO products(id,name,price,stock_qty,shelf_location,aisle,expiry_date,category_id,image_url) VALUES
(1,'Fresh Milk 1L',520.00,35,'A3-S1','Aisle 3 - Dairy & Refrigerated','2026-11-02',1,'https://images.unsplash.com/photo-1563636619-e9143da7973b?w=600'),
(2,'Ceylon Tea 200g',780.00,42,'A1-S2','Aisle 1 - Tea & Coffee','2027-06-30',2,'https://images.unsplash.com/photo-1597318181409-cf64d0b5d8a2?w=600'),
(3,'Chocolate Biscuits',350.00,4,'A2-S3','Aisle 2 - Biscuits & Snacks','2027-02-01',3,'https://images.unsplash.com/photo-1558961363-fa8fdf82db35?w=600'),
(4,'White Rice 5kg',1850.00,28,'A4-S1','Aisle 4 - Rice & Grains','2027-12-31',4,'https://images.unsplash.com/photo-1586201375761-83865001e31c?w=600'),
(5,'Bananas 1kg',420.00,18,'P1-S1','Produce - Fruit Rack','2026-10-20',5,'https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?w=600'),
(6,'Eggs 10 pack',780.00,0,'A3-S2','Aisle 3 - Dairy & Refrigerated','2026-10-25',1,'https://images.unsplash.com/photo-1506976785307-8732e854ad03?w=600'),
(7,'Bottled Water 1.5L',180.00,65,'A1-S4','Aisle 1 - Drinks','2028-01-01',2,'https://images.unsplash.com/photo-1523362628745-0c100150b504?w=600'),
(8,'Washing Powder 1kg',950.00,12,'A5-S2','Aisle 5 - Household','2028-01-01',6,'https://images.unsplash.com/photo-1585421514738-01798e348b17?w=600');
INSERT IGNORE INTO promotions(id,title,description,discount_percent,active,location_based) VALUES (1,'Near-store Fresh Deals','Ask in store about selected fresh produce offers.',10,1,1),(2,'Weekend Pantry Savings','Save on selected pantry essentials this weekend.',5,1,0);
INSERT IGNORE INTO geofence(id,store_name,address,latitude,longitude,radius_km) VALUES(1,'Dealz Super Maharagama','101 Pathiragoda Rd, Maharagama',6.8480000,79.9265000,2.00);
INSERT IGNORE INTO store_settings(setting_key,setting_value) VALUES ('store_name','Dealz Super Maharagama'),('store_address','101 Pathiragoda Rd, Maharagama'),('currency','LKR');
