-- Migration: 添加 returned 和 refunded 订单状态
-- 执行前检查现有数据，确保不会破坏约束

-- 更新订单状态枚举，添加 returned 和 refunded
ALTER TABLE orders
    MODIFY status ENUM('pending', 'paid', 'shipped', 'completed', 'cancelled', 'refunded', 'returned') DEFAULT 'pending';

-- 更新订单项状态枚举（如果有）
ALTER TABLE order_items
    ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active';
