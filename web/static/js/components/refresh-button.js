/**
 * 🔄 Компонент кнопки обновления
 */
import { $ } from '../core/utils.js';

export class RefreshButton {
    constructor() {
        this.button = $('#refreshButton');
        this.init();
    }

    init() {
        if (this.button) {
            this.setupEventListener();
        }
    }

    setupEventListener() {
        this.button.addEventListener('click', () => this.handleRefresh());
    }

    async handleRefresh() {
        const icon = this.button.querySelector('i');
        
        // Добавляем анимацию
        icon.classList.add('spin');
        this.button.disabled = true;

        // Имитируем загрузку
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Обновляем страницу
        window.location.reload();
    }
}