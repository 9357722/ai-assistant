-- WARNING: 默认管理员账户密码为 admin123，首次登录后请立即修改！
-- 本文件已合并 migrations/001-004，新建数据库只需执行此文件即可
ALTER DATABASE product_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
SET NAMES utf8mb4;

-- 建表：商品信息
CREATE TABLE IF NOT EXISTS products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    price DECIMAL(10,2) NOT NULL CHECK (price > 0),
    platform VARCHAR(50),
    category_id INT,
    description TEXT,
    main_image VARCHAR(500),
    images JSON,
    stock INT DEFAULT 100 CHECK (stock >= 0),
    sales INT DEFAULT 0 CHECK (sales >= 0),
    rating DECIMAL(2,1) DEFAULT 5.0,
    status ENUM('on_sale', 'off_sale') DEFAULT 'on_sale',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_name (name),
    INDEX idx_platform (platform),
    INDEX idx_category (category_id),
    INDEX idx_status (status),
    INDEX idx_sales (sales),
    INDEX idx_price (price),
    INDEX idx_platform_status (platform, status),
    FULLTEXT INDEX idx_name_fulltext (name) WITH PARSER ngram
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 建表：行情资讯
CREATE TABLE IF NOT EXISTS market_news (
    id INT AUTO_INCREMENT PRIMARY KEY,
    keyword VARCHAR(100),
    content TEXT
);

-- 插入初始数据
INSERT INTO products (name, price, platform, category_id, main_image, stock, sales, rating) VALUES
('蓝牙耳机 Pro', 159.00, '京东', 2, '/static/products/蓝牙耳机_Pro.jpg', 200, 85, 4.8),
('蓝牙耳机 Lite', 59.90, '拼多多', 2, '/static/products/蓝牙耳机_Lite.jpg', 500, 320, 4.5),
('iPhone 17 Pro', 7999.00, '京东', 1, '/static/products/iPhone_17_Pro.jpg', 50, 12, 4.9),
('iPhone 17 Pro', 7899.00, '淘宝', 1, '/static/products/iPhone_17_Pro.jpg', 80, 25, 4.9),
('华为Mate 70 Pro', 6999.00, '京东', 1, '/static/products/华为Mate_70_Pro.jpg', 60, 18, 4.8),
('华为Mate 70 Pro', 6899.00, '拼多多', 1, '/static/products/华为Mate_70_Pro.jpg', 100, 30, 4.8),
('红米K80', 2499.00, '淘宝', 1, '/static/products/红米K80.jpg', 150, 95, 4.6),
('小米14', 3999.00, '京东', 1, '/static/products/小米14.jpg', 120, 67, 4.7),
('小米14', 3899.00, '淘宝', 1, '/static/products/小米14.jpg', 90, 43, 4.7);

INSERT INTO market_news (keyword, content) VALUES
('手机行情', '2026年5月：华为Mate 70 Pro均价6999元，iPhone 17 Pro均价7999元，红米K80均价2499元。');

-- ============ 电商模块：用户系统 ============

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    avatar VARCHAR(500),
    role ENUM('user', 'admin', 'merchant') DEFAULT 'user',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 用户地址表
CREATE TABLE IF NOT EXISTS user_addresses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(50) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    province VARCHAR(50),
    city VARCHAR(50),
    district VARCHAR(50),
    detail VARCHAR(200),
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 商品分类表
CREATE TABLE IF NOT EXISTS categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    parent_id INT,
    icon VARCHAR(200),
    sort_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES categories(id)
);

-- 购物车表
CREATE TABLE IF NOT EXISTS cart_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT DEFAULT 1 CHECK (quantity > 0),
    selected BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    UNIQUE KEY uk_user_product (user_id, product_id)
);

-- 订单表
CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_no VARCHAR(32) UNIQUE NOT NULL,
    user_id INT NOT NULL,
    total_amount DECIMAL(10,2) NOT NULL CHECK (total_amount >= 0),
    pay_amount DECIMAL(10,2) CHECK (pay_amount >= 0),
    status ENUM('pending', 'paid', 'shipped', 'completed', 'cancelled', 'refunded', 'returned') DEFAULT 'pending',
    address_snapshot JSON,
    remark VARCHAR(500),
    idempotency_key VARCHAR(64),
    paid_at TIMESTAMP NULL,
    shipped_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    tracking_no VARCHAR(50),
    carrier VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_user_status (user_id, status),
    INDEX idx_user_status_created (user_id, status, created_at DESC),
    INDEX idx_created (created_at),
    UNIQUE INDEX idx_idempotency (idempotency_key, user_id)
);

