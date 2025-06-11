/**
 * 🔧 Утилиты приложения (обновленные)
 */

export const $ = (selector) => document.querySelector(selector);
export const $$ = (selector) => document.querySelectorAll(selector);

export const createElement = (tag, options = {}) => {
    const element = document.createElement(tag);
    if (options.className) element.className = options.className;
    if (options.innerHTML) element.innerHTML = options.innerHTML;
    if (options.textContent) element.textContent = options.textContent;
    return element;
};

export const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

export const debounce = (func, wait) => {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
};

// Улучшенная система уведомлений
class NotificationManager {
    constructor() {
        this.container = null;
        this.notifications = new Map();
        this.counter = 0;
        this.init();
    }

    init() {
        // Создаем контейнер для уведомлений
        this.container = document.createElement('div');
        this.container.id = 'notification-container';
        this.container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 10000;
            width: 400px;
            max-width: 90vw;
            pointer-events: none;
        `;
        document.body.appendChild(this.container);
    }

    show(message, type = 'info', duration = 5000) {
        const id = ++this.counter;
        
        // Создаем уведомление
        const notification = this.createNotification(message, type, id);
        
        // Добавляем в контейнер
        this.container.appendChild(notification);
        this.notifications.set(id, notification);
        
        // Анимация появления
        requestAnimationFrame(() => {
            notification.style.transform = 'translateX(0)';
            notification.style.opacity = '1';
        });
        
        // Переупорядочиваем уведомления
        this.reorderNotifications();
        
        // Автоматическое удаление
        setTimeout(() => {
            this.hide(id);
        }, duration);
        
        return id;
    }

    createNotification(message, type, id) {
        const notification = document.createElement('div');
        
        const typeConfig = {
            success: { icon: 'fa-check-circle', color: '#198754', bg: '#d1e7dd' },
            error: { icon: 'fa-exclamation-triangle', color: '#dc3545', bg: '#f8d7da' },
            warning: { icon: 'fa-exclamation-triangle', color: '#fd7e14', bg: '#fff3cd' },
            info: { icon: 'fa-info-circle', color: '#0dcaf0', bg: '#d1ecf1' }
        };
        
        const config = typeConfig[type] || typeConfig.info;
        
        notification.className = `notification notification-${type}`;
        notification.style.cssText = `
            display: flex;
            align-items: center;
            margin-bottom: 12px;
            padding: 16px 20px;
            background: ${config.bg};
            border: 1px solid ${config.color}40;
            border-left: 4px solid ${config.color};
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            font-size: 14px;
            line-height: 1.4;
            color: #333;
            transform: translateX(100%);
            opacity: 0;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            pointer-events: auto;
            backdrop-filter: blur(10px);
        `;
        
        notification.innerHTML = `
            <i class="fas ${config.icon}" style="color: ${config.color}; margin-right: 12px; font-size: 16px;"></i>
            <span style="flex: 1;">${message}</span>
            <button type="button" style="
                background: none;
                border: none;
                color: #666;
                font-size: 18px;
                cursor: pointer;
                margin-left: 12px;
                padding: 0;
                line-height: 1;
                opacity: 0.7;
                transition: opacity 0.2s;
            " onmouseover="this.style.opacity='1'" onmouseout="this.style.opacity='0.7'">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        // Обработчик закрытия
        const closeBtn = notification.querySelector('button');
        closeBtn.addEventListener('click', () => {
            this.hide(id);
        });
        
        // Автопаузование при наведении
        notification.addEventListener('mouseenter', () => {
            notification.dataset.paused = 'true';
        });
        
        notification.addEventListener('mouseleave', () => {
            delete notification.dataset.paused;
        });
        
        return notification;
    }

    hide(id) {
        const notification = this.notifications.get(id);
        if (!notification) return;
        
        // Анимация исчезновения
        notification.style.transform = 'translateX(100%)';
        notification.style.opacity = '0';
        notification.style.maxHeight = notification.offsetHeight + 'px';
        
        setTimeout(() => {
            notification.style.maxHeight = '0';
            notification.style.marginBottom = '0';
            notification.style.padding = '0 20px';
        }, 150);
        
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
            this.notifications.delete(id);
            this.reorderNotifications();
        }, 300);
    }

    reorderNotifications() {
        // Анимированная переупорядочивание уведомлений
        const notifications = Array.from(this.notifications.values());
        notifications.forEach((notification, index) => {
            notification.style.transform = `translateX(0) translateY(${index * 4}px)`;
        });
    }

    clear() {
        this.notifications.forEach((notification, id) => {
            this.hide(id);
        });
    }
}

// Создаем глобальный менеджер уведомлений
const notificationManager = new NotificationManager();

export const showNotification = (message, type = 'info', duration = 5000) => {
    return notificationManager.show(message, type, duration);
};

export const hideNotification = (id) => {
    notificationManager.hide(id);
};

export const clearNotifications = () => {
    notificationManager.clear();
};