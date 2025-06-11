/**
 * 📊 Компонент таблицы данных (исправленный)
 */
import { $ } from '../core/utils.js';

export class DataTable {
    constructor(containerId) {
        this.container = typeof containerId === 'string' ? 
            $(containerId) : containerId;
        this.table = null;
        this.thead = null;
        this.tbody = null;
        
        this.init();
    }

    init() {
        if (!this.container) {
            return;
        }

        // Ищем таблицу в контейнере или создаем
        this.table = this.container.querySelector('table');
        if (!this.table) {
            this.createTable();
        }

        this.thead = this.table.querySelector('thead');
        this.tbody = this.table.querySelector('tbody');
        
        if (!this.thead) {
            this.thead = this.table.createTHead();
        }
        
        if (!this.tbody) {
            this.tbody = this.table.createTBody();
        }
    }

    createTable() {
        this.table = document.createElement('table');
        this.table.className = 'table table-striped table-hover';
        this.container.appendChild(this.table);
    }

    displayResults(columns, rows) {
        if (!this.table) {
            return;
        }
        
        this.clearTable();
        this.createHeaders(columns);
        this.createRows(columns, rows);
        this.show();
    }

    displayLimitedResults(columns, rows, maxRows = 25) {
        if (!this.table) {
            return;
        }
        
        this.clearTable();
        this.createHeaders(columns);
        
        const displayRows = rows.slice(0, maxRows);
        this.createRows(columns, displayRows);
        
        if (rows.length > maxRows) {
            this.addMoreRowsMessage(columns.length, rows.length, maxRows);
        }
        
        this.show();
    }

    clearTable() {
        if (this.thead) this.thead.innerHTML = '';
        if (this.tbody) this.tbody.innerHTML = '';
    }

    createHeaders(columns) {
        if (!this.thead || !columns?.length) return;
        
        const headerRow = this.thead.insertRow();
        columns.forEach(column => {
            const th = document.createElement('th');
            th.textContent = column;
            th.style.backgroundColor = '#f8f9fa';
            th.style.fontWeight = '600';
            th.style.borderBottom = '2px solid #dee2e6';
            headerRow.appendChild(th);
        });
    }

    createRows(columns, rows) {
        if (!this.tbody) return;
        
        if (!rows?.length) {
            this.showNoResults(columns?.length || 1);
            return;
        }
        
        rows.forEach((row, index) => {
            const tr = this.tbody.insertRow();
            tr.classList.add(index % 2 === 0 ? 'even-row' : 'odd-row');
            
            columns.forEach(column => {
                const td = tr.insertCell();
                const value = row[column] === null ? 'NULL' : String(row[column] || '');
                td.textContent = value;
                
                if (value === 'NULL') {
                    td.classList.add('null-value');
                    td.style.fontStyle = 'italic';
                    td.style.color = '#6c757d';
                }
                
                // Добавляем отступы для лучшего вида
                td.style.padding = '12px 8px';
                td.style.borderBottom = '1px solid #dee2e6';
            });
        });
    }

    showNoResults(colSpan = 1) {
        if (!this.tbody) return;
        
        const tr = this.tbody.insertRow();
        const td = tr.insertCell();
        td.textContent = "Результаты не найдены";
        td.colSpan = colSpan;
        td.style.textAlign = 'center';
        td.style.padding = '3rem';
        td.style.fontStyle = 'italic';
        td.style.color = '#6c757d';
        td.style.backgroundColor = '#f8f9fa';
    }

    addMoreRowsMessage(colSpan, totalRows, displayedRows) {
        if (!this.tbody) return;
        
        const tr = this.tbody.insertRow();
        const td = tr.insertCell();
        td.colSpan = colSpan;
        td.className = 'text-center p-3 text-muted';
        td.style.backgroundColor = '#e9ecef';
        td.style.borderTop = '2px solid #dee2e6';
        td.innerHTML = `
            <i class="fas fa-info-circle me-2"></i>
            Отображено первых ${displayedRows} строк из ${totalRows}. 
            Нажмите "Скачать отчёт", чтобы получить все строки.
        `;
    }

    show() {
        if (this.container) {
            this.container.style.display = 'block';
        }
    }

    hide() {
        if (this.container) {
            this.container.style.display = 'none';
        }
    }

    // Новый метод для отображения без результатов
    showNoResults() {
        this.clearTable();
        this.showNoResults(1);
        this.show();
    }
}