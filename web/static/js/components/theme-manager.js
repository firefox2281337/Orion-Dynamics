/**
 * 🌙 Менеджер тем
 */
import { $, showNotification } from '../core/utils.js';
import { CSS_VARIABLES, MONACO_THEMES } from '../core/config.js';

export class ThemeManager {
    constructor() {
        this.darkModeToggle = $('#darkModeToggle');
        this.currentTheme = this.getStoredTheme();
        this.init();
    }

    init() {
        this.applyStoredTheme();
        this.setupEventListeners();
    }

    setupEventListeners() {
        if (this.darkModeToggle) {
            this.darkModeToggle.addEventListener('click', () => this.toggleTheme());
        }
    }

    getStoredTheme() {
        return localStorage.getItem('darkMode') === 'true' ? 'dark' : 'light';
    }

    toggleTheme() {
        this.currentTheme = this.currentTheme === 'dark' ? 'light' : 'dark';
        this.applyTheme(this.currentTheme);
        this.saveTheme();
        this.updateMonacoTheme();
        
        showNotification(`Тема изменена на ${this.currentTheme === 'dark' ? 'тёмную' : 'светлую'}`, 'success');
    }

    applyStoredTheme() {
        if (this.currentTheme === 'dark') {
            this.applyTheme('dark');
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

    applyDarkStyles() {
        const variables = CSS_VARIABLES.dark;
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
        const variables = CSS_VARIABLES.light;
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
            const theme = MONACO_THEMES[this.currentTheme];
            monaco.editor.setTheme(theme);
            
            const editors = monaco.editor.getEditors();
            editors.forEach(() => monaco.editor.setTheme(theme));
        }
    }

    saveTheme() {
        localStorage.setItem('darkMode', this.currentTheme === 'dark');
    }

    getCurrentTheme() {
        return this.currentTheme;
    }
}