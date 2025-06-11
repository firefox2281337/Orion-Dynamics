/**
 * Основное приложение Автоежедневок
 * Единый JavaScript файл для всех типов автоежедневок
 */

const AutoDailyesApp = {
    // Состояние приложения
    state: {
        selectedFiles: [],
        processingCancelled: false,
        statusCheckInterval: null,
        config: null
    },

    // Инициализация приложения
    init() {
        this.loadConfig();
        this.loadUITheme();
        this.setupDragAndDrop();
        this.setupModalCloseOnOutsideClick();
        this.updateFileDisplay();
        this.updateExecuteButton();
    },

    // Загрузка конфигурации
    loadConfig() {
        if (window.autodailyesConfig) {
            this.state.config = window.autodailyesConfig;
        }
    },

    // Переключение темной темы
    toggleDarkMode() {
        const body = document.body;
        const isDark = body.classList.contains('dark-mode');

        if (isDark) {
            body.classList.remove('dark-mode');
            localStorage.setItem('theme', 'light');
        } else {
            body.classList.add('dark-mode');
            localStorage.setItem('theme', 'dark');
        }

        this.showToast('Тема изменена', 'Оформление интерфейса обновлено', 'info');
    },

    // Загрузка сохранённой темы
    loadUITheme() {
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'dark') {
            document.body.classList.add('dark-mode');
        }
    },

    // === РАБОТА С ФАЙЛАМИ ===

    // Выбор файлов
    selectFiles() {
        const input = document.createElement('input');
        input.type = 'file';
        input.multiple = this.state.config.multiple;
        input.accept = '.xls,.xlsx';
        input.onchange = (e) => {
            this.handleFiles(Array.from(e.target.files));
        };
        input.click();
    },

    // Обработка выбранных файлов
    handleFiles(files) {
        const validFiles = files.filter(file => 
            file.name.endsWith('.xls') || file.name.endsWith('.xlsx')
        );

        if (this.state.config.multiple) {
            // Для множественных файлов - добавляем к существующим
            validFiles.forEach(file => {
                if (!this.state.selectedFiles.some(f => f.name === file.name)) {
                    this.state.selectedFiles.push(file);
                }
            });
        } else {
            // Для одиночного файла - заменяем
            if (validFiles.length > 0) {
                this.state.selectedFiles = [validFiles[0]];
            }
        }

        this.updateFileDisplay();
        this.updateExecuteButton();
    },

    // Обновление отображения файлов
    updateFileDisplay() {
        const fileList = document.getElementById('fileList');
        const fileStatus = document.getElementById('fileStatus');
        const uploadText = document.getElementById('uploadText');

        if (this.state.selectedFiles.length === 0) {
            fileList.innerHTML = '';
            fileStatus.innerHTML = `<i class="fas fa-info-circle"></i><span>${this.state.config.statusTexts.empty}</span>`;
            fileStatus.className = 'file-status';
            uploadText.innerHTML = this.state.config.dragDropText;
            return;
        }

        const fileCount = this.state.selectedFiles.length;
        const statusText = this.state.config.multiple ? 
            `Файлов выбрано: ${fileCount}` : 
            'Файл выбран';

        fileStatus.innerHTML = `<i class="fas fa-check-circle"></i><span>${statusText}</span>`;
        fileStatus.className = 'file-status success';
        uploadText.textContent = this.state.config.multiple ? 
            `Файлов выбрано: ${fileCount}` : 
            `Файл выбран: ${this.state.selectedFiles[0].name}`;

        fileList.innerHTML = this.state.selectedFiles.map((file, index) => `
            <li class="file-item">
                <div class="file-info">
                    <i class="fas fa-file-excel"></i>
                    <div>
                        <div class="file-name">${file.name}</div>
                        <div class="file-type">${this.getFileType(file.name)}</div>
                    </div>
                </div>
                <button class="remove-file" onclick="AutoDailyesApp.removeFile(${index})">
                    <i class="fas fa-times"></i>
                </button>
            </li>
        `).join('');
    },

    // Определение типа файла
    getFileType(fileName) {
        for (const rule of this.state.config.fileRules) {
            if (fileName.startsWith(rule.prefix)) {
                return rule.type;
            }
        }
        return 'Excel';
    },

    // Удаление файла
    removeFile(index) {
        this.state.selectedFiles.splice(index, 1);
        this.updateFileDisplay();
        this.updateExecuteButton();
    },

    // Очистка всех файлов
    clearFiles() {
        this.state.selectedFiles = [];
        this.updateFileDisplay();
        this.updateExecuteButton();
    },

    // Обновление состояния кнопки выполнения
    updateExecuteButton() {
        const executeButton = document.getElementById('executeButton');
        const isValid = this.validateFiles();
        executeButton.disabled = !isValid;
    },

    // Валидация файлов
    validateFiles() {
        if (this.state.selectedFiles.length < this.state.config.minFiles) {
            return false;
        }

        // Проверяем обязательные файлы
        for (const rule of this.state.config.fileRules) {
            if (rule.required) {
                const hasFile = this.state.selectedFiles.some(f => f.name.startsWith(rule.prefix));
                if (!hasFile) {
                    return false;
                }
            }
        }

        return true;
    },

    // === ВЫПОЛНЕНИЕ ЗАДАЧИ ===

    // Выполнение задачи
    async executeTask() {
        // Валидация
        const validation = this.performValidation();
        if (!validation.valid) {
            this.showToast(validation.error, '', 'error');
            return;
        }

        try {
            await this.startProcessing();
        } catch (error) {
            this.showToast('Ошибка обработки', error.message, 'error');
        }
    },

    // Детальная валидация
    performValidation() {
        if (this.state.selectedFiles.length < this.state.config.minFiles) {
            const message = this.state.config.multiple ? 
                `Необходимо выбрать минимум ${this.state.config.minFiles} файла` :
                'Необходимо выбрать файл';
            return { valid: false, error: message };
        }

        // Проверяем каждое обязательное правило
        for (const rule of this.state.config.fileRules) {
            if (rule.required) {
                const hasFile = this.state.selectedFiles.some(f => f.name.startsWith(rule.prefix));
                if (!hasFile) {
                    return { 
                        valid: false, 
                        error: `Не найден файл ${rule.type} (должен начинаться с "${rule.prefix}")` 
                    };
                }
            }
        }

        return { valid: true };
    },

    // Запуск обработки
    async startProcessing() {
        this.state.processingCancelled = false;
        
        document.getElementById('progress-modal').style.display = 'flex';
        document.getElementById('progress-modal').classList.add('show');

        // Создаем FormData для отправки файлов
        const formData = new FormData();
        if (this.state.config.multiple) {
            this.state.selectedFiles.forEach(file => {
                formData.append('files', file);
            });
        } else {
            formData.append('file', this.state.selectedFiles[0]);
        }

        try {
            // Отправляем запрос на обработку
            const response = await fetch(this.state.config.apiEndpoints.process, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Ошибка сервера');
            }

            // Начинаем отслеживание статуса
            this.startStatusTracking();

        } catch (error) {
            document.getElementById('progress-modal').style.display = 'none';
            throw error;
        }
    },

    // Отслеживание статуса обработки
    startStatusTracking() {
        this.state.statusCheckInterval = setInterval(async () => {
            try {
                const response = await fetch(this.state.config.apiEndpoints.status);
                const status = await response.json();

                document.getElementById('progress-step').textContent = status.status;
                document.getElementById('progress-percentage').textContent = status.progress + '%';
                document.getElementById('progress-bar-fill').style.width = status.progress + '%';

                if (!status.is_running) {
                    clearInterval(this.state.statusCheckInterval);

                    if (status.error) {
                        this.showToast('Ошибка обработки', status.error, 'error');
                        document.getElementById('progress-modal').style.display = 'none';
                    } else if (status.has_result) {
                        document.getElementById('progress-step').textContent = 'Успешно выполнено!';
                        document.getElementById('progress-percentage').textContent = '100%';
                        document.getElementById('progress-bar-fill').style.width = '100%';

                        // Скачиваем файл автоматически
                        await this.downloadResult();

                        // Закрываем модалку
                        document.getElementById('progress-modal').style.display = 'none';

                        this.showToast('Файл скачан', '', 'success');
                    }
                }
            } catch (error) {
                console.error('Ошибка получения статуса:', error);
                clearInterval(this.state.statusCheckInterval);
            }
        }, 1000);
    },

    // Скачивание результата
    async downloadResult() {
        try {
            const response = await fetch(this.state.config.apiEndpoints.download);
            
            if (!response.ok) {
                throw new Error('Ошибка скачивания файла');
            }

            // Создаем ссылку для скачивания
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = this.generateFileName();
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            // Закрываем модальное окно
            document.getElementById('progress-modal').style.display = 'none';
            this.showToast('Файл скачан', '', 'success');

        } catch (error) {
            this.showToast('Ошибка скачивания', error.message, 'error');
        }
    },

    // Генерация имени файла для скачивания
    generateFileName() {
        const date = new Date().toLocaleDateString('ru-RU');
        return `${this.state.config.downloadPrefix}_${date}.xlsx`;
    },

    // Отмена обработки
    async cancelProcessing() {
        // Если это кнопка "Скачать", выполняем скачивание
        if (document.getElementById('cancelButton').textContent.includes('Скачать')) {
            await this.downloadResult();
            return;
        }

        // Если это кнопка "Закрыть", просто закрываем
        if (document.getElementById('cancelButton').textContent.includes('Закрыть')) {
            document.getElementById('progress-modal').style.display = 'none';
            return;
        }

        // Отменяем обработку
        try {
            await fetch(this.state.config.apiEndpoints.cancel, { method: 'POST' });
            this.state.processingCancelled = true;
            
            if (this.state.statusCheckInterval) {
                clearInterval(this.state.statusCheckInterval);
            }
            
            document.getElementById('progress-modal').style.display = 'none';
            this.showToast('Обработка отменена', '', 'warning');
            
        } catch (error) {
            console.error('Ошибка отмены:', error);
        }
    },

    // === УТИЛИТЫ ===

    // Навигация назад
    goBack() {
        this.showToast('Возврат к главному модулю', '', 'info');
        window.location.href = this.state.config.backUrl;
    },

    // Уведомления
    showToast(title, message, type = 'info') {
        const toastContainer = document.getElementById('toast-container');
        
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        let iconClass = 'fa-info-circle';
        if (type === 'success') iconClass = 'fa-check-circle';
        if (type === 'error') iconClass = 'fa-exclamation-circle';
        if (type === 'warning') iconClass = 'fa-exclamation-triangle';
        
        toast.innerHTML = `
            <div class="toast-icon">
                <i class="fas ${iconClass}"></i>
            </div>
            <div class="toast-content">
                <div class="toast-title">${title}</div>
                <div class="toast-message">${message}</div>
            </div>
            <button class="toast-close" onclick="this.parentNode.remove()">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        toastContainer.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('show');
        }, 10);
        
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, 5000);
    },

    // Настройка drag and drop
    setupDragAndDrop() {
        const dragDropArea = document.getElementById('dragDropArea');

        dragDropArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            dragDropArea.classList.add('drag-over');
        });

        dragDropArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            dragDropArea.classList.remove('drag-over');
        });

        dragDropArea.addEventListener('drop', (e) => {
            e.preventDefault();
            dragDropArea.classList.remove('drag-over');
            
            const files = Array.from(e.dataTransfer.files);
            this.handleFiles(files);
        });
    },

    // Закрытие модального окна при клике вне его
    setupModalCloseOnOutsideClick() {
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.style.display = 'none';
                    if (this.state.statusCheckInterval) {
                        clearInterval(this.state.statusCheckInterval);
                    }
                }
            });
        });
    }
};

// Инициализация при загрузке DOM
document.addEventListener('DOMContentLoaded', () => AutoDailyesApp.init());