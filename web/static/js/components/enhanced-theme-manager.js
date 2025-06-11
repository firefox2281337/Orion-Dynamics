/**
 * ✨ Улучшенный менеджер тем с современными кнопками (исправленный)
 */
import { showNotification } from '../core/utils.js';

export class EnhancedThemeManager {
    constructor() {
        this.darkModeToggle = document.getElementById('darkModeToggle');
        this.currentTheme = this.getStoredTheme();
        this.init();
    }

    init() {
        this.enhanceButtons();
        this.applyStoredTheme();
        this.setupEventListeners();
        
        // ИСПРАВЛЕНО: помечаем кнопки как инициализированные после первого появления
        setTimeout(() => {
            this.markButtonsAsInitialized();
        }, 1000); // После завершения анимации входа
    }

    markButtonsAsInitialized() {
        // Помечаем кнопки как инициализированные чтобы они больше не анимировались
        if (this.darkModeToggle) {
            this.darkModeToggle.classList.add('initialized');
        }
        
        const appToggle = document.getElementById('appWindowToggle');
        if (appToggle) {
            appToggle.classList.add('initialized');
        }
    }

    enhanceButtons() {
        // Кнопки уже имеют нужные классы в HTML, просто добавляем интерактивность
        if (this.darkModeToggle) {
            this.darkModeToggle.setAttribute('aria-label', 'Переключить тему');
        }

        const appToggle = document.getElementById('appWindowToggle');
        if (appToggle) {
            appToggle.setAttribute('aria-label', 'Открыть приложение');
        }
    }

    setupEventListeners() {
        if (this.darkModeToggle) {
            this.darkModeToggle.addEventListener('click', (e) => {
                this.createRippleEffect(e);
                this.toggleTheme();
            });
        }

        const appToggle = document.getElementById('appWindowToggle');
        if (appToggle) {
            appToggle.addEventListener('click', (e) => {
                this.createRippleEffect(e);
                this.handleAppToggle();
            });
        }
    }

    createRippleEffect(event) {
        const button = event.currentTarget;
        const rect = button.getBoundingClientRect();
        const ripple = document.createElement('span');
        
        ripple.classList.add('ripple');
        
        const size = Math.max(rect.width, rect.height);
        const x = event.clientX - rect.left - size / 2;
        const y = event.clientY - rect.top - size / 2;
        
        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = x + 'px';
        ripple.style.top = y + 'px';
        
        button.appendChild(ripple);
        
        setTimeout(() => {
            ripple.remove();
        }, 600);
    }

    toggleTheme() {
        // Добавляем класс для анимации переключения иконки
        this.darkModeToggle.classList.add('switching');
        
        setTimeout(() => {
            this.currentTheme = this.currentTheme === 'dark' ? 'light' : 'dark';
            this.applyTheme(this.currentTheme);
            this.saveTheme();
            this.updateMonacoTheme();
            
            // Показываем успешное действие
            this.showSuccessAnimation(this.darkModeToggle);
            
            // Убираем класс анимации
            this.darkModeToggle.classList.remove('switching');
            
            // Показываем уведомление
            showNotification(
                `Тема изменена на ${this.currentTheme === 'dark' ? 'тёмную' : 'светлую'}`, 
                'success'
            );
        }, 300);
    }

    showSuccessAnimation(button) {
        button.classList.add('success');
        setTimeout(() => {
            button.classList.remove('success');
        }, 600);
    }

    handleAppToggle() {
        const windowFeatures = 'width=850,height=1080,menubar=no,toolbar=no,location=no,status=no,resizable=no,scrollbars=yes';
        const targetUrl = 'http://192.168.50.220:5000/nexus';
        
        const appWindow = window.open(targetUrl, 'OrionDynamicsApp', windowFeatures);
        const appToggle = document.getElementById('appWindowToggle');
        
        if (appWindow) {
            appWindow.focus();
            this.showSuccessAnimation(appToggle);
            showNotification('Приложение открыто в новом окне', 'success');
        } else {
            showNotification('Не удалось открыть окно. Проверьте блокировку всплывающих окон.', 'error');
        }
    }

