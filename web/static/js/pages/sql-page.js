/**
 * 🗄️ Модуль страницы SQL запросов (исправленный)
 */
import { $, $$, showNotification } from '../core/utils.js';
import { MonacoEditor } from '../features/monaco-editor.js';

export class SqlPage {
    constructor() {
        this.dbSelect = $('#db-select');
        this.runButton = $('#run-button');
        this.saveButton = $('#save-button');
        this.clearButton = $('#clear-button');
        this.tabButtons = $$('.tab-button');
        this.tabContents = $$('.tab-content');
        this.resultsTable = $('#results-table');
        this.resultsContainer = $('.results-container');
        
        this.monacoEditor = null;
        this.fullResultsData = { columns: [], rows: [] };
        this.databaseOptions = ["ACTUAR2", "Oracle", "PostgreSQL", "adinsure_prod"];
        this.lastQueryResults = null; // Сохраняем последние результаты
        
        this.init();
    }

    async init() {
        
        this.populateDatabaseSelect();
        this.setupTabButtons();
        this.setupPresetQueries();
        this.setupEventListeners();
        
        // Инициализируем Monaco Editor
        await this.initializeMonacoEditor();
        
        this.loadHistory();
        
    }

    async initializeMonacoEditor() {
        try {
            this.monacoEditor = new MonacoEditor('#monaco-editor', {
                language: 'sql',
                value: ''
            });
        } catch (error) {
            showNotification('Ошибка загрузки редактора кода', 'error');
        }
    }

    populateDatabaseSelect() {
        if (!this.dbSelect) return;
        
        this.dbSelect.innerHTML = '';
        
        const defaultOption = document.createElement('option');
        defaultOption.value = "";
        defaultOption.disabled = true;
        defaultOption.selected = true;
        defaultOption.textContent = "Выберите базу данных...";
        this.dbSelect.appendChild(defaultOption);

        this.databaseOptions.forEach(dbName => {
            const option = document.createElement('option');
            option.value = dbName;
            option.textContent = dbName;
            this.dbSelect.appendChild(option);
        });
    }

    setupTabButtons() {
        this.tabButtons.forEach(button => {
            button.addEventListener('click', () => {
                this.switchTab(button.dataset.tab);
            });
        });
    }

    switchTab(tabId) {
        this.tabButtons.forEach(btn => btn.classList.remove('active'));
        this.tabContents.forEach(content => content.style.display = 'none');

        const activeButton = $(`.tab-button[data-tab="${tabId}"]`);
        const activeContent = $(`#${tabId}-tab`);
        
        if (activeButton) activeButton.classList.add('active');
        if (activeContent) activeContent.style.display = 'block';
        
        if (tabId === 'history') {
            this.loadHistory();
        }
    }

    setupPresetQueries() {
        const presetToggle = $('#preset-toggle');
        const presetDropdown = $('#preset-dropdown');
        
        if (presetToggle && presetDropdown) {
            presetToggle.addEventListener('click', () => {
                presetDropdown.classList.toggle('show');
                const icon = presetToggle.querySelector('.fa-chevron-down');
                if (icon) {
                    icon.style.transform = presetDropdown.classList.contains('show') ? 
                        'rotate(180deg)' : 'rotate(0deg)';
                }
            });

            presetDropdown.addEventListener('click', (event) => {
                const target = event.target.closest('.preset-item');
                if (!target) return;

                const query = target.getAttribute('data-query');
                const database = target.getAttribute('data-database');
                
                if (this.monacoEditor) {
                    this.monacoEditor.setValue(query);
                }
                
                if (database && this.dbSelect) {
                    this.dbSelect.value = database;
                }
                
                presetDropdown.classList.remove('show');
                const icon = presetToggle.querySelector('.fa-chevron-down');
                if (icon) icon.style.transform = 'rotate(0deg)';
            });

            // Закрытие при клике вне области
            document.addEventListener('click', (event) => {
                if (!presetToggle.contains(event.target) && !presetDropdown.contains(event.target)) {
                    presetDropdown.classList.remove('show');
                    const icon = presetToggle.querySelector('.fa-chevron-down');
                    if (icon) icon.style.transform = 'rotate(0deg)';
                }
            });
        }
    }

    setupEventListeners() {
        if (this.runButton) {
            this.runButton.addEventListener('click', () => this.executeQuery());
        }

        if (this.saveButton) {
            this.saveButton.addEventListener('click', () => this.saveResults());
        }

        if (this.clearButton) {
            this.clearButton.addEventListener('click', () => this.clearEditor());
        }
    }

