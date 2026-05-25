ALTER DATABASE product_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
SET NAMES utf8mb4;

-- 建表：商品信息
CREATE TABLE IF NOT EXISTS products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    price DECIMAL(10,2),
    platform VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 建表：行情资讯
CREATE TABLE IF NOT EXISTS market_news (
    id INT AUTO_INCREMENT PRIMARY KEY,
    keyword VARCHAR(100),
    content TEXT
);

-- 插入初始数据
INSERT INTO products (name, price, platform) VALUES
('蓝牙耳机 Pro', 159.00, '京东'),
('蓝牙耳机 Lite', 59.90, '拼多多'),
('iPhone 17 Pro', 7999.00, '京东'),
('iPhone 17 Pro', 7899.00, '淘宝'),
('华为Mate 70 Pro', 6999.00, '京东'),
('华为Mate 70 Pro', 6899.00, '拼多多'),
('红米K80', 2499.00, '淘宝'),
('小米14', 3999.00, '京东'),
('小米14', 3899.00, '淘宝');

INSERT INTO market_news (keyword, content) VALUES
('手机行情', '2026年5月：华为Mate 70 Pro均价6999元，iPhone 17 Pro均价7999元，红米K80均价2499元。');