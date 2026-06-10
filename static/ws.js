/**
 * WebSocket 实时通知客户端
 * 自动连接、重连、心跳保活
 */
const WSClient = (() => {
    let ws = null;
    let reconnectTimer = null;
    let heartbeatTimer = null;
    let listeners = {};
    const RECONNECT_INTERVAL = 3000;
    const HEARTBEAT_INTERVAL = 30000;

    function getToken() {
        return localStorage.getItem('token');
    }

    async function fetchTicket(token) {
        const res = await fetch('/api/ws-ticket', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) throw new Error('Failed to create WebSocket ticket');
        const data = await res.json();
        return data.ticket;
    }

    async function connect() {
        const token = getToken();
        if (!token) return;

        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';

        try {
            const ticket = await fetchTicket(token);
            const url = `${protocol}//${location.host}/ws/${encodeURIComponent(ticket)}`;
            ws = new WebSocket(url);
        } catch (e) {
            console.warn('WebSocket connection failed:', e);
            scheduleReconnect();
            return;
        }

        ws.onopen = () => {
            console.log('[WS] Connected');
            startHeartbeat();
            emit('connected');
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'pong') return;
                emit(data.type, data);
                emit('message', data);
            } catch (e) {
                console.warn('[WS] Parse error:', e);
            }
        };

        ws.onclose = () => {
            console.log('[WS] Disconnected');
            stopHeartbeat();
            emit('disconnected');
            scheduleReconnect();
        };

        ws.onerror = (err) => {
            console.warn('[WS] Error');
        };
    }

    function disconnect() {
        clearTimeout(reconnectTimer);
        stopHeartbeat();
        if (ws) {
            ws.onclose = null;
            ws.close();
            ws = null;
        }
    }

    function scheduleReconnect() {
        clearTimeout(reconnectTimer);
        reconnectTimer = setTimeout(() => {
            if (getToken()) connect();
        }, RECONNECT_INTERVAL);
    }

    function startHeartbeat() {
        stopHeartbeat();
        heartbeatTimer = setInterval(() => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send('ping');
            }
        }, HEARTBEAT_INTERVAL);
    }

    function stopHeartbeat() {
        clearInterval(heartbeatTimer);
    }

    function on(event, callback) {
        if (!listeners[event]) listeners[event] = [];
        listeners[event].push(callback);
        return () => {
            listeners[event] = listeners[event].filter(fn => fn !== callback);
        };
    }

    function emit(event, data) {
        (listeners[event] || []).forEach(fn => {
            try { fn(data); } catch (e) { console.error('[WS] Listener error:', e); }
        });
    }

    return { connect, disconnect, on };
})();

// ---- 通知 UI ----

function showNotification(data) {
    const toast = document.createElement('div');
    toast.className = 'ws-notification';
    const title = document.createElement('div');
    title.className = 'ws-notification-title';
    title.textContent = data.type === 'order_status' ? '订单通知' : '系统通知';
    const body = document.createElement('div');
    body.className = 'ws-notification-body';
    body.textContent = data.message || data.content || '';
    toast.append(title, body);
    document.body.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add('show'));
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

// 注入通知样式
(function injectStyles() {
    const style = document.createElement('style');
    style.textContent = `
        .ws-notification {
            position: fixed; top: 20px; right: 20px; z-index: 9999;
            background: rgba(255,255,255,0.98); border-radius: 12px;
            box-shadow: 0 8px 30px rgba(0,0,0,0.12); padding: 16px 20px;
            min-width: 280px; max-width: 380px; transform: translateX(120%);
            transition: transform 0.3s cubic-bezier(0.4,0,0.2,1);
            border-left: 4px solid #0071e3; font-family: 'Inter', sans-serif;
        }
        .ws-notification.show { transform: translateX(0); }
        .ws-notification-title { font-weight: 600; font-size: 14px; margin-bottom: 4px; color: #1d1d1f; }
        .ws-notification-body { font-size: 13px; color: #6e6e73; line-height: 1.4; }
    `;
    document.head.appendChild(style);
})();

// 页面加载后自动连接
document.addEventListener('DOMContentLoaded', () => {
    if (localStorage.getItem('token')) {
        WSClient.connect();
        WSClient.on('order_status', showNotification);
        WSClient.on('stock_alert', showNotification);
        WSClient.on('promotion', showNotification);
    }
});