    async executeQuery() {
        const sqlQuery = this.monacoEditor?.getValue();
        const selectedDb = this.dbSelect?.value;
        
        if (!sqlQuery?.trim()) {
            this.logMessage("Ошибка: SQL-запрос не предоставлен", "ERROR");
            showNotification("Введите SQL запрос", "error");
            return;
        }

        if (!this.databaseOptions.includes(selectedDb)) {
            this.logMessage("Ошибка: Выбрана некорректная база данных", "ERROR");
            showNotification("Выберите базу данных", "error");
            return;
        }

        const originalText = this.runButton?.innerHTML || 'Выполнить запрос';
        
        try {
            if (this.runButton) {
                this.runButton.disabled = true;
                this.runButton.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Выполняется...';
            }
            
            this.updateExecutionMessage(`Выполнение запроса к ${selectedDb}...`);
            this.logMessage(`Выполняется запрос к базе данных: ${selectedDb}`, "INFO");

            const startTime = Date.now();
            
            const response = await fetch('/sql/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    sql_query: sqlQuery,
                    database: selectedDb
                })
            });

            const executionTime = (Date.now() - startTime) / 1000;

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Ошибка выполнения запроса');
            }

            const data = await response.json();
            this.handleQueryResults(data, selectedDb, executionTime, sqlQuery);

        } catch (error) {
            this.handleQueryError(error);
        } finally {
            if (this.runButton) {
                this.runButton.disabled = false;
                this.runButton.innerHTML = originalText;
            }
        }
    }

    handleQueryResults(data, database, executionTime, query) {
        if (data.error) {
            this.logMessage(`Ошибка: ${data.error}`, "ERROR");
            this.updateExecutionMessage(`Ошибка: ${data.error}`);
            this.clearResultsTable();
            return;
        }

        let columns = [];
        let rows = [];

        // Обработка разных форматов ответа
        if (data.results?.length > 0) {
            const resultSet = data.results[0];
            if (resultSet.columns && resultSet.rows) {
                columns = resultSet.columns;
                rows = resultSet.rows;
            }
        } else if (data.columns && data.rows) {
            columns = data.columns;
            rows = data.rows;
        }

        // Сохраняем результаты
        this.fullResultsData = { columns, rows };
        this.lastQueryResults = {
            database,
            query,
            columns,
            rows,
            executionTime,
            timestamp: new Date().toISOString(),
            rowCount: rows.length
        };

        this.displayResults(columns, rows);
        
        const message = rows.length > 0 ? 
            `${database}: Запрос выполнен успешно - получено ${rows.length} строк` :
            `${database}: Запрос выполнен, данные не получены`;
            
        this.updateExecutionMessage(message, executionTime);
        this.logMessage(`${message} за ${executionTime.toFixed(2)} сек.`, "INFO");
        
        // Активируем кнопку сохранения если есть данные
        if (this.saveButton) {
            this.saveButton.disabled = rows.length === 0;
        }
        
        // Сохраняем в историю с количеством строк
        this.saveQueryToHistory(database, query, rows.length, executionTime);
        this.switchTab('results');
        
        // Показываем уведомление
        if (rows.length > 0) {
            showNotification(`Получено ${rows.length} строк данных`, 'success');
        } else {
            showNotification('Запрос выполнен, но данные не получены', 'info');
        }
    }

    displayResults(columns, rows) {
        if (!this.resultsTable) {
            return;
        }

        this.clearResultsTable();

        // Создаем заголовки
        if (columns && columns.length > 0) {
            const thead = this.resultsTable.querySelector('thead') || this.resultsTable.createTHead();
            thead.innerHTML = '';
            
            const headerRow = thead.insertRow();
            columns.forEach(column => {
                const th = document.createElement('th');
                th.textContent = column;
                headerRow.appendChild(th);
            });
        }

        // Создаем строки данных
        const tbody = this.resultsTable.querySelector('tbody') || this.resultsTable.createTBody();
        tbody.innerHTML = '';

        if (rows && rows.length > 0) {
            // Показываем максимум 25 строк в таблице
            const displayRows = rows.slice(0, 25);
            
            displayRows.forEach((row, index) => {
                const tr = tbody.insertRow();
                tr.classList.add(index % 2 === 0 ? 'even-row' : 'odd-row');
                
                columns.forEach(column => {
                    const td = tr.insertCell();
                    const value = row[column] === null ? 'NULL' : String(row[column] || '');
                    td.textContent = value;
                    if (value === 'NULL') {
                        td.classList.add('null-value');
                        td.style.fontStyle = 'italic';
                        td.style.color = '#999';
                    }
                });
            });

            // Добавляем сообщение о количестве строк
            if (rows.length > 25) {
                const tr = tbody.insertRow();
                const td = tr.insertCell();
                td.colSpan = columns.length;
                td.className = 'text-center p-3 text-muted';
                td.innerHTML = `
                    <i class="fas fa-info-circle me-2"></i>
                    Отображено первых 25 строк из ${rows.length}. 
                    Нажмите "Сохранить результаты", чтобы получить все строки.
                `;
            }
        } else {
            // Нет результатов
            const tr = tbody.insertRow();
            const td = tr.insertCell();
            td.colSpan = columns.length > 0 ? columns.length : 1;
            td.textContent = "Результаты не найдены";
            td.style.textAlign = 'center';
            td.style.padding = '2rem';
            td.style.fontStyle = 'italic';
        }

        // Показываем контейнер результатов
        if (this.resultsContainer) {
            this.resultsContainer.style.display = 'block';
        }
    }

    clearResultsTable() {
        if (this.resultsTable) {
            this.resultsTable.innerHTML = '';
        }
        
        if (this.saveButton) {
            this.saveButton.disabled = true;
        }
    }

    handleQueryError(error) {
        this.logMessage(`Ошибка: ${error.message}`, "ERROR");
        this.updateExecutionMessage(`Ошибка: ${error.message}`);
        showNotification(`Ошибка выполнения запроса: ${error.message}`, 'error');
        this.clearResultsTable();
        this.fullResultsData = { columns: [], rows: [] }; // Очищаем только при ошибке
    }

    updateExecutionMessage(message, time = null) {
        const messageEl = $('#execution-message');
        const timeEl = $('.execution-time');
        
        if (messageEl) messageEl.textContent = message;
        if (timeEl && time !== null) {
            timeEl.textContent = `${time.toFixed(2)} сек`;
        }
    }

    async saveResults() {

        // Используем данные из lastQueryResults если fullResultsData пуст
        const dataToSave = this.fullResultsData.rows?.length > 0 ? 
            this.fullResultsData : 
            this.lastQueryResults;

        if (!dataToSave?.rows?.length) {
            showNotification("Нет данных для сохранения", "warning");
            this.logMessage("Попытка сохранения без данных", "WARNING");
            return;
        }

        const originalText = this.saveButton?.innerHTML || 'Сохранить результаты';
        
        try {
            if (this.saveButton) {
                this.saveButton.disabled = true;
                this.saveButton.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Сохранение...';
            }

            const tableData = [dataToSave.columns, ...dataToSave.rows];
            
            const response = await fetch('/sql/save_excel', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ table_data: tableData })
            });

            if (!response.ok) {
                throw new Error('Ошибка сохранения файла');
            }

            const blob = await response.blob();
            this.downloadFile(blob, 'sql_results.xlsx');
            
            showNotification(`Результаты успешно сохранены (${dataToSave.rows.length} строк)`, "success");

        } catch (error) {
            this.logMessage(`Ошибка сохранения: ${error.message}`, "ERROR");
            showNotification("Ошибка при сохранении файла", "error");
        } finally {
            if (this.saveButton) {
                this.saveButton.disabled = false;
                this.saveButton.innerHTML = originalText;
            }
        }
    }

    downloadFile(blob, filename) {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    }

    clearEditor() {
        if (this.monacoEditor) {
            this.monacoEditor.setValue('');
        }
        this.logMessage("Редактор очищен", "INFO");
    }

    logMessage(message, type = "INFO") {
        const logOutput = $('#log-output');
        if (!logOutput) return;

        const paragraph = document.createElement('p');
        paragraph.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
        paragraph.classList.add('log-message', `log-${type.toLowerCase()}`);

        // Стили для разных типов сообщений
        switch (type) {
            case 'ERROR':
                paragraph.style.color = '#dc3545';
                break;
            case 'WARNING':
                paragraph.style.color = '#ffc107';
                break;
            case 'INFO':
                paragraph.style.color = '#17a2b8';
                break;
        }

        logOutput.prepend(paragraph);
        
        // Ограничиваем количество сообщений
        while (logOutput.children.length > 10) {
            logOutput.removeChild(logOutput.lastChild);
        }

        const logArea = $('.log-area');
        if (logArea) logArea.classList.add('has-content');
    }

    saveQueryToHistory(database, query, rowCount = 0, executionTime = 0) {
        const history = JSON.parse(localStorage.getItem('sql_query_history')) || [];
        const timestamp = new Date().toISOString();
        
        const historyItem = { 
            database, 
            query, 
            timestamp,
            rowCount,
            executionTime: executionTime.toFixed(2)
        };
        
        history.unshift(historyItem);
        
        if (history.length > 20) {
            history.pop();
        }
        
        localStorage.setItem('sql_query_history', JSON.stringify(history));
    }

    loadHistory() {
        const historyList = $('#history-list');
        if (!historyList) return;

        const history = JSON.parse(localStorage.getItem('sql_query_history')) || [];

        if (history.length === 0) {
            historyList.innerHTML = `
                <div class="text-center p-4">
                    <i class="fas fa-history fa-3x text-muted mb-3"></i>
                    <h5>История запросов пуста</h5>
                    <p class="text-muted">Выполненные запросы будут отображаться здесь</p>
                </div>
            `;
            return;
        }

        historyList.innerHTML = '';
        
        history.forEach(item => {
            const historyItem = this.createHistoryItem(item);
            historyList.appendChild(historyItem);
        });
    }

    createHistoryItem(item) {
        const historyItem = document.createElement('div');
        historyItem.classList.add('history-item');

        // Форматируем время выполнения и количество строк
        const stats = [];
        if (item.rowCount !== undefined) {
            stats.push(`${item.rowCount} строк`);
        }
        if (item.executionTime !== undefined) {
            stats.push(`${item.executionTime} сек`);
        }
        const statsText = stats.length > 0 ? ` • ${stats.join(' • ')}` : '';

        historyItem.innerHTML = `
            <div class="history-item-database">${item.database}</div>
            <div class="history-item-query">${item.query.substring(0, 100)}${item.query.length > 100 ? '...' : ''}</div>
            <div class="history-item-time">
                <i class="far fa-clock"></i> ${this.timeAgoFromISO(item.timestamp)}${statsText}
            </div>
        `;

        // Добавляем стили для лучшего вида
        historyItem.style.cssText = `
            padding: 12px 16px;
            margin-bottom: 8px;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s ease;
            background: #fff;
        `;

        historyItem.addEventListener('mouseenter', () => {
            historyItem.style.backgroundColor = '#f8f9fa';
            historyItem.style.borderColor = '#dee2e6';
            historyItem.style.transform = 'translateY(-1px)';
            historyItem.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)';
        });

        historyItem.addEventListener('mouseleave', () => {
            historyItem.style.backgroundColor = '#fff';
            historyItem.style.borderColor = '#e9ecef';
            historyItem.style.transform = 'translateY(0)';
            historyItem.style.boxShadow = 'none';
        });

        historyItem.addEventListener('click', () => {
            if (this.dbSelect) this.dbSelect.value = item.database;
            if (this.monacoEditor) this.monacoEditor.setValue(item.query);
            this.switchTab('editor');
            showNotification(`Запрос загружен из истории (${item.rowCount || 0} строк)`, 'info');
        });

        return historyItem;
    }

    timeAgoFromISO(isoTimestamp) {
        const now = new Date();
        const then = new Date(isoTimestamp);
        const diff = now.getTime() - then.getTime();
        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);

        if (days > 0) {
            return `${days} ${days === 1 ? 'день' : days < 5 ? 'дня' : 'дней'} назад`;
        } else if (hours > 0) {
            return `${hours} ${hours === 1 ? 'час' : hours < 5 ? 'часа' : 'часов'} назад`;
        } else if (minutes > 0) {
            return `${minutes} ${minutes === 1 ? 'минута' : minutes < 5 ? 'минуты' : 'минут'} назад`;
        } else {
            return `${seconds} ${seconds === 1 ? 'секунда' : 'секунды'} назад`;
        }
    }

    // Методы для отладки
    getStatus() {
        return {
            monacoReady: !!this.monacoEditor,
            tableFound: !!this.resultsTable,
            hasResults: this.fullResultsData.rows.length > 0,
            hasLastQueryResults: !!this.lastQueryResults?.rows?.length,
            selectedDatabase: this.dbSelect?.value,
            saveButtonEnabled: !this.saveButton?.disabled
        };
    }

    // Метод для принудительного включения кнопки сохранения (для отладки)
    enableSaveButton() {
        if (this.saveButton) {
            this.saveButton.disabled = false;
        }
    }
}