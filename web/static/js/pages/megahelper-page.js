/**
 * 👁️ Модуль страницы DataVision (исправленный с таймаутом)
 */
import { $, showNotification } from '../core/utils.js';
import { MultiSelect } from '../components/multi-select.js';
import { Loader } from '../components/loader.js';
import { DataTable } from '../features/data-table.js';

export class MegahelperPage {
    constructor() {
        this.form = $('#dataForm');
        this.loader = new Loader('loaderWrapper');
        this.dataTable = new DataTable('#resultsContainer');
        this.fullResultsData = { columns: [], rows: [] };
        this.MAX_ROWS_TO_DISPLAY = 5;
        this.jQueryReady = false;
        this.useNativeDatePickers = false;
        
        this.init();
    }

    async init() {
        if (!this.form) return;
        
        
        // Проверяем jQuery с таймаутом
        await this.checkJQueryAvailability();
        
        this.initializeDatePickers();
        this.initializeMultiSelects();
        this.setupEventListeners();
        
    }

    async checkJQueryAvailability() {
        const maxWaitTime = 3000; // 3 секунды максимум
        const checkInterval = 100; // проверяем каждые 100мс
        let waitedTime = 0;

        return new Promise((resolve) => {
            const checkJQuery = () => {
                // Проверяем разные варианты jQuery
                const hasGlobalJQuery = typeof window.jQuery !== 'undefined' && window.jQuery.fn && window.jQuery.fn.datepicker;
                const hasGlobalDollar = typeof window.$ !== 'undefined' && window.$ !== $ && window.$.fn && window.$.fn.datepicker;
                
                if (hasGlobalJQuery || hasGlobalDollar) {
                    this.jQueryReady = true;
                    resolve();
                    return;
                }

                waitedTime += checkInterval;
                
                if (waitedTime >= maxWaitTime) {
                    this.useNativeDatePickers = true;
                    resolve();
                    return;
                }

                setTimeout(checkJQuery, checkInterval);
            };
            
            checkJQuery();
        });
    }

    initializeDatePickers() {
        const startDateEl = document.getElementById('startDate');
        const endDateEl = document.getElementById('endDate');
        
        if (!startDateEl || !endDateEl) {
            return;
        }

        // Если jQuery не готов или мы решили использовать нативные поля
        if (this.useNativeDatePickers || !this.jQueryReady) {
            this.setupNativeDatePickers(startDateEl, endDateEl);
            return;
        }

        // Пытаемся инициализировать jQuery UI datepicker
        try {
            // Используем глобальный jQuery если доступен
            const jq = window.jQuery || window.$;
            
            if (jq && jq.fn && jq.fn.datepicker) {
                jq("#startDate, #endDate").datepicker({
                    dateFormat: 'yy-mm-dd',
                    showAnim: "slideDown",
                    changeMonth: true,
                    changeYear: true,
                    yearRange: "-10:+2",
                    maxDate: new Date(),
                    onSelect: function(dateText, inst) {
                    }
                });
                
                return;
            }
        } catch (error) {
        }

        // Fallback к нативным полям
        this.setupNativeDatePickers(startDateEl, endDateEl);
    }

    setupNativeDatePickers(startDateEl, endDateEl) {
        
        // Настраиваем нативные поля
        startDateEl.type = 'date';
        endDateEl.type = 'date';
        
        // Убираем placeholder'ы
        startDateEl.placeholder = '';
        endDateEl.placeholder = '';
        
        // Устанавливаем разумные ограничения
        const today = new Date();
        const tenYearsAgo = new Date(today.getFullYear() - 10, today.getMonth(), today.getDate());
        const twoYearsForward = new Date(today.getFullYear() + 2, today.getMonth(), today.getDate());
        
        startDateEl.min = this.formatDateForInput(tenYearsAgo);
        startDateEl.max = this.formatDateForInput(twoYearsForward);
        endDateEl.min = this.formatDateForInput(tenYearsAgo);
        endDateEl.max = this.formatDateForInput(twoYearsForward);
        
        // Добавляем обработчики для синхронизации дат
        startDateEl.addEventListener('change', () => {
            if (startDateEl.value && endDateEl.value && startDateEl.value > endDateEl.value) {
                endDateEl.value = startDateEl.value;
            }
            endDateEl.min = startDateEl.value || this.formatDateForInput(tenYearsAgo);
        });
        
        endDateEl.addEventListener('change', () => {
            if (startDateEl.value && endDateEl.value && endDateEl.value < startDateEl.value) {
                startDateEl.value = endDateEl.value;
            }
            startDateEl.max = endDateEl.value || this.formatDateForInput(twoYearsForward);
        });
        
    }

