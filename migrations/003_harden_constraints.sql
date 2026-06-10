-- Migration: harden numeric constraints and keep order statuses consistent.
-- Run after checking existing data for negative price/stock/sales/quantity values.

ALTER TABLE products
    ADD CONSTRAINT chk_products_price_positive CHECK (price > 0),
    ADD CONSTRAINT chk_products_stock_non_negative CHECK (stock >= 0),
    ADD CONSTRAINT chk_products_sales_non_negative CHECK (sales >= 0);

ALTER TABLE cart_items
    ADD CONSTRAINT chk_cart_items_quantity_positive CHECK (quantity > 0);

ALTER TABLE orders
    MODIFY status ENUM('pending', 'paid', 'shipped', 'completed', 'cancelled') DEFAULT 'pending',
    ADD CONSTRAINT chk_orders_total_amount_non_negative CHECK (total_amount >= 0),
    ADD CONSTRAINT chk_orders_pay_amount_non_negative CHECK (pay_amount IS NULL OR pay_amount >= 0);

ALTER TABLE order_items
    ADD CONSTRAINT chk_order_items_price_positive CHECK (price > 0),
    ADD CONSTRAINT chk_order_items_quantity_positive CHECK (quantity > 0);