    applyTheme(theme) {
        const body = document.body;
        const icon = this.darkModeToggle?.querySelector('i');

        if (theme === 'dark') {
            body.classList.add('dark-mode');
            if (icon) {
                icon.classList.remove('fa-moon');
                icon.classList.add('fa-sun');
            }
            this.applyDarkStyles();
        } else {
            body.classList.remove('dark-mode');
            if (icon) {
                icon.classList.remove('fa-sun');
                icon.classList.add('fa-moon');
            }
            this.applyLightStyles();
        }
    }

    applyStoredTheme() {
        if (this.currentTheme === 'dark') {
            this.applyTheme('dark');
        }
    }

    getStoredTheme() {
        return localStorage.getItem('darkMode') === 'true' ? 'dark' : 'light';
    }

    saveTheme() {
        localStorage.setItem('darkMode', this.currentTheme === 'dark');
    }

    getCurrentTheme() {
        return this.currentTheme;
    }

    applyDarkStyles() {
        const variables = {
            '--dark-color': '#f8f9fa',
            '--light-color': '#1a202c'
        };
        
        Object.entries(variables).forEach(([key, value]) => {
            document.documentElement.style.setProperty(key, value);
        });

        document.body.style.backgroundColor = '#1a202c';
        document.body.style.color = '#f8f9fa';

        this.updateElementStyles('.dashboard-card, .navbar', {
            backgroundColor: '#2d3748',
            color: '#f8f9fa'
        });

        this.updateElementStyles('.list-group-item', {
            backgroundColor: '#2d3748',
            color: '#f8f9fa',
            borderColor: '#4a5568'
        });

        this.updateElementStyles('.metric-label, .last-check', {
            color: '#a0aec0'
        });
    }

    applyLightStyles() {
        const variables = {
            '--dark-color': '#2d3748',
            '--light-color': '#f8f9fa'
        };
        
        Object.entries(variables).forEach(([key, value]) => {
            document.documentElement.style.setProperty(key, value);
        });

        document.body.style.backgroundColor = '#f0f2f5';
        document.body.style.color = '#2d3748';

        this.updateElementStyles('.dashboard-card, .navbar', {
            backgroundColor: 'white',
            color: '#2d3748'
        });

        this.updateElementStyles('.list-group-item', {
            backgroundColor: 'white',
            color: '#2d3748',
            borderColor: 'rgba(0,0,0,.125)'
        });

        this.updateElementStyles('.metric-label, .last-check', {
            color: '#718096'
        });
    }

    updateElementStyles(selector, styles) {
        document.querySelectorAll(selector).forEach(element => {
            Object.assign(element.style, styles);
        });
    }

    updateMonacoTheme() {
        if (typeof monaco !== 'undefined' && monaco.editor) {
            const theme = this.currentTheme === 'dark' ? 'vs-dark' : 'vs';
            monaco.editor.setTheme(theme);
            
            const editors = monaco.editor.getEditors();
            editors.forEach(() => monaco.editor.setTheme(theme));
        }
    }
}

// ИСПРАВЛЕНО: убираем эффект параллакса который мог двигать кнопки
export class ButtonEffects {
    static init() {
        // Добавляем только вибрацию для мобильных, без параллакса
        const buttons = document.querySelectorAll('.floating-button-base');
        buttons.forEach(button => {
            let pressTimer;
            
            button.addEventListener('touchstart', () => {
                pressTimer = setTimeout(() => {
                    if (navigator.vibrate) {
                        navigator.vibrate(50);
                    }
                }, 300);
            });
            
            button.addEventListener('touchend', () => {
                clearTimeout(pressTimer);
            });
        });

        // Добавляем стили для анимации вибрации
        if (!document.getElementById('button-effects-styles')) {
            const style = document.createElement('style');
            style.id = 'button-effects-styles';
            style.textContent = `
                @keyframes vibrate {
                    0%, 100% { transform: translateX(0); }
                    10%, 30%, 50%, 70%, 90% { transform: translateX(-1px); }
                    20%, 40%, 60%, 80% { transform: translateX(1px); }
                }
            `;
            document.head.appendChild(style);
        }
    }
}