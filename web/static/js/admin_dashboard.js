// web/static/js/admin_dashboard.js
/**
 * Главный JavaScript файл админ панели
 * Управляет всей интерактивностью и обновлениями в реальном времени
 */

class AdminDashboard {
    constructor() {
        this.charts = {};
        this.updateIntervals = {};
        this.init();
    }

    init() {
        console.log('🚀 Admin Dashboard initializing...');
        this.setupEventListeners();
        this.setupRealTimeUpdates();
        this.loadInitialData();
        console.log('✅ Admin Dashboard ready');
    }

    setupEventListeners() {
        // Sidebar toggle for mobile
        document.addEventListener('click', (e) => {
            if (e.target.matches('.sidebar-toggle')) {
                this.toggleSidebar();
            }
        });

        // Performance timeframe selector
        const timeframeSelect = document.getElementById('performanceTimeframe');
        if (timeframeSelect) {
            timeframeSelect.addEventListener('change', (e) => {
                this.updatePerformanceChart(e.target.value);
            });
        }

        // Refresh buttons
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-refresh]')) {
                const target = e.target.dataset.refresh;
                this.refreshComponent(target);
            }
        });

        // Quick action buttons
        document.addEventListener('click', (e) => {
            const button = e.target.closest('[data-action]');
            if (button) {
                const action = button.dataset.action;
                this.executeQuickAction(action);
            }
        });
    }

    setupRealTimeUpdates() {
        // System metrics every 5 seconds
        this.updateIntervals.metrics = setInterval(() => {
            this.updateSystemMetrics();
        }, 5000);

        // Activity feed every 10 seconds
        this.updateIntervals.activity = setInterval(() => {
            this.updateRecentActivity();
        }, 10000);

        // Database status every 30 seconds
        this.updateIntervals.database = setInterval(() => {
            this.updateDatabaseStatus();
        }, 30000);
    }

    async loadInitialData() {
        try {
            await Promise.all([
                this.loadPerformanceChart(),
                this.loadRecentActivity(),
                this.loadSecurityAlerts(),
                this.updateSystemMetrics()
            ]);
        } catch (error) {
            console.error('Error loading initial data:', error);
            this.showToast('error', 'Ошибка загрузки данных панели');
        }
    }

    async updateSystemMetrics() {
        try {
            const response = await fetch('/admin/api/stats');
            if (!response.ok) throw new Error('Failed to fetch stats');
            
            const stats = await response.json();
            
            // Update real-time metrics
            this.updateMetricDisplay('cpu', stats.system.cpu_usage);
            this.updateMetricDisplay('memory', stats.system.memory_usage);
            this.updateMetricDisplay('disk', stats.system.disk_usage);
            
            // Update process count
            const processesElement = document.getElementById('processesValue');
            if (processesElement) {
                processesElement.textContent = stats.system.process_count;
            }
            
        } catch (error) {
            console.error('Error updating system metrics:', error);
        }
    }

    updateMetricDisplay(metric, value) {
        const valueElement = document.getElementById(`${metric}Value`);
        const progressElement = document.getElementById(`${metric}Progress`);
        
        if (valueElement && progressElement) {
            valueElement.textContent = `${value}%`;
            progressElement.style.width = `${value}%`;
            
            // Update color based on usage
            progressElement.className = 'mini-progress-bar';
            if (value > 80) {
                progressElement.classList.add('critical');
            } else if (value > 60) {
                progressElement.classList.add('warning');
            } else {
                progressElement.classList.add('normal');
            }
        }
    }

    async loadPerformanceChart(timeframe = '24h') {
        try {
            const response = await fetch(`/admin/api/performance-data?timeframe=${timeframe}`);
            const data = await response.json();
            
            const ctx = document.getElementById('performanceChart');
            if (!ctx) return;
            
            // Destroy existing chart if it exists
            if (this.charts.performance) {
                this.charts.performance.destroy();
            }
            
            this.charts.performance = new Chart(ctx.getContext('2d'), {
                type: 'line',
                data: {
                    labels: data.labels.map(label => {
                        const date = new Date(label);
                        return timeframe === '7d' ? 
                            date.toLocaleDateString() : 
                            date.toLocaleTimeString();
                    }),
                    datasets: [{
                        label: 'CPU %',
                        data: data.cpu,
                        borderColor: '#4361ee',
                        backgroundColor: 'rgba(67, 97, 238, 0.1)',
                        fill: true,
                        tension: 0.4
                    }, {
                        label: 'Memory %',
                        data: data.memory,
                        borderColor: '#27ae60',
                        backgroundColor: 'rgba(39, 174, 96, 0.1)',
                        fill: true,
                        tension: 0.4
                    }, {
                        label: 'Disk %',
                        data: data.disk,
                        borderColor: '#f39c12',
                        backgroundColor: 'rgba(243, 156, 18, 0.1)',
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        intersect: false,
                        mode: 'index'
                    },
                    plugins: {
                        legend: {
                            labels: {
                                color: '#ffffff',
                                usePointStyle: true
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(26, 26, 46, 0.9)',
                            titleColor: '#ffffff',
                            bodyColor: '#ffffff',
                            borderColor: '#2d3748',
                            borderWidth: 1
                        }
                    },
                    scales: {
                        x: {
                            ticks: {
                                color: '#8e8e93',
                                maxTicksLimit: 10
                            },
                            grid: {
                                color: '#2d3748'
                            }
                        },
                        y: {
                            beginAtZero: true,
                            max: 100,
                            ticks: {
                                color: '#8e8e93',
                                callback: function(value) {
                                    return value + '%';
                                }
                            },
                            grid: {
                                color: '#2d3748'
                            }
                        }
                    }
                }
            });
        } catch (error) {
            console.error('Error loading performance chart:', error);
        }
    }

    async updatePerformanceChart(timeframe) {
        await this.loadPerformanceChart(timeframe);
    }

    async loadRecentActivity() {
        try {
            const response = await fetch('/admin/api/logs?limit=8');
            const data = await response.json();
            
            this.updateActivityDisplay(data.logs);
        } catch (error) {
            console.error('Error loading recent activity:', error);
        }
    }

    async updateRecentActivity() {
        await this.loadRecentActivity();
    }

    updateActivityDisplay(logs) {
        const container = document.getElementById('recentActivity');
        if (!container) return;
        
        container.innerHTML = '';
        
        if (logs.length === 0) {
            container.innerHTML = `
                <div class="no-data">
                    <i class="fas fa-info-circle"></i>
                    <p>Нет последней активности</p>
                </div>
            `;
            return;
        }
        
        logs.forEach(log => {
            const item = document.createElement('div');
            item.className = 'activity-item';
            
            const iconClass = this.getLogIcon(log.level);
            const timeAgo = this.formatTimeAgo(new Date(log.timestamp));
            
            item.innerHTML = `
                <div class="activity-icon ${log.level.toLowerCase()}">
                    <i class="fas ${iconClass}"></i>
                </div>
                <div class="activity-content">
                    <div class="activity-action">${this.escapeHtml(log.message)}</div>
                    <div class="activity-details">
                        <span><i class="fas fa-file-code"></i> ${this.escapeHtml(log.source)}</span>
                        <span><i class="fas fa-clock"></i> ${timeAgo}</span>
                        <span class="log-level ${log.level.toLowerCase()}">
                            <i class="fas fa-tag"></i> ${log.level}
                        </span>
                    </div>
                </div>
            `;
            
            container.appendChild(item);
        });
    }

    async updateDatabaseStatus() {
        try {
            const response = await fetch('/admin/api/stats');
            const stats = await response.json();
            
            const container = document.getElementById('databaseStatus');
            if (!container || !stats.databases) return;
            
            container.innerHTML = '';
            
            Object.entries(stats.databases.connection_pools).forEach(([name, info]) => {
                const item = document.createElement('div');
                item.className = `db-item ${info.connected ? 'online' : 'offline'}`;
                
                item.innerHTML = `
                    <div class="db-name">${this.escapeHtml(name)}</div>
                    <div class="db-status">
                        ${info.connected ? `
                            <span class="status-badge success">
                                <i class="fas fa-check-circle"></i>
                                Онлайн
                            </span>
                            ${info.response_time ? `<small class="response-time">${info.response_time}ms</small>` : ''}
                        ` : `
                            <span class="status-badge danger">
                                <i class="fas fa-times-circle"></i>
                                Офлайн
                            </span>
                        `}
                    </div>
                `;
                
                container.appendChild(item);
            });
        } catch (error) {
            console.error('Error updating database status:', error);
        }
    }

    async loadSecurityAlerts() {
        try {
            const response = await fetch('/admin/api/security-events');
            const events = await response.json();
            
            // Update security badge if there are high severity events
            const badge = document.querySelector('.nav-item[href="/admin/security"] .nav-badge');
            const highSeverityCount = events.filter(e => e.severity === 'high').length;
            
            if (badge && highSeverityCount > 0) {
                badge.textContent = highSeverityCount;
                badge.style.display = 'inline-block';
            } else if (badge) {
                badge.style.display = 'none';
            }
            
            // Show security modal if there are critical alerts
            if (highSeverityCount > 0) {
                this.showSecurityModal(events);
            }
        } catch (error) {
            console.error('Error loading security alerts:', error);
        }
    }

    showSecurityModal(events) {
        const modal = document.getElementById('securityModal');
        const alertsContainer = document.getElementById('securityAlerts');
        
        if (!modal || !alertsContainer) return;
        
        alertsContainer.innerHTML = '';
        
        const highSeverityEvents = events.filter(e => e.severity === 'high');
        
        if (highSeverityEvents.length === 0) {
            alertsContainer.innerHTML = `
                <div class="no-alerts">
                    <i class="fas fa-shield-alt"></i>
                    <h4>Система защищена</h4>
                    <p>Критичных событий безопасности не обнаружено</p>
                </div>
            `;
        } else {
            highSeverityEvents.forEach(event => {
                const alert = document.createElement('div');
                alert.className = `security-alert ${event.severity}`;
                
                alert.innerHTML = `
                    <div class="alert-header">
                        <span class="alert-type">${this.escapeHtml(event.type)}</span>
                        <span class="alert-severity ${event.severity}">${event.severity}</span>
                    </div>
                    <div class="alert-content">
                        <p>${this.escapeHtml(event.message)}</p>
                        <div class="alert-details">
                            <span><i class="fas fa-clock"></i> ${this.formatTimeAgo(new Date(event.timestamp))}</span>
                            <span><i class="fas fa-map-marker-alt"></i> ${this.escapeHtml(event.source)}</span>
                        </div>
                    </div>
                `;
                
                alertsContainer.appendChild(alert);
            });
        }
        
        // Auto-show modal for critical alerts
        if (highSeverityEvents.length > 0) {
            setTimeout(() => {
                modal.classList.add('active');
                modal.querySelector('.modal-content').style.transform = 'scale(1)';
                modal.querySelector('.modal-content').style.opacity = '1';
            }, 1000);
        }
    }

    async executeQuickAction(action) {
        switch (action) {
            case 'backup':
                await this.createBackup();
                break;
            case 'code-editor':
                this.openCodeEditor();
                break;
            case 'terminal':
                this.openTerminal();
                break;
            case 'restart':
                await this.showSystemRestart();
                break;
            default:
                console.warn('Unknown action:', action);
        }
    }

    async createBackup() {
        const button = document.querySelector('[data-action="backup"]');
        const originalText = button.innerHTML;
        
        button.innerHTML = '<div class="spinner"></div> Создание...';
        button.disabled = true;
        
        try {
            const response = await fetch('/admin/api/create-backup', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showToast('success', result.message || 'Бэкап создан успешно');
            } else {
                this.showToast('error', result.error || 'Ошибка создания бэкапа');
            }
        } catch (error) {
            console.error('Backup error:', error);
            this.showToast('error', 'Ошибка создания бэкапа');
        } finally {
            button.innerHTML = originalText;
            button.disabled = false;
        }
    }

    openCodeEditor() {
        window.open('/admin/code-editor', '_blank');
    }

    openTerminal() {
        window.open('/admin/terminal', '_blank');
    }

    async showSystemRestart() {
        const confirmed = await this.showConfirmDialog(
            'Перезагрузка системы',
            'Вы уверены, что хотите перезагрузить систему? Все несохраненные данные будут потеряны.',
            'Перезагрузить',
            'danger'
        );
        
        if (confirmed) {
            try {
                const response = await fetch('/admin/api/system/restart', {
                    method: 'POST'
                });
                
                const result = await response.json();
                if (result.success) {
                    this.showRestartIndicator();
                } else {
                    this.showToast('error', result.error || 'Ошибка перезагрузки');
                }
            } catch (error) {
                console.error('Restart error:', error);
                this.showToast('error', 'Ошибка перезагрузки системы');
            }
        }
    }

    showRestartIndicator() {
        const indicator = document.createElement('div');
        indicator.className = 'restart-indicator';
        indicator.innerHTML = `
            <div class="restart-content">
                <div class="spinner large"></div>
                <h3>Перезагрузка системы</h3>
                <p>Система перезагружается, подождите...</p>
                <div class="restart-timer" id="restartTimer">15</div>
                <p style="font-size: 0.875rem; color: var(--text-secondary); margin-top: 1rem;">
                    Страница автоматически обновится после перезагрузки
                </p>
            </div>
        `;
        
        document.body.appendChild(indicator);
        
        let counter = 15;
        const timer = setInterval(() => {
            counter--;
            const timerElement = document.getElementById('restartTimer');
            if (timerElement) {
                timerElement.textContent = counter;
            }
            
            if (counter <= 0) {
                clearInterval(timer);
                window.location.reload();
            }
        }, 1000);
    }

    async refreshComponent(component) {
        const button = document.querySelector(`[data-refresh="${component}"]`);
        const icon = button?.querySelector('i');
        
        if (icon) {
            icon.classList.add('fa-spin');
        }
        
        try {
            switch (component) {
                case 'database':
                    await this.updateDatabaseStatus();
                    this.showToast('success', 'Статус баз данных обновлен');
                    break;
                case 'activity':
                    await this.updateRecentActivity();
                    this.showToast('success', 'Активность обновлена');
                    break;
                case 'performance':
                    const timeframe = document.getElementById('performanceTimeframe')?.value || '24h';
                    await this.updatePerformanceChart(timeframe);
                    this.showToast('success', 'График производительности обновлен');
                    break;
                default:
                    console.warn('Unknown component:', component);
            }
        } catch (error) {
            console.error(`Error refreshing ${component}:`, error);
            this.showToast('error', `Ошибка обновления ${component}`);
        } finally {
            if (icon) {
                icon.classList.remove('fa-spin');
            }
        }
    }

    toggleSidebar() {
        const sidebar = document.getElementById('sidebar');
        sidebar?.classList.toggle('active');
    }

    // Utility methods
    getLogIcon(level) {
        const icons = {
            'error': 'fa-exclamation-triangle',
            'warning': 'fa-exclamation-circle',
            'info': 'fa-info-circle',
            'debug': 'fa-bug',
            'success': 'fa-check-circle'
        };
        return icons[level.toLowerCase()] || 'fa-circle';
    }

    formatTimeAgo(date) {
        const now = new Date();
        const diffInSeconds = Math.floor((now - date) / 1000);
        
        if (diffInSeconds < 60) return `${diffInSeconds}с назад`;
        if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}м назад`;
        if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}ч назад`;
        return `${Math.floor(diffInSeconds / 86400)}д назад`;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showToast(type, message, duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const icons = {
            success: 'fa-check-circle',
            error: 'fa-exclamation-triangle',
            warning: 'fa-exclamation-circle',
            info: 'fa-info-circle'
        };
        
        toast.innerHTML = `
            <div class="toast-content">
                <i class="fas ${icons[type] || icons.info}"></i>
                <span>${this.escapeHtml(message)}</span>
            </div>
            <button class="toast-close" onclick="this.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        // Create container if it doesn't exist
        let container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container';
            document.body.appendChild(container);
        }
        
        container.appendChild(toast);
        
        // Animate in
        requestAnimationFrame(() => {
            toast.style.transform = 'translateX(0)';
            toast.style.opacity = '1';
        });
        
        // Auto remove
        setTimeout(() => {
            toast.style.transform = 'translateX(100%)';
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }

    async showConfirmDialog(title, message, confirmText = 'Подтвердить', type = 'primary') {
        return new Promise((resolve) => {
            const modal = document.createElement('div');
            modal.className = 'modal active';
            modal.innerHTML = `
                <div class="modal-overlay"></div>
                <div class="modal-content" style="transform: scale(1); opacity: 1;">
                    <div class="modal-header">
                        <h3>${this.escapeHtml(title)}</h3>
                    </div>
                    <div class="modal-body">
                        <p>${this.escapeHtml(message)}</p>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" data-action="cancel">Отмена</button>
                        <button class="btn btn-${type}" data-action="confirm">${this.escapeHtml(confirmText)}</button>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
            
            modal.addEventListener('click', (e) => {
                if (e.target.matches('[data-action="confirm"]')) {
                    modal.remove();
                    resolve(true);
                } else if (e.target.matches('[data-action="cancel"]') || e.target.matches('.modal-overlay')) {
                    modal.remove();
                    resolve(false);
                }
            });
        });
    }

    // Cleanup method
    destroy() {
        // Clear all intervals
        Object.values(this.updateIntervals).forEach(interval => {
            clearInterval(interval);
        });
        
        // Destroy charts
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
        
        console.log('Admin Dashboard destroyed');
    }
}

// Global functions for template compatibility
window.createBackup = () => window.adminDashboard?.executeQuickAction('backup');
window.openCodeEditor = () => window.adminDashboard?.executeQuickAction('code-editor');
window.openTerminal = () => window.adminDashboard?.executeQuickAction('terminal');
window.showSystemRestart = () => window.adminDashboard?.executeQuickAction('restart');
window.refreshDatabaseStatus = () => window.adminDashboard?.refreshComponent('database');

window.closeSecurityModal = () => {
    const modal = document.getElementById('securityModal');
    if (modal) {
        modal.classList.remove('active');
        modal.querySelector('.modal-content').style.transform = 'scale(0.9)';
        modal.querySelector('.modal-content').style.opacity = '0';
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.adminDashboard = new AdminDashboard();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.adminDashboard) {
        window.adminDashboard.destroy();
    }
});