-- 订单项表
CREATE TABLE IF NOT EXISTS order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    product_name VARCHAR(100),
    product_image VARCHAR(500),
    price DECIMAL(10,2) NOT NULL CHECK (price > 0),
    quantity INT NOT NULL CHECK (quantity > 0),
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- 商品评价表
CREATE TABLE IF NOT EXISTS product_reviews (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    user_id INT NOT NULL,
    rating INT CHECK (rating >= 1 AND rating <= 5),
    content TEXT,
    images JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_product_rating (product_id, rating)
);

-- 插入默认管理员账户（首次登录后请立即修改密码）
INSERT INTO users (username, email, hashed_password, role) VALUES
('admin', 'admin@example.com', '$2b$12$LJ3m4ys3Lk0TSwHjnF4oR.K3VJxqfVYqxSy3TqFG3YfP0z3bGHXBe', 'admin');

-- 插入商品分类
INSERT INTO categories (name, sort_order) VALUES
('手机', 1),
('耳机', 2),
('电脑', 3),
('平板', 4);

-- 外键约束（categories 在 products 之后创建，所以用 ALTER TABLE）
ALTER TABLE products ADD CONSTRAINT fk_product_category
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL;

-- ============ 商家模块（来自 migration 002） ============

-- 商家表
CREATE TABLE IF NOT EXISTS merchants (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNIQUE NOT NULL,
    shop_name VARCHAR(100) NOT NULL,
    shop_description TEXT,
    shop_logo VARCHAR(500),
    contact_phone VARCHAR(20),
    contact_email VARCHAR(100),
    address VARCHAR(200),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 商家商品表
CREATE TABLE IF NOT EXISTS merchant_products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    merchant_id INT NOT NULL,
    product_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (merchant_id) REFERENCES merchants(id),
    FOREIGN KEY (product_id) REFERENCES products(id),
    UNIQUE KEY uk_mp (merchant_id, product_id)
);

-- 优惠券表
CREATE TABLE IF NOT EXISTS coupons (
    id INT AUTO_INCREMENT PRIMARY KEY,
    merchant_id INT,
    name VARCHAR(100) NOT NULL,
    type ENUM('fixed', 'percent') NOT NULL,
    value DECIMAL(10,2) NOT NULL,
    min_amount DECIMAL(10,2) DEFAULT 0,
    max_uses INT DEFAULT 0,
    used_count INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    start_date DATE,
    end_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (merchant_id) REFERENCES merchants(id)
);

-- 用户优惠券表
CREATE TABLE IF NOT EXISTS user_coupons (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    coupon_id INT NOT NULL,
    is_used BOOLEAN DEFAULT FALSE,
    claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (coupon_id) REFERENCES coupons(id)
);

-- ============ 对话历史表（用于替代内存存储） ============

CREATE TABLE IF NOT EXISTS chat_history (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    role ENUM('user', 'assistant', 'system') NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_created (user_id, created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============ 记忆管理系统 ============

-- 用户画像表
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id INT PRIMARY KEY,
    nickname VARCHAR(100),
    gender ENUM('male', 'female', 'other'),
    age_group VARCHAR(20),
    favorite_colors JSON,
    favorite_categories JSON,
    price_range JSON,
    brand_preferences JSON,
    total_orders INT DEFAULT 0,
    last_order_date DATETIME,
    avg_order_value DECIMAL(10, 2),
    purchase_frequency VARCHAR(20),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 记忆日志表
CREATE TABLE IF NOT EXISTS memory_logs (
    log_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    memory_type ENUM('preference', 'behavior', 'context') NOT NULL,
    content TEXT NOT NULL,
    confidence DECIMAL(3, 2) DEFAULT 0.80,
    source VARCHAR(50) DEFAULT 'auto_extract',
    action ENUM('create', 'update', 'delete', 'merge') DEFAULT 'create',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_memory_type (memory_type),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 用户记忆向量表（存储用户长期记忆的向量）
CREATE TABLE IF NOT EXISTS user_memory_vectors (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    memory_text TEXT NOT NULL,
    memory_type VARCHAR(50) DEFAULT 'general',
    metadata JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_memory_type (memory_type),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

