const NexusApp = {
    // Случайные слоганы
    slogans: [
        "В ритме задач.",
        "Быстрее, чем ты.",
        "Автоматизируй это.",
        "Сделано без суеты.",
        "Не мечтай — автоматизируй.",
        "Всё само.",
        "Запускай — отдыхай.",
        "Просто сделай.",
        "Дальше — легче.",
        "Один клик и готово.",
    ],

    // Инициализация приложения
    init() {
        this.loadTheme();
        this.setupRandomSlogan();
        this.createButtons();
        this.createStepsIfNeeded();
        this.setupAnimations();
    },

    // Переключение темной темы
    toggleDarkMode() {
        const body = document.body;
        const isDark = body.getAttribute('data-theme') === 'dark';
        
        if (isDark) {
            body.removeAttribute('data-theme');
            localStorage.setItem('theme', 'light');
        } else {
            body.setAttribute('data-theme', 'dark');
            localStorage.setItem('theme', 'dark');
        }
    },

    // Загрузка сохраненной темы
    loadTheme() {
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'dark') {
            document.body.setAttribute('data-theme', 'dark');
        }
    },

    // Установка случайного слогана
    setupRandomSlogan() {
        if (window.pageConfig.randomSlogan) {
            const subtitleElement = document.getElementById('subtitle');
            const randomSlogan = this.slogans[Math.floor(Math.random() * this.slogans.length)];
            subtitleElement.textContent = randomSlogan;
        }
    },

    // Создание кнопок
    createButtons() {
        const menuButtons = document.getElementById('menu-buttons');
        if (!window.pageConfig.buttons) return;

        window.pageConfig.buttons.forEach(buttonConfig => {
            const button = this.createButton(buttonConfig);
            menuButtons.appendChild(button);
        });
    },

    // Создание отдельной кнопки
    createButton(config) {
        const button = document.createElement('button');
        button.className = `btn ${config.disabled ? 'btn-disabled' : 'btn-secondary'}`;
        
        if (config.disabled) {
            button.style.position = 'relative';
            button.onclick = () => this.showNotification(config.disabledMessage || 'В разработке', 'warning');
        } else {
            button.onclick = () => this.navigateTo(config.url, config.message);
        }
        
        button.innerHTML = `
            <i class="${config.icon}"></i>
            <span>${config.text}</span>
            ${config.badge ? `<span class="coming-soon">${config.badge}</span>` : ''}
        `;
        
        return button;
    },

    // Создание индикатора шагов если нужно
    createStepsIfNeeded() {
        if (window.pageConfig.showSteps) {
            const stepsContainer = document.getElementById('steps-container');
            const stepsIndicator = this.createStepsIndicator(window.pageConfig.currentStep || 1);
            stepsContainer.appendChild(stepsIndicator);
        }
    },

    // Создание индикатора шагов
    createStepsIndicator(currentStep = 1) {
        const steps = [
            { number: 1, text: 'Выбор типа' },
            { number: 2, text: 'Загрузка файла' },
            { number: 3, text: 'Сопоставление' },
            { number: 4, text: 'Обработка' }
        ];
        
        const stepsWrapper = document.createElement('div');
        stepsWrapper.className = 'steps-indicator';
        
        steps.forEach((step, index) => {
            const stepElement = document.createElement('div');
            stepElement.className = `step ${step.number <= currentStep ? 'active' : ''}`;
            stepElement.innerHTML = `
                <div class="step-number">${step.number}</div>
                <div class="step-text">${step.text}</div>
            `;
            stepsWrapper.appendChild(stepElement);
            
            if (index < steps.length - 1) {
                const connector = document.createElement('div');
                connector.className = 'step-connector';
                stepsWrapper.appendChild(connector);
            }
        });
        
        return stepsWrapper;
    },

    // Настройка анимаций
    setupAnimations() {
        // Анимация при загрузке
        const contentWrapper = document.querySelector('.content-wrapper');
        contentWrapper.style.transform = 'translateY(20px)';
        contentWrapper.style.opacity = '0';
        
        setTimeout(() => {
            contentWrapper.style.transform = 'translateY(0)';
            contentWrapper.style.opacity = '1';
        }, 200);
        
        // Анимация при наведении на кнопки
        setTimeout(() => {
            document.querySelectorAll('.btn:not(.btn-disabled)').forEach(button => {
                button.addEventListener('mouseenter', function() {
                    this.style.transform = 'translateY(-2px) scale(1.02)';
                });
                
                button.addEventListener('mouseleave', function() {
                    this.style.transform = 'translateY(0) scale(1)';
                });
            });
        }, 300);
    },

    // Навигация
    navigateTo(url, message) {
        this.showNotification(message, 'info');
        window.location.href = url;
    },

    // Система уведомлений
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'info' ? '#3498db' : type === 'warning' ? '#f39c12' : '#e74c3c'};
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            z-index: 1000;
            font-weight: 500;
            opacity: 0;
            transform: translateX(100px);
            transition: all 0.3s ease;
        `;
        notification.textContent = message;
        document.body.appendChild(notification);

        // Анимация появления
        setTimeout(() => {
            notification.style.opacity = '1';
            notification.style.transform = 'translateX(0)';
        }, 100);

        // Автоматическое скрытие
        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transform = 'translateX(100px)';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
};

// Инициализация при загрузке DOM
document.addEventListener('DOMContentLoaded', () => NexusApp.init());