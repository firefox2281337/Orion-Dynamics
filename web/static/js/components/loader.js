/**
 * ⏳ Компонент загрузчика
 */
import { $ } from '../core/utils.js';

export class Loader {
    constructor(wrapperId) {
        this.wrapper = $(`#${wrapperId}`);
        this.textElement = this.wrapper?.querySelector('.loader-text');
    }

    show(text = 'Загрузка...') {
        if (!this.wrapper) return;
        
        if (this.textElement) {
            this.textElement.textContent = text;
        }
        
        this.wrapper.style.display = 'flex';
        setTimeout(() => {
            this.wrapper.style.opacity = '1';
        }, 10);
    }

    hide() {
        if (!this.wrapper) return;
        
        this.wrapper.style.opacity = '0';
        setTimeout(() => {
            this.wrapper.style.display = 'none';
        }, 300);
    }

    updateText(text) {
        if (this.textElement) {
            this.textElement.textContent = text;
        }
    }
}