    formatDateForInput(date) {
        return date.toISOString().split('T')[0];
    }

    initializeMultiSelects() {
        try {
            this.insuranceTypeSelect = new MultiSelect('insuranceTypeButton', 'insuranceTypeDropdown');
            this.channelSelect = new MultiSelect('channelButton', 'channelDropdown');
            this.branchSelect = new MultiSelect('branchCodeButton', 'branchCodeDropdown');
        } catch (error) {
        }
    }

    setupEventListeners() {
        const generateButton = $('#generateReport');
        const downloadButton = $('#downloadButton');

        if (generateButton) {
            generateButton.addEventListener('click', () => this.generateReport());
        }

        if (downloadButton) {
            downloadButton.addEventListener('click', () => this.downloadResults());
        }
    }

    async generateReport() {
        const generateButton = $('#generateReport');
        const downloadButton = $('#downloadButton');
        const originalText = generateButton?.innerHTML || 'Генерировать отчёт';
        
        // Скрываем предыдущие результаты
        this.dataTable.hide();
        if (downloadButton) downloadButton.style.display = 'none';

        try {
            if (generateButton) {
                generateButton.disabled = true;
                generateButton.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Генерация...';
            }
            
            this.loader.show('Генерируется отчёт...');

            const formData = this.collectFormData();
            
            const response = await fetch('/api/get_data', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data?.columns && data?.rows && data.rows.length > 0) {
                this.fullResultsData = { columns: data.columns, rows: data.rows };
                this.dataTable.displayLimitedResults(
                    this.fullResultsData.columns, 
                    this.fullResultsData.rows,
                    this.MAX_ROWS_TO_DISPLAY
                );
                
                if (downloadButton) downloadButton.style.display = 'inline-flex';
                showNotification(`Получено ${data.rows.length} строк данных`, 'success');
            } else {
                this.dataTable.showNoResults();
                showNotification('Данные не найдены', 'warning');
            }

        } catch (error) {
            showNotification('Ошибка при получении данных', 'error');
        } finally {
            if (generateButton) {
                generateButton.disabled = false;
                generateButton.innerHTML = originalText;
            }
            this.loader.hide();
        }
    }

    collectFormData() {
        const formData = new FormData(this.form);
        
        // Обработка мульти-селектов
        const multiSelects = ['insurance_type', 'channel', 'branch_code'];
        multiSelects.forEach(name => {
            const values = Array.from(
                this.form.querySelectorAll(`input[name="${name}"]:checked:not([id$="All"])`)
            ).map(el => el.value);
            formData.set(name, values.join(', '));
        });

        return formData;
    }

    async downloadResults() {
        if (!this.fullResultsData.rows || this.fullResultsData.rows.length === 0) {
            showNotification('Нет данных для скачивания.', 'warning');
            return;
        }

        const tableData = [this.fullResultsData.columns, ...this.fullResultsData.rows];

        try {
            const response = await fetch('/sql/save_excel', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ table_data: tableData })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const blob = await response.blob();
            this.downloadFile(blob, 'datavision_results.xlsx');
            showNotification('Отчёт успешно скачан!', 'success');

        } catch (error) {
            showNotification('Ошибка скачивания Excel', 'error');
        }
    }

    downloadFile(blob, filename) {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
    }

    // Публичные методы для отладки
    getDatePickerStatus() {
        return {
            jQueryReady: this.jQueryReady,
            useNativeDatePickers: this.useNativeDatePickers,
            hasGlobalJQuery: typeof window.jQuery !== 'undefined',
            hasGlobalDollar: typeof window.$ !== 'undefined',
            hasDatepicker: !!(window.jQuery?.fn?.datepicker || window.$?.fn?.datepicker),
            startDateType: document.getElementById('startDate')?.type,
            endDateType: document.getElementById('endDate')?.type
        };
    }

    switchToNativeDatePickers() {
        this.useNativeDatePickers = true;
        this.initializeDatePickers();
    }

    retryJQueryDatePickers() {
        this.jQueryReady = false;
        this.useNativeDatePickers = false;
        this.checkJQueryAvailability().then(() => {
            this.initializeDatePickers();
        });
    }
}