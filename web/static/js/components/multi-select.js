/**
 * 🔽 Компонент мульти-селекта
 */
import { $ } from '../core/utils.js';

export class MultiSelect {
    constructor(buttonId, dropdownId) {
        this.button = $(`#${buttonId}`);
        this.dropdown = $(`#${dropdownId}`);
        this.checkboxes = this.dropdown?.querySelectorAll('input[type="checkbox"]') || [];
        this.allCheckbox = this.dropdown?.querySelector('input[id$="All"]');
        this.regularCheckboxes = Array.from(this.checkboxes).filter(cb => !cb.id.endsWith('All'));
        
        this.init();
    }

    init() {
        if (!this.button || !this.dropdown) return;
        
        this.setupEventListeners();
        this.updateButtonText();
    }

    setupEventListeners() {
        // Открытие/закрытие dropdown
        this.button.addEventListener('click', (e) => {
            this.closeOtherDropdowns();
            this.dropdown.classList.toggle('show');
            this.button.classList.toggle('open');
            e.stopPropagation();
        });

        // Закрытие при клике вне области
        document.addEventListener('click', (e) => {
            if (!this.dropdown.contains(e.target) && !this.button.contains(e.target)) {
                this.dropdown.classList.remove('show');
                this.button.classList.remove('open');
            }
        });

        // Обновление текста кнопки при изменении чекбоксов
        this.checkboxes.forEach(checkbox => {
            checkbox.addEventListener('change', () => this.updateButtonText());
        });

        // Обработка "Выбрать все"
        if (this.allCheckbox) {
            this.allCheckbox.addEventListener('change', () => {
                this.regularCheckboxes.forEach(checkbox => {
                    checkbox.checked = this.allCheckbox.checked;
                });
                this.updateButtonText();
            });

            this.regularCheckboxes.forEach(checkbox => {
                checkbox.addEventListener('change', () => {
                    const allChecked = this.regularCheckboxes.every(cb => cb.checked);
                    this.allCheckbox.checked = allChecked;
                    this.updateButtonText();
                });
            });
        }
    }

    closeOtherDropdowns() {
        const allDropdowns = document.querySelectorAll('.multi-select-dropdown');
        allDropdowns.forEach(dropdown => {
            if (dropdown !== this.dropdown && dropdown.classList.contains('show')) {
                dropdown.classList.remove('show');
                dropdown.previousElementSibling?.classList.remove('open');
            }
        });
    }

    updateButtonText() {
        const selectedLabels = Array.from(this.regularCheckboxes)
            .filter(cb => cb.checked)
            .map(cb => cb.parentElement.textContent.trim());
            
        this.button.textContent = selectedLabels.length > 0 ? 
            selectedLabels.join(', ') : 
            'Выберите значения';
    }

    getSelectedValues() {
        return this.regularCheckboxes
            .filter(cb => cb.checked)
            .map(cb => cb.value);
    }

    selectAll() {
        this.regularCheckboxes.forEach(cb => cb.checked = true);
        if (this.allCheckbox) this.allCheckbox.checked = true;
        this.updateButtonText();
    }

    deselectAll() {
        this.checkboxes.forEach(cb => cb.checked = false);
        this.updateButtonText();
    }
}