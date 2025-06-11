/**
 * Полное приложение Автореестров с поддержкой OneFactor
 * Единый JavaScript файл для всех типов автореестров
 */

const AutoregApp = {
    // Состояние приложения
    state: {
        appSettings: {},
        currentRegisterType: '',
        templateHeaders: [],
        fileHeaders: [],
        mappedHeaders: {},
        isDarkMode: false,
        fileUploaded: false,
        sessionId: null,
        currentProcessId: null,
        backUrl: '/nexus/autoreg/prolong',
        selectedFiles: [],
        requiredFiles: [],
        config: null
    },

    // Инициализация приложения
    init() {
        this.loadConfig();
        this.loadUITheme();
        this.updateButtonStates();
        this.scheduleCleanup();
        this.loadTemplateHeadersDemo();
        this.setupModalCloseOnOutsideClick();
        
        // Если включен drag&drop, настраиваем его
        if (this.state.config?.dragDropEnabled) {
            this.setupDragAndDrop();
        }
    },

    // Загрузка конфигурации
    loadConfig() {
        if (window.autoregConfig) {
            this.state.config = window.autoregConfig;
            this.state.currentRegisterType = window.autoregConfig.registerType;
            this.state.templateHeaders = window.autoregConfig.templateHeaders || [];
            this.state.backUrl = window.autoregConfig.backUrl || '/nexus/autoreg/prolong';
            
            // Инициализируем requiredFiles если это множественные файлы
            if (window.autoregConfig.multipleFiles && window.autoregConfig.requiredFiles) {
                this.state.requiredFiles = window.autoregConfig.requiredFiles.map(file => ({
                    ...file,
                    found: false
                }));
            }
        }
    },

    // Демо-загрузка заголовков шаблона
    loadTemplateHeadersDemo() {
        setTimeout(() => {
            console.log(`Загружены заголовки для ${this.state.currentRegisterType}:`, this.state.templateHeaders.length);
        }, 500);
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

        this.state.isDarkMode = !isDark;
        this.showToast('Тема изменена', 'Оформление интерфейса обновлено', 'info');
    },

    // Загрузка сохранённой темы
    loadUITheme() {
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'dark') {
            document.body.classList.add('dark-mode');
            this.state.isDarkMode = true;
        }
    },

    // Обновление состояния кнопок
    updateButtonStates() {
        const loadButton = document.getElementById('loadButton');
        const mapButton = document.querySelector('.centered-button .btn-primary[onclick="AutoregApp.mapHeaders()"]');
        const processButton = document.querySelector('.bottom-buttons .btn-primary');
        
        if (this.state.config?.multipleFiles) {
            // Для множественных файлов проверяем все ли файлы найдены
            const foundCount = this.state.requiredFiles.filter(req => req.found).length;
            const totalRequired = this.state.requiredFiles.length;
            if (loadButton) loadButton.disabled = foundCount !== totalRequired;
        } else {
            // Для одиночного файла
            if (loadButton) loadButton.disabled = !this.state.fileUploaded;
        }
        
        if (mapButton) {
            mapButton.disabled = Object.keys(this.state.mappedHeaders).length === 0;
        }
        
        if (processButton) {
            processButton.disabled = Object.keys(this.state.mappedHeaders).length === 0;
        }
    },

    // === РАБОТА С ФАЙЛАМИ ===

    // Выбор файла (универсальный метод)
    selectFile() {
        if (this.state.config?.multipleFiles) {
            this.selectFiles();
        } else {
            this.selectSingleFile();
        }
    },

    // Выбор множественных файлов (для OneFactor)
    selectFiles() {
        const input = document.createElement('input');
        input.type = 'file';
        input.multiple = true;
        input.accept = '.xls,.xlsx';
        input.onchange = (e) => {
            this.handleFiles(Array.from(e.target.files));
        };
        input.click();
    },

    // Выбор одиночного файла (для обычных автореестров)
    selectSingleFile() {
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.accept = '.xlsx, .xls';
        fileInput.style.display = 'none';
        
        fileInput.addEventListener('change', (e) => {
            if (e.target.files && e.target.files[0]) {
                this.handleFileSelection(e.target.files[0]);
            }
        });
        
        document.body.appendChild(fileInput);
        fileInput.click();
        document.body.removeChild(fileInput);
    },

    // Обработка множественных файлов
    handleFiles(files) {
        const validFiles = files.filter(file => 
            file.name.endsWith('.xls') || file.name.endsWith('.xlsx')
        );

        validFiles.forEach(file => {
            if (!this.state.selectedFiles.some(f => f.name === file.name)) {
                this.state.selectedFiles.push(file);
            }
        });

        this.updateFileDisplay();
        this.validateFiles();
        this.updateButtonStates();
    },

    // Валидация файлов для OneFactor
    validateFiles() {
        if (!this.state.config?.multipleFiles) return;

        // Сбрасываем статус найденных файлов
        this.state.requiredFiles.forEach(req => req.found = false);
        
        // Проверяем какие файлы найдены
        this.state.selectedFiles.forEach(file => {
            this.state.requiredFiles.forEach(req => {
                if (file.name.toLowerCase().startsWith(req.prefix.toLowerCase())) {
                    req.found = true;
                }
            });
        });
        
        this.updateFileStatus();
    },

    // Обновление статуса файлов
    updateFileStatus() {
        const fileStatus = document.querySelector('.file-status');
        
        if (this.state.config?.multipleFiles) {
            const foundCount = this.state.requiredFiles.filter(req => req.found).length;
            const totalRequired = this.state.requiredFiles.length;
            
            if (this.state.selectedFiles.length === 0) {
                fileStatus.innerHTML = `<i class="fas fa-info-circle"></i><span>Файлы не выбраны (требуется ${totalRequired} файла)</span>`;
                fileStatus.className = 'file-status';
            } else if (foundCount === totalRequired) {
                fileStatus.innerHTML = '<i class="fas fa-check-circle"></i><span>Все необходимые файлы выбраны!</span>';
                fileStatus.className = 'file-status success';
            } else {
                const missing = this.state.requiredFiles.filter(req => !req.found).map(req => req.name).join(', ');
                fileStatus.innerHTML = `<i class="fas fa-exclamation-triangle"></i><span>Найдено ${foundCount}/${totalRequired}. Отсутствуют: ${missing}</span>`;
                fileStatus.className = 'file-status error';
            }
        }
    },

    // Обновление отображения файлов
    updateFileDisplay() {
        if (this.state.config?.multipleFiles) {
            this.updateMultipleFileDisplay();
        }
    },

    // Отображение множественных файлов
    updateMultipleFileDisplay() {
        const fileList = document.getElementById('fileList');
        const uploadText = document.getElementById('uploadText');
        const progressBarFill = document.getElementById('progressBarFill');

        if (this.state.selectedFiles.length === 0) {
            fileList.innerHTML = '';
            uploadText.innerHTML = this.state.config.dragDropText;
            if (progressBarFill) progressBarFill.style.width = '0%';
            return;
        }

        uploadText.textContent = `Файлов выбрано: ${this.state.selectedFiles.length}`;
        if (progressBarFill) {
            progressBarFill.style.width = `${(this.state.selectedFiles.length / this.state.config.requiredFilesCount) * 100}%`;
        }

        fileList.innerHTML = this.state.selectedFiles.map((file, index) => `
            <li class="file-item">
                <div class="file-info">
                    <i class="fas fa-file-excel"></i>
                    <div>
                        <div class="file-name">${file.name}</div>
                        <div class="file-type">${this.getFileType(file.name)}</div>
                    </div>
                </div>
                <button class="remove-file" onclick="AutoregApp.removeFile(${index})">
                    <i class="fas fa-times"></i>
                </button>
            </li>
        `).join('');
    },

    // Определение типа файла
    getFileType(fileName) {
        if (!this.state.config?.requiredFiles) return 'Excel файл';
        
        const lowerName = fileName.toLowerCase();
        for (const req of this.state.config.requiredFiles) {
            if (lowerName.startsWith(req.prefix.toLowerCase())) {
                return req.name;
            }
        }
        return 'Excel файл';
    },

    // Удаление файла
    removeFile(index) {
        this.state.selectedFiles.splice(index, 1);
        this.updateFileDisplay();
        this.validateFiles();
        this.updateButtonStates();
    },

    // Обработка выбранного файла (для обычных автореестров)
    async handleFileSelection(file) {
        const filePathInput = document.getElementById('file-path-input');
        if (filePathInput) filePathInput.value = file.name;
        
        const fileStatus = document.querySelector('.file-status');
        fileStatus.innerHTML = '<i class="fas fa-sync fa-spin"></i><span>Загрузка файла...</span>';
        fileStatus.classList.remove('success', 'error');
        
        this.showProgressBar();
        
        try {
            const formData = new FormData();
            formData.append('file', file);
            
            const response = await fetch('/processing/upload-excel', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            this.state.sessionId = data.session_id;
            this.state.fileHeaders = data.headers;
            
            fileStatus.innerHTML = '<i class="fas fa-check-circle"></i><span>Файл загружен успешно</span>';
            fileStatus.classList.add('success');
            
            this.hideProgressBar(true);
            this.showToast('Файл загружен', `Файл "${file.name}" успешно загружен`, 'success');
            
            this.state.fileUploaded = true;
            this.updateButtonStates();
            
        } catch (error) {
            fileStatus.innerHTML = `<i class="fas fa-exclamation-circle"></i><span>Ошибка: ${error.message}</span>`;
            fileStatus.classList.add('error');
            
            this.hideProgressBar(false);
            this.showToast('Ошибка загрузки', error.message, 'error');
            
            this.state.fileUploaded = false;
            this.state.sessionId = null;
            this.updateButtonStates();
        }
    },

    // Показать прогресс-бар
    showProgressBar() {
        const progressBar = document.querySelector('.progress-bar');
        const progressFill = document.querySelector('.progress-bar-fill');
        
        if (progressBar && progressFill) {
            progressBar.style.display = 'block';
            progressFill.style.width = '0%';
            
            let progress = 0;
            const interval = setInterval(() => {
                progress += 5;
                if (progress > 90) {
                    clearInterval(interval);
                } else {
                    progressFill.style.width = progress + '%';
                }
            }, 50);
        }
    },

    // Скрыть прогресс-бар
    hideProgressBar(success) {
        const progressBar = document.querySelector('.progress-bar');
        const progressFill = document.querySelector('.progress-bar-fill');
        
        if (progressBar && progressFill) {
            if (success) {
                progressFill.style.width = '100%';
            }
            
            setTimeout(() => {
                progressBar.style.display = 'none';
            }, 500);
        }
    },

    // === РАБОТА С ЗАГОЛОВКАМИ ===

    // Загрузка заголовков шаблона (универсальный метод)
    async loadTemplateHeaders() {
        if (this.state.config?.multipleFiles) {
            await this.loadMultipleFileHeaders();
        } else {
            await this.loadSingleFileHeaders();
        }
    },

    // Загрузка заголовков для множественных файлов (OneFactor)
    async loadMultipleFileHeaders() {
        if (this.state.selectedFiles.length !== this.state.config.requiredFilesCount) {
            this.showToast('Ошибка', `Необходимо выбрать все ${this.state.config.requiredFilesCount} файла`, 'error');
            return;
        }
        
        const foundCount = this.state.requiredFiles.filter(req => req.found).length;
        if (foundCount !== this.state.config.requiredFilesCount) {
            this.showToast('Ошибка', 'Не все необходимые файлы найдены', 'error');
            return;
        }
        
        const loadButton = document.getElementById('loadButton');
        loadButton.innerHTML = '<div class="loading-spinner"><div></div><div></div><div></div><div></div></div> Загрузка...';
        loadButton.disabled = true;
        
        const fileStatus = document.querySelector('.file-status');
        fileStatus.innerHTML = '<i class="fas fa-sync fa-spin"></i><span>Объединение и загрузка файлов...</span>';
        fileStatus.classList.remove('success', 'error');
        
        this.showProgressBar();
        
        try {
            const formData = new FormData();
            this.state.selectedFiles.forEach(file => {
                formData.append('files', file);
            });
            
            const uploadEndpoint = this.state.config.uploadEndpoint || '/processing/upload-excel';
            const response = await fetch(uploadEndpoint, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            this.state.sessionId = data.session_id;
            this.state.fileHeaders = data.headers;
            
            fileStatus.innerHTML = '<i class="fas fa-check-circle"></i><span>Файлы объединены и загружены успешно</span>';
            fileStatus.classList.add('success');
            
            this.hideProgressBar(true);
            
            // Автоматическое сопоставление
            await this.performAutoMapping();
            
            loadButton.innerHTML = '<i class="fas fa-check"></i> Заголовки загружены';
            this.showToast('Заголовки загружены', `Объединено ${this.state.selectedFiles.length} файлов, найдено ${this.state.fileHeaders.length} уникальных заголовков`, 'success');
            
            this.state.fileUploaded = true;
            this.updateButtonStates();
            
        } catch (error) {
            this.handleLoadingError(loadButton, fileStatus, error);
        }
    },

    // Загрузка заголовков для одиночного файла
    async loadSingleFileHeaders() {
        if (!this.state.fileUploaded || !this.state.sessionId) {
            this.showToast('Ошибка', 'Пожалуйста, выберите и загрузите файл', 'error');
            return;
        }
        
        const loadButton = document.getElementById('loadButton');
        loadButton.innerHTML = '<div class="loading-spinner"><div></div><div></div><div></div><div></div></div> Загрузка...';
        loadButton.disabled = true;
        
        try {
            await this.performAutoMapping();
            
            loadButton.innerHTML = '<i class="fas fa-check"></i> Заголовки загружены';
            this.showToast('Заголовки загружены', 'Теперь вы можете сопоставить заголовки', 'success');
            this.updateButtonStates();
            
        } catch (error) {
            loadButton.innerHTML = '<i class="fas fa-sync-alt"></i> Загрузить заголовки';
            loadButton.disabled = false;
            this.showToast('Ошибка', error.message, 'error');
        }
    },

    // Автоматическое сопоставление
    async performAutoMapping() {
        const response = await fetch('/api/auto-map-headers', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                registerType: this.state.currentRegisterType.toLowerCase(),
                templateHeaders: this.state.templateHeaders,
                fileHeaders: this.state.fileHeaders
            })
        });

        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        if (data.mappings && Object.keys(data.mappings).length > 0) {
            this.state.mappedHeaders = data.mappings;
            this.showToast('Автоматическое сопоставление', `Автоматически сопоставлено ${Object.keys(this.state.mappedHeaders).length} заголовков`, 'success');
            this.updateStepIndicator(4);
        } else {
            this.updateStepIndicator(3);
        }
        
        this.updateTemplateHeadersList();
        this.updateFileHeadersList();
        this.updateVisualMappingState();
    },

    // Обработка ошибок загрузки
    handleLoadingError(loadButton, fileStatus, error) {
        loadButton.innerHTML = '<i class="fas fa-sync-alt"></i> Загрузить заголовки';
        loadButton.disabled = false;
        
        fileStatus.innerHTML = `<i class="fas fa-exclamation-circle"></i><span>Ошибка: ${error.message}</span>`;
        fileStatus.classList.add('error');
        
        this.hideProgressBar(false);
        this.showToast('Ошибка загрузки', error.message, 'error');
        
        this.state.fileUploaded = false;
        this.state.sessionId = null;
        this.updateButtonStates();
    },

    // Обновление списка заголовков шаблона
    updateTemplateHeadersList() {
        const listElement = document.getElementById('list-registry');
        listElement.innerHTML = '';
        
        this.state.templateHeaders.forEach((header, index) => {
            const li = document.createElement('li');
            li.className = 'header-item';
            li.setAttribute('data-index', index);
            li.setAttribute('data-header', header);
            li.innerHTML = `
            <div>
                <i class="fas fa-grip-lines drag-handle"></i>
                <span class="item-text">${header}</span>
            </div>
            <span class="item-indicator"></span>
            `;
            
            li.addEventListener('click', () => {
                this.selectTemplateHeader(li);
            });
            
            listElement.appendChild(li);
        });
        
        document.getElementById('template-counter').textContent = this.state.templateHeaders.length;
    },

    // Обновление списка заголовков файла
    updateFileHeadersList() {
        const listElement = document.getElementById('list-excel');
        listElement.innerHTML = '';
        
        this.state.fileHeaders.forEach((header, index) => {
            const li = document.createElement('li');
            li.className = 'header-item';
            li.setAttribute('data-index', index);
            li.setAttribute('data-header', header);
            li.innerHTML = `
            <div>
                <span class="item-text">${header}</span>
            </div>
            <span class="item-indicator"></span>
            `;
            
            li.addEventListener('click', () => {
                this.selectFileHeader(li);
            });
            
            listElement.appendChild(li);
        });
        
        document.getElementById('file-counter').textContent = this.state.fileHeaders.length;
    },

    // Выбор заголовка шаблона
    selectTemplateHeader(element) {
        document.querySelectorAll('#list-registry .header-item').forEach(item => {
            item.classList.remove('selected');
        });
        element.classList.add('selected');
    },

    // Выбор заголовка файла
    selectFileHeader(element) {
        const templateSelected = document.querySelector('#list-registry .header-item.selected');
        if (templateSelected) {
            const templateHeader = templateSelected.getAttribute('data-header');
            const fileHeader = element.getAttribute('data-header');
            
            this.state.mappedHeaders[templateHeader] = fileHeader;
            
            templateSelected.classList.add('matched');
            element.classList.add('matched');
            
            this.showMappingAnimation(templateSelected, element);
            templateSelected.classList.remove('selected');
            
            this.showToast('Соответствие установлено', `"${templateHeader}" ↔ "${fileHeader}"`, 'success');
            this.updateButtonStates();
        } else {
            this.showToast('Внимание', 'Сначала выберите заголовок шаблона', 'warning');
        }
    },

    // Анимация сопоставления
    showMappingAnimation(templateElement, fileElement) {
        setTimeout(() => {
            templateElement.querySelector('.item-indicator').style.backgroundColor = '#10b981';
            fileElement.querySelector('.item-indicator').style.backgroundColor = '#10b981';
        }, 100);
    },

    // Фильтрация заголовков
    filterTemplateHeaders(query) {
        const items = document.querySelectorAll('#list-registry .header-item');
        const lowerQuery = query.toLowerCase();
        
        items.forEach(item => {
            const headerText = item.getAttribute('data-header').toLowerCase();
            item.style.display = headerText.includes(lowerQuery) ? '' : 'none';
        });
    },

    filterFileHeaders(query) {
        const items = document.querySelectorAll('#list-excel .header-item');
        const lowerQuery = query.toLowerCase();
        
        items.forEach(item => {
            const headerText = item.getAttribute('data-header').toLowerCase();
            item.style.display = headerText.includes(lowerQuery) ? '' : 'none';
        });
    },

    // === СОПОСТАВЛЕНИЕ ===

    // Установка соответствия заголовков
    async mapHeaders() {
        const mappedCount = Object.keys(this.state.mappedHeaders).length;
        
        if (mappedCount === 0) {
            this.showToast('Ошибка', 'Не установлено ни одного соответствия', 'error');
            return;
        }
        
        if (mappedCount < Math.min(this.state.templateHeaders.length, this.state.fileHeaders.length) * 0.7) {
            this.showConfirmDialog(
                'Внимание',
                `Сопоставлено только ${mappedCount} из ${this.state.templateHeaders.length} заголовков. Вы уверены, что хотите продолжить?`,
                () => {
                    this.saveCorrespondences();
                }
            );
        } else {
            this.saveCorrespondences();
        }
    },

    // Сохранение соответствий
    async saveCorrespondences() {
        const mapButton = document.querySelector('.centered-button .btn-primary[onclick="AutoregApp.mapHeaders()"]');
        const originalButtonText = mapButton.innerHTML;
        mapButton.innerHTML = '<div class="loading-spinner"><div></div><div></div><div></div><div></div></div> Сохранение...';
        mapButton.disabled = true;
        
        try {
            const response = await fetch('/api/save-correspondences', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    registerType: this.state.currentRegisterType.toLowerCase(),
                    mappings: this.state.mappedHeaders
                })
            });

            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            mapButton.innerHTML = originalButtonText;
            mapButton.disabled = false;
            
            this.showToast('Соответствия сохранены', 'Соответствия успешно сохранены в базе данных', 'success');
            this.updateStepIndicator(4);
            document.querySelector('.bottom-buttons .btn-primary').disabled = false;
            
        } catch (error) {
            mapButton.innerHTML = originalButtonText;
            mapButton.disabled = false;
            this.showToast('Ошибка', `Не удалось сохранить соответствия: ${error.message}`, 'error');
        }
    },

    // === ОБРАБОТКА ===

    // Диалог задачи
    openTaskDialog() {
        const modal = document.getElementById('task-modal');
        const modalContent = modal.querySelector('.modal-content');
        
        modal.classList.add('show');
        setTimeout(() => {
            modalContent.style.opacity = '1';
            modalContent.style.transform = 'translateY(0)';
        }, 10);
        
        setTimeout(() => {
            document.getElementById('task-number').focus();
        }, 300);
    },

    closeTaskDialog() {
        const modal = document.getElementById('task-modal');
        const modalContent = modal.querySelector('.modal-content');
        
        modalContent.style.opacity = '0';
        modalContent.style.transform = 'translateY(-20px)';
        
        setTimeout(() => {
            modal.classList.remove('show');
        }, 300);
    },

    // Запуск обработки
    async startProcessing() {
        const taskNumber = document.getElementById('task-number').value;
        
        if (!taskNumber || isNaN(taskNumber) || taskNumber <= 0) {
            this.showToast('Ошибка', 'Пожалуйста, введите корректный номер задачи', 'error');
            return;
        }
        
        if (!this.state.sessionId) {
            this.showToast('Ошибка', 'Файл не загружен или сессия истекла', 'error');
            return;
        }
        
        if (Object.keys(this.state.mappedHeaders).length === 0) {
            this.showToast('Ошибка', 'Не установлены соответствия заголовков', 'error');
            return;
        }
        
        this.closeTaskDialog();
        this.openProgressDialog();
        
        try {
            const response = await fetch('/processing/start-processing', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    taskNumber: taskNumber,
                    sessionId: this.state.sessionId,
                    mappings: this.state.mappedHeaders,
                    registerType: this.state.currentRegisterType
                })
            });

            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            this.state.currentProcessId = data.process_id;
            this.startProgressPolling();
            this.showToast('Обработка запущена', 'Реестр обрабатывается, ожидайте...', 'info');
            
        } catch (error) {
            this.closeProgressDialog();
            this.showToast('Ошибка запуска', error.message, 'error');
        }
    },

    // Отслеживание прогресса
    startProgressPolling() {
        if (!this.state.currentProcessId) return;
        
        const pollInterval = setInterval(async () => {
            if (!this.state.currentProcessId) {
                clearInterval(pollInterval);
                return;
            }
            
            try {
                const response = await fetch(`/processing/process-stats/${this.state.currentProcessId}`);
                const data = await response.json();
                
                if (data.error) {
                    clearInterval(pollInterval);
                    this.closeProgressDialog();
                    this.showToast('Ошибка', data.error, 'error');
                    return;
                }
                
                this.updateProgressDialog(data.progress, data.step);
                
                if (data.status === 'completed') {
                    clearInterval(pollInterval);
                    
                    if (data.has_download) {
                        this.downloadResultAutomatically();
                    } else {
                        this.closeProgressDialog();
                        this.showToast('Ошибка', 'Файл результата недоступен', 'error');
                    }
                    
                } else if (data.status === 'error') {
                    clearInterval(pollInterval);
                    this.closeProgressDialog();
                    this.showToast('Ошибка обработки', data.error || 'Неизвестная ошибка', 'error');
                } else if (data.status === 'cancelled') {
                    clearInterval(pollInterval);
                    this.closeProgressDialog();
                    this.showToast('Отменено', 'Обработка была отменена', 'warning');
                }
            } catch (error) {
                clearInterval(pollInterval);
                this.closeProgressDialog();
                this.showToast('Ошибка', 'Потеряна связь с сервером', 'error');
            }
        }, 1000);
    },

    // Автоматическое скачивание результата
    async downloadResultAutomatically() {
        try {
            document.getElementById('progress-step').textContent = 'Успешно выполнено!';
            document.getElementById('progress-percentage').textContent = '100%';
            document.getElementById('progress-bar-fill').style.width = '100%';
            
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            const response = await fetch(`/processing/download-result/${this.state.currentProcessId}`);
            
            if (!response.ok) {
                throw new Error('Ошибка скачивания файла');
            }
            
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = `${this.state.currentProcessId}_${this.state.currentRegisterType}_пролонгация.zip`;
            
            if (contentDisposition) {
                const filenameStarMatch = contentDisposition.match(/filename\*=UTF-8''([^;]+)/);
                if (filenameStarMatch) {
                    try {
                        filename = decodeURIComponent(filenameStarMatch[1]);
                    } catch (e) {
                        console.warn('Ошибка декодирования filename*:', e);
                    }
                } else {
                    const filenameMatch = contentDisposition.match(/filename="?([^";]+)"?/);
                    if (filenameMatch) {
                        filename = filenameMatch[1];
                    }
                }
            }

            filename = filename.replace(/[<>:"/\\|?*]/g, '_').trim();
            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            this.closeProgressDialog();
            this.showToast('Файл скачан', `Архив "${filename}" успешно скачан`, 'success');
            this.updateStepIndicator(5);
            
            setTimeout(() => {
                this.cleanupProcess();
            }, 5000);
            
        } catch (error) {
            this.closeProgressDialog();
            this.showToast('Ошибка скачивания', error.message || 'Не удалось скачать файл', 'error');
        }
    },

    // Очистка процесса
    async cleanupProcess() {
        if (!this.state.currentProcessId) return;
        
        try {
            await fetch(`/processing/cleanup-process/${this.state.currentProcessId}`, {
                method: 'POST'
            });
            console.log('Процесс очищен:', this.state.currentProcessId);
            this.state.currentProcessId = null;
        } catch (error) {
            console.error('Ошибка очистки процесса:', error);
        }
    },

    // Отмена обработки
    async cancelProcessing() {
        if (!this.state.currentProcessId) {
            this.closeProgressDialog();
            return;
        }
        
        try {
            const response = await fetch(`/processing/cancel-processing/${this.state.currentProcessId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            const data = await response.json();
            this.state.currentProcessId = null;
            this.closeProgressDialog();
            
            if (data.success) {
                this.showToast('Отменено', 'Обработка реестра была отменена', 'warning');
            } else {
                this.showToast('Ошибка', data.error || 'Не удалось отменить процесс', 'error');
            }
        } catch (error) {
            this.state.currentProcessId = null;
            this.closeProgressDialog();
            this.showToast('Ошибка', 'Не удалось отменить процесс', 'error');
        }
    },

    // === ДИАЛОГИ ===

    // Прогресс диалог
    openProgressDialog() {
        const modal = document.getElementById('progress-modal');
        const modalContent = modal.querySelector('.modal-content');
        
        document.getElementById('progress-bar-fill').style.width = '0%';
        document.getElementById('progress-percentage').textContent = '0%';
        document.getElementById('progress-step').textContent = 'Инициализация...';
        
        modal.classList.add('show');
        setTimeout(() => {
            modalContent.style.opacity = '1';
            modalContent.style.transform = 'translateY(0)';
        }, 10);
    },

    closeProgressDialog() {
        const modal = document.getElementById('progress-modal');
        const modalContent = modal.querySelector('.modal-content');
        
        modalContent.style.opacity = '0';
        modalContent.style.transform = 'translateY(-20px)';
        
        setTimeout(() => {
            modal.classList.remove('show');
        }, 300);
    },

    updateProgressDialog(progress, step) {
        const progressBar = document.getElementById('progress-bar-fill');
        const progressPercent = document.getElementById('progress-percentage');
        const progressStep = document.getElementById('progress-step');
        
        if (progressBar) progressBar.style.width = `${progress}%`;
        if (progressPercent) progressPercent.textContent = `${Math.round(progress)}%`;
        if (progressStep) progressStep.textContent = step || 'Обработка...';
    },

    // Настройки диалог
    openSettingsDialog() {
        const modal = document.getElementById('settings-modal');
        const modalContent = modal.querySelector('.modal-content');
        
        this.loadSettings();
        modal.classList.add('show');
        setTimeout(() => {
            modalContent.style.opacity = '1';
            modalContent.style.transform = 'translateY(0)';
        }, 10);
    },

    closeSettingsDialog() {
        const modal = document.getElementById('settings-modal');
        const modalContent = modal.querySelector('.modal-content');
        
        modalContent.style.opacity = '0';
        modalContent.style.transform = 'translateY(-20px)';
        
        setTimeout(() => {
            modal.classList.remove('show');
        }, 300);
    },

    async loadSettings() {
        try {
            const response = await fetch(`/api/get-settings?type=${this.state.currentRegisterType}`);
            const data = await response.json();
            this.renderSettingsFields(data);
        } catch (error) {
            console.error('Error loading settings:', error);
            this.showToast('Ошибка', 'Не удалось загрузить настройки', 'error');
        }
    },

    renderSettingsFields(settingsData) {
        const settingsFields = document.getElementById('settings-fields');
        settingsFields.innerHTML = '';
        
        Object.entries(settingsData).forEach(([key, value]) => {
            const fieldDiv = document.createElement('div');
            fieldDiv.className = 'settings-field';
            fieldDiv.innerHTML = `
                <label for="setting-${key}">${key}</label>
                <input type="text" id="setting-${key}" value="${value}" data-key="${key}">
            `;
            settingsFields.appendChild(fieldDiv);
        });
        
        if (Object.keys(settingsData).length === 0) {
            settingsFields.innerHTML = '<p class="no-settings-message">Для данного типа реестра нет настроек</p>';
        }
        
        this.state.appSettings = {...settingsData};
    },

    async saveSettings() {
        const settingsInputs = document.querySelectorAll('#settings-fields input');
        const updatedSettings = {};
        
        settingsInputs.forEach(input => {
            const key = input.getAttribute('data-key');
            updatedSettings[key] = input.value;
        });
        
        try {
            const response = await fetch('/api/save-settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    type: this.state.currentRegisterType,
                    settings: updatedSettings
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.closeSettingsDialog();
                this.showToast('Настройки сохранены', 'Настройки приложения успешно сохранены', 'success');
            } else {
                throw new Error('Failed to save settings');
            }
        } catch (error) {
            console.error('Error saving settings:', error);
            this.showToast('Ошибка', 'Не удалось сохранить настройки', 'error');
        }
    },

    // Соответствия диалог
    openCorrespondencesDialog() {
        const modal = document.getElementById('correspondences-modal');
        const modalContent = modal.querySelector('.modal-content');
        
        this.updateCorrespondencesList();
        modal.classList.add('show');
        setTimeout(() => {
            modalContent.style.opacity = '1';
            modalContent.style.transform = 'translateY(0)';
        }, 10);
    },

    closeCorrespondencesDialog() {
        const modal = document.getElementById('correspondences-modal');
        const modalContent = modal.querySelector('.modal-content');
        
        modalContent.style.opacity = '0';
        modalContent.style.transform = 'translateY(-20px)';
        
        setTimeout(() => {
            modal.classList.remove('show');
        }, 300);
    },

    updateCorrespondencesList() {
        const listElement = document.getElementById('correspondence-list');
        const emptyMessage = document.getElementById('empty-correspondence-message');
        
        listElement.innerHTML = '';
        const correspondences = Object.entries(this.state.mappedHeaders);
        
        if (correspondences.length === 0) {
            emptyMessage.style.display = 'block';
            listElement.style.display = 'none';
            return;
        }
        
        emptyMessage.style.display = 'none';
        listElement.style.display = 'block';
        
        correspondences.forEach(([templateHeader, fileHeader]) => {
            const item = document.createElement('div');
            item.className = 'correspondence-item';
            item.innerHTML = `
                <div class="correspondence-content">
                    <div class="template-header">${templateHeader}</div>
                    <div class="correspondence-arrow">
                        <i class="fas fa-long-arrow-alt-down"></i> соответствует
                    </div>
                    <div class="file-header">${fileHeader}</div>
                </div>
                <button class="delete-btn" onclick="AutoregApp.deleteCorrespondence('${templateHeader}')">
                    <i class="fas fa-trash"></i>
                </button>
            `;
            listElement.appendChild(item);
        });
    },

    deleteCorrespondence(templateHeader) {
        if (confirm(`Вы действительно хотите удалить соответствие для "${templateHeader}"?`)) {
            delete this.state.mappedHeaders[templateHeader];
            this.updateVisualMappingState();
            this.updateCorrespondencesList();
            this.updateButtonStates();
            this.showToast('Соответствие удалено', `Соответствие для "${templateHeader}" успешно удалено`, 'info');
        }
    },

    // === УТИЛИТЫ ===

    // Обновление визуального состояния сопоставления
    updateVisualMappingState() {
        document.querySelectorAll('#list-registry .header-item, #list-excel .header-item').forEach(item => {
            item.classList.remove('matched');
            item.querySelector('.item-indicator').style.backgroundColor = '';
        });
        
        Object.entries(this.state.mappedHeaders).forEach(([templateHeader, fileHeader]) => {
            const templateItem = Array.from(document.querySelectorAll('#list-registry .header-item'))
                .find(item => item.getAttribute('data-header') === templateHeader);
            
            const fileItem = Array.from(document.querySelectorAll('#list-excel .header-item'))
                .find(item => item.getAttribute('data-header') === fileHeader);
            
            if (templateItem) {
                templateItem.classList.add('matched');
                templateItem.querySelector('.item-indicator').style.backgroundColor = '#10b981';
            }
            
            if (fileItem) {
                fileItem.classList.add('matched');
                fileItem.querySelector('.item-indicator').style.backgroundColor = '#10b981';
            }
        });
    },

    // Обновление индикатора шагов
    updateStepIndicator(activeStep) {
        const steps = document.querySelectorAll('.steps-indicator .step');
        
        steps.forEach((step, index) => {
            const stepNumber = index + 1;
            
            if (stepNumber < activeStep) {
                step.className = 'step completed';
            } else if (stepNumber === activeStep) {
                step.className = 'step active';
            } else {
                step.className = 'step';
            }
        });
    },

    // Настройка drag and drop
    setupDragAndDrop() {
        const dragDropArea = document.getElementById('dragDropArea');
        if (!dragDropArea) return;

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
    },

    // Навигация
    goBack() {
        if (Object.keys(this.state.mappedHeaders).length > 0) {
            this.showConfirmDialog(
                'Подтверждение',
                'Все несохраненные данные будут потеряны. Вы уверены, что хотите вернуться?',
                () => {
                    this.showToast('Переход', 'Возврат к выбору типа реестра', 'info');
                    window.location.href = this.state.backUrl;
                }
            );
        } else {
            this.showToast('Переход', 'Возврат к выбору типа реестра', 'info');
            window.location.href = this.state.backUrl;
        }
    },

    // Диалог подтверждения
    showConfirmDialog(title, message, confirmCallback) {
        if (confirm(message)) {
            confirmCallback();
        }
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

    // Очистка файлов
    scheduleCleanup() {
        setInterval(() => {
            fetch('/processing/cleanup-temp', {
                method: 'POST'
            }).catch(() => {});
        }, 30 * 60 * 1000);
    }
};

// Инициализация при загрузке DOM
document.addEventListener('DOMContentLoaded', () => AutoregApp.init());

// Очистка при выходе
window.addEventListener('beforeunload', function() {
    if (AutoregApp.state.sessionId) {
        fetch('/processing/cleanup-temp', {
            method: 'POST',
            keepalive: true
        });
    }
});