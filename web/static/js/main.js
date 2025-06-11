/**
 * 🎪 Главная точка входа приложения (полная версия с новыми кнопками)
 */
import { EnhancedThemeManager, ButtonEffects } from './components/enhanced-theme-manager.js';
import { TooltipManager } from './components/tooltip-manager.js';
import { RefreshButton } from './components/refresh-button.js';
import { Navigation } from './components/navigation.js';

// Импорт страниц
import { KaskoPage } from './pages/kasko-page.js';
import { MegahelperPage } from './pages/megahelper-page.js';
import { MetragiPage } from './pages/metragi-page.js';
import { SoftwarePage } from './pages/software-page.js';
import { SqlPage } from './pages/sql-page.js';

import { showNotification } from './core/utils.js';

class OrionDynamicsApp {
    constructor() {
        this.components = new Map();
        this.currentPage = null;
        this.isInitialized = false;
        this.initializationErrors = [];
    }

    async init() {
        if (this.isInitialized) return;

        try {

            // Инициализируем базовые компоненты (с обработкой ошибок)
            await this.initializeBaseComponents();

            // Инициализируем страницу в зависимости от URL (с обработкой ошибок)
            await this.initializePage();

            // Настраиваем глобальные обработчики
            this.setupGlobalHandlers();

            this.isInitialized = true;
            
            // Отчет об инициализации
            if (this.initializationErrors.length > 0) {
                showNotification(`Приложение загружено с ${this.initializationErrors.length} предупреждениями`, 'warning');
            } else {
            }

        } catch (error) {
            showNotification('Критическая ошибка загрузки приложения', 'error');
            
            // Пытаемся загрузить хотя бы базовую функциональность
            this.fallbackInitialization();
        }
    }

    async initializeBaseComponents() {
        const components = [
            { name: 'themeManager', class: EnhancedThemeManager, critical: true },
            { name: 'tooltipManager', class: TooltipManager, critical: false },
            { name: 'refreshButton', class: RefreshButton, critical: false },
            { name: 'navigation', class: Navigation, critical: false }
        ];

        for (const { name, class: ComponentClass, critical } of components) {
            try {
                const instance = new ComponentClass();
                this.components.set(name, instance);
            } catch (error) {
                const errorMsg = `Ошибка инициализации ${name}: ${error.message}`;
                this.initializationErrors.push(errorMsg);
                
                if (critical) {
                    throw new Error(errorMsg);
                } else {
                }
            }
        }

        // Инициализируем эффекты кнопок
        try {
            ButtonEffects.init();
        } catch (error) {
            this.initializationErrors.push(`ButtonEffects: ${error.message}`);
        }
    }

    async initializePage() {
        const path = window.location.pathname;
        let pageInitialized = false;
        
        try {
            if (path.includes('kasko')) {
                this.currentPage = new KaskoPage();
                this.components.set('kaskoPage', this.currentPage);
                pageInitialized = true;
                
            } else if (path.includes('megahelper')) {
                this.currentPage = new MegahelperPage();
                this.components.set('megahelperPage', this.currentPage);
                pageInitialized = true;
                
            } else if (path.includes('data_extraction') || path.includes('metragi')) {
                this.currentPage = new MetragiPage();
                this.components.set('metragiPage', this.currentPage);
                pageInitialized = true;
                
            } else if (path.includes('software')) {
                this.currentPage = new SoftwarePage();
                this.components.set('softwarePage', this.currentPage);
                pageInitialized = true;
                
            } else if (path.includes('sql')) {
                this.currentPage = new SqlPage();
                this.components.set('sqlPage', this.currentPage);
                pageInitialized = true;
                
            } else {
                
                // Попробуем определить страницу по наличию характерных элементов
                if (document.getElementById('extractionForm')) {
                    this.currentPage = new MetragiPage();
                    this.components.set('metragiPage', this.currentPage);
                    pageInitialized = true;
                } else if (document.getElementById('dataForm')) {
                    this.currentPage = new MegahelperPage();
                    this.components.set('megahelperPage', this.currentPage);
                    pageInitialized = true;
                } else if (document.getElementById('monaco-editor')) {
                    this.currentPage = new SqlPage();
                    this.components.set('sqlPage', this.currentPage);
                    pageInitialized = true;
                }
            }
        } catch (error) {
            const errorMsg = `Ошибка инициализации страницы: ${error.message}`;
            this.initializationErrors.push(errorMsg);
            
            // Не выбрасываем ошибку, продолжаем с базовой функциональностью
        }
    }

    fallbackInitialization() {
        
        try {
            // Пытаемся инициализировать хотя бы тему
            if (!this.components.has('themeManager')) {
                this.components.set('themeManager', new EnhancedThemeManager());
            }
            
            // Настраиваем базовые обработчики
            this.setupGlobalHandlers();
            
            this.isInitialized = true;
        } catch (fallbackError) {
        }
    }

