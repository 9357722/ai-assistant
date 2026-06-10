/**
 * 公共工具函数
 */
const API_BASE = '';

// XSS 防护：转义 HTML 特殊字符
function escapeHTML(str) {
    if (str == null) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function safeImageUrl(url, fallback = '/static/products/product_1.jpg') {
    if (!url) return fallback;
    const value = String(url).trim();
    if (value.startsWith('/static/products/')) return value;
    if (value.startsWith('https://images.unsplash.com/')) return value;
    return fallback;
}

// 统一 Toast 提示
function showToast(message, type = 'success') {
    let toast = document.getElementById('toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toast';
        toast.className = 'toast';
        toast.style.cssText = 'position:fixed;top:80px;right:20px;padding:1rem 1.5rem;border-radius:8px;color:white;z-index:9999;transform:translateX(120%);transition:transform 0.3s;font-size:14px;';
        document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.style.background = type === 'error' ? '#ff3b30' : '#34c759';
    toast.classList.add('show');
    toast.style.transform = 'translateX(0)';
    setTimeout(() => { toast.style.transform = 'translateX(120%)'; }, 3000);
}

// 检查登录状态
function getToken() {
    return localStorage.getItem('token');
}

function getAuthHeaders() {
    const token = getToken();
    return token ? { 'Authorization': `Bearer ${token}` } : {};
}

function isLoggedIn() {
    return !!getToken() && !!localStorage.getItem('username');
}

// ============ 移动端底部 Tab 栏 ============
function injectMobileTabBar() {
    const currentPath = window.location.pathname;
    const tabs = [
        { href: '/', icon: 'H', label: '首页', match: '/' },
        { href: '/product.html', icon: 'S', label: '商品', match: '/product.html' },
        { href: '/cart.html', icon: 'C', label: '购物车', match: '/cart.html' },
        { href: '/orders.html', icon: 'O', label: '订单', match: '/orders.html' },
        { href: '/user.html', icon: 'U', label: '我的', match: '/user.html' },
    ];

    const css = document.createElement('style');
    css.textContent = `
        .mobile-tab-bar {
            display: none;
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: rgba(255,255,255,0.95);
            backdrop-filter: blur(20px);
            border-top: 1px solid rgba(0,0,0,0.08);
            z-index: 900;
            padding: 6px 0 env(safe-area-inset-bottom, 6px);
        }
        .mobile-tab-bar .tab-list {
            display: flex;
            justify-content: space-around;
            list-style: none;
            margin: 0;
            padding: 0;
        }
        .mobile-tab-bar .tab-item {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 2px;
            text-decoration: none;
            color: #86868b;
            font-size: 10px;
            padding: 4px 8px;
            transition: color 0.2s;
        }
        .mobile-tab-bar .tab-item.active { color: #6366f1; }
        .mobile-tab-bar .tab-item .tab-icon { font-size: 20px; }
        @media (max-width: 768px) {
            .mobile-tab-bar { display: block; }
            body { padding-bottom: 64px; }
        }
    `;
    document.head.appendChild(css);

    const bar = document.createElement('nav');
    bar.className = 'mobile-tab-bar';
    bar.innerHTML = `<div class="tab-list">${tabs.map(t => {
        const isActive = currentPath === t.match || (t.match === '/' && currentPath === '/');
        return `<a href="${t.href}" class="tab-item ${isActive ? 'active' : ''}">
            <span class="tab-icon">${t.icon}</span><span>${t.label}</span></a>`;
    }).join('')}</div>`;
    document.body.appendChild(bar);
}

// ============ 回到顶部按钮 ============
function injectBackToTop() {
    const css = document.createElement('style');
    css.textContent = `
        .back-to-top {
            position: fixed;
            bottom: 88px;
            right: 24px;
            width: 44px;
            height: 44px;
            background: rgba(255,255,255,0.9);
            border: 1px solid rgba(0,0,0,0.08);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            font-size: 20px;
            z-index: 800;
            opacity: 0;
            transform: translateY(20px);
            transition: all 0.3s;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        }
        .back-to-top.show { opacity: 1; transform: translateY(0); }
        .back-to-top:hover { background: white; box-shadow: 0 4px 16px rgba(0,0,0,0.12); }
        @media (max-width: 768px) { .back-to-top { bottom: 76px; right: 16px; } }
    `;
    document.head.appendChild(css);

    const btn = document.createElement('div');
    btn.className = 'back-to-top';
    btn.textContent = '↑';
    btn.onclick = () => window.scrollTo({ top: 0, behavior: 'smooth' });
    document.body.appendChild(btn);

    window.addEventListener('scroll', () => {
        btn.classList.toggle('show', window.scrollY > 300);
    });
}

// 自动注入
document.addEventListener('DOMContentLoaded', () => {
    injectMobileTabBar();
    injectBackToTop();
});
