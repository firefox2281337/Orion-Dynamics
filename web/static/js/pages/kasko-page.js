/**
 * 🚗 Модуль страницы КАСКО
 */
import { $, showNotification, createElement } from '../core/utils.js';
import { Loader } from '../components/loader.js';

export class KaskoPage {
    constructor() {
        this.form = $('form[method="POST"]');
        this.loader = new Loader('loaderWrapper');
        this.selectAllCheckbox = $('#selectAllCheckboxes');
        this.checkboxes = document.querySelectorAll('input[name="checkboxes"]');
        this.submitButton = this.form?.querySelector('button[type="submit"]');
        
        this.init();
    }

    init() {
        if (!this.form) return;
        
        this.setupSelectAll();
        this.setupFormSubmission();
        this.animateCheckboxes();
    }

    setupSelectAll() {
        if (!this.selectAllCheckbox) return;

        this.selectAllCheckbox.addEventListener('change', () => {
            const isChecked = this.selectAllCheckbox.checked;
            
            this.checkboxes.forEach((checkbox, index) => {
                setTimeout(() => {
                    checkbox.checked = isChecked;
                    this.animateCheckbox(checkbox.parentElement);
                }, index * 10);
            });
        });

        // Обновление состояния "Выбрать все"
        this.checkboxes.forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                const allChecked = Array.from(this.checkboxes).every(cb => cb.checked);
                const noneChecked = Array.from(this.checkboxes).every(cb => !cb.checked);
                
                this.selectAllCheckbox.checked = allChecked;
                this.selectAllCheckbox.indeterminate = !allChecked && !noneChecked;
            });
        });
    }

    animateCheckbox(element) {
        element.style.transform = 'scale(1.05)';
        setTimeout(() => {
            element.style.transform = 'scale(1)';
        }, 100);
    }

    setupFormSubmission() {
        this.form.addEventListener('submit', async (event) => {
            event.preventDefault();
            await this.handleFormSubmit();
        });
    }

    async handleFormSubmit() {
        const formData = new FormData(this.form);
        const originalText = this.submitButton.innerHTML;
        
        try {
            // Блокируем кнопку
            this.submitButton.disabled = true;
            this.submitButton.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Генерация отчёта...';
            
            // Показываем loader
            this.loader.show('Генерируется отчёт...');

            const response = await fetch('/processing/kasko', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Ошибка сети');
            }

            const blob = await response.blob();
            this.downloadFile(blob, this.generateFileName());
            
            showNotification('Отчёт успешно сгенерирован!', 'success');

        } catch (error) {
            showNotification(`Ошибка генерации отчёта: ${error.message}`, 'error');
        } finally {
            this.submitButton.disabled = false;
            this.submitButton.innerHTML = originalText;
            this.loader.hide();
        }
    }

    downloadFile(blob, filename) {
        const url = window.URL.createObjectURL(blob);
        const a = createElement('a');
        a.href = url;
        a.download = filename;
        
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
    }

    generateFileName() {
        const quarter = $('#quarter')?.value || '1';
        const year = $('#year')?.value || new Date().getFullYear();
        return `otchet_kasko_${quarter}_kv_${year}.xlsx`;
    }

    animateCheckboxes() {
        const checkboxContainers = document.querySelectorAll('.form-check');
        checkboxContainers.forEach((container, index) => {
            container.style.opacity = '0';
            container.style.transform = 'translateY(20px)';
            
            setTimeout(() => {
                container.style.transition = 'all 0.3s ease';
                container.style.opacity = '1';
                container.style.transform = 'translateY(0)';
            }, index * 20);
        });
    }
}