    setupGlobalHandlers() {
        try {
            this.setupAnimations();
        } catch (error) {
        }
    }

    setupAnimations() {
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-fade-in');
                }
            });
        }, observerOptions);

        document.querySelectorAll('.dashboard-card, .metric-card').forEach(card => {
            observer.observe(card);
        });
    }

    getComponent(name) {
        return this.components.get(name);
    }

    // Методы для отладки
    getInitializationErrors() {
        return this.initializationErrors;
    }

    reinitializePage() {
        if (this.currentPage) {
            this.initializePage();
        }
    }

    getComponentsStatus() {
        const status = {};
        this.components.forEach((component, name) => {
            status[name] = {
                initialized: !!component,
                type: component.constructor.name
            };
        });
        return status;
    }
}

// Глобальная инициализация
window.OrionApp = new OrionDynamicsApp();

// Автозапуск при загрузке DOM
document.addEventListener('DOMContentLoaded', () => {
    window.OrionApp.init();
});

// Глобальные методы для отладки
window.debugOrion = {
    getErrors: () => window.OrionApp.getInitializationErrors(),
    getStatus: () => window.OrionApp.getComponentsStatus(),
    reinit: () => window.OrionApp.reinitializePage(),
    checkJQuery: () => {
        
        // Проверяем элементы дат
        const startDate = document.getElementById('startDate');
        const endDate = document.getElementById('endDate');
    },
    
    // Универсальные методы для проверки элементов
    checkPage: () => {
        const path = window.location.pathname;
    },
    
    // Принудительная инициализация страниц
    forceInit: {
        metragi: () => {
            try {
                const page = new MetragiPage();
                window.OrionApp.components.set('metragiPage', page);
                return page;
            } catch (error) {
            }
        }
    },
    
    // Специальные методы для MegahelperPage
    megahelper: {
        getStatus: () => {
            const page = window.OrionApp.getComponent('megahelperPage');
            return page ? page.getDatePickerStatus() : 'MegahelperPage не найдена';
        },
        switchToNative: () => {
            const page = window.OrionApp.getComponent('megahelperPage');
            if (page) page.switchToNativeDatePickers();
        },
        retryJQuery: () => {
            const page = window.OrionApp.getComponent('megahelperPage');
            if (page) page.retryJQueryDatePickers();
        }
    },
    
    // Специальные методы для MetragiPage
    metragi: {
        getStatus: () => {
            const page = window.OrionApp.getComponent('metragiPage');
            if (!page) {
                return 'MetragiPage не найдена';
            }
            return page.getStatus();
        },
        checkFileInput: () => {
            const fileInput = document.getElementById('excel_file');
            const fileInfo = document.getElementById('file-info');
            const fileName = document.getElementById('file-name');
            const submitButton = document.getElementById('submitButton');
            const uploadContainer = document.querySelector('.file-upload-container');
        },
        testFile: () => {
            const page = window.OrionApp.getComponent('metragiPage');
            if (page) {
                page.testFileSelection();
            } else {
            }
        },
        checkEvents: () => {
            const fileInput = document.getElementById('excel_file');
            if (fileInput) {
                
                // Клонируем элемент чтобы увидеть все события
                const events = typeof getEventListeners !== 'undefined' ? getEventListeners(fileInput) : 'getEventListeners недоступен';
                
                // Проверяем родительские элементы
            }
        },
        simulateClick: () => {
            const fileInput = document.getElementById('excel_file');
            if (fileInput) {
                fileInput.click();
            }
        },
        checkHTML: () => {
            const form = document.getElementById('extractionForm');
        }
    },
    
    // Специальные методы для SqlPage
    sql: {
        getStatus: () => {
            const page = window.OrionApp.getComponent('sqlPage');
            return page ? page.getStatus() : 'SqlPage не найдена';
        },
        checkTable: () => {
            const table = document.getElementById('results-table');
        },
        clearResults: () => {
            const page = window.OrionApp.getComponent('sqlPage');
            if (page) page.clearResultsTable();
        }
    },

    // Методы для тестирования новых кнопок
    buttons: {
        test: () => {
        },
        testRipple: () => {
            const button = document.getElementById('darkModeToggle');
            if (button) {
                const event = new MouseEvent('click', {
                    clientX: button.getBoundingClientRect().left + 30,
                    clientY: button.getBoundingClientRect().top + 30
                });
                button.dispatchEvent(event);
            }
        },
        checkTheme: () => {
            const themeManager = window.OrionApp.getComponent('themeManager');
        }
    }
};

export default OrionDynamicsApp;