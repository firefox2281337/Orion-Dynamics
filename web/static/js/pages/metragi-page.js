/**
 * 📏 Модуль страницы генератора метражей (полностью исправленный)
 */
import { $, showNotification, createElement } from '../core/utils.js';
import { Loader } from '../components/loader.js';

export class MetragiPage {
    constructor() {
        this.form = document.getElementById('extractionForm');
        this.fileInput = document.getElementById('excel_file');
        this.fileInfo = document.getElementById('file-info');
        this.fileName = document.getElementById('file-name');
        this.submitButton = document.getElementById('submitButton');
        this.uploadLabel = document.querySelector('label[for="excel_file"]');
        this.loader = new Loader('loaderWrapper');
        
        this.init();
    }

    init() {
        
        if (!this.form) {
            return;
        }
        
        if (!this.fileInput) {
            return;
        }
        
        this.setupFileInput();
        this.setupFormSubmission();
        this.setupDragAndDrop();
        this.clearErrors();
        
    }

    setupFileInput() {
        
        this.fileInput.addEventListener('change', (event) => {
            const file = event.target.files[0];
            this.handleFileSelection(file);
        });

        // Дополнительный обработчик на label (если клик по label не работает)
        if (this.uploadLabel) {
            this.uploadLabel.addEventListener('click', () => {
            });
        }
    }

    handleFileSelection(file) {
        
        this.clearErrors();
        
        if (!file) {
            this.hideFileInfo();
            this.disableSubmit();
            return;
        };

        // Валидация файла
        const validation = this.validateFile(file);
        if (!validation.valid) {
            this.showError(validation.error);
            this.fileInput.value = '';
            this.hideFileInfo();
            this.disableSubmit();
            return;
        }

        
        // Показываем информацию о файле
        this.showFileInfo(file);
        this.enableSubmit();
    }

    validateFile(file) {
        const allowedTypes = [
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', // .xlsx
            'application/vnd.ms-excel' // .xls
        ];
        
        const maxSize = 50 * 1024 * 1024; // 50MB
        
        // Проверка типа файла
        const isValidType = allowedTypes.includes(file.type) || file.name.match(/\.(xlsx|xls)$/i);
        
        if (!isValidType) {
            return {
                valid: false,
                error: `Пожалуйста, выберите файл Excel (.xlsx или .xls). Тип файла: ${file.type}`
            };
        }

        // Проверка размера
        if (file.size > maxSize) {
            return {
                valid: false,
                error: `Файл слишком большой. Максимальный размер: ${this.formatFileSize(maxSize)}, ваш файл: ${this.formatFileSize(file.size)}`
            };
        }

        return { valid: true };
    }

    showFileInfo(file) {
        
        if (!this.fileInfo || !this.fileName) {
            return;
        }

        this.fileName.textContent = `${file.name} (${this.formatFileSize(file.size)})`;
        this.fileInfo.style.display = 'block';
        
        // Анимация появления
        this.fileInfo.style.opacity = '0';
        this.fileInfo.style.transform = 'translateY(10px)';
        setTimeout(() => {
            this.fileInfo.style.transition = 'all 0.3s ease';
            this.fileInfo.style.opacity = '1';
            this.fileInfo.style.transform = 'translateY(0)';
        }, 10);
        
    }

    hideFileInfo() {
        if (this.fileInfo) {
            this.fileInfo.style.display = 'none';
        }
    }

    enableSubmit() {
        if (this.submitButton) {
            this.submitButton.disabled = false;
        }
    }

    disableSubmit() {
        if (this.submitButton) {
            this.submitButton.disabled = true;
        }
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    setupFormSubmission() {
        this.form.addEventListener('submit', async (event) => {
            event.preventDefault();
            await this.handleFormSubmit();
        });
    }

    async handleFormSubmit() {
        if (!this.fileInput?.files?.length) {
            this.showError('Пожалуйста, выберите файл');
            return;
        }

        const formData = new FormData(this.form);
        const originalText = this.submitButton?.innerHTML || 'Сгенерировать отчёт';

        try {
            if (this.submitButton) {
                this.submitButton.disabled = true;
                this.submitButton.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Обработка...';
            }
            
            this.loader.show('Обрабатывается файл...');

            const response = await fetch('/processing/metragi', {
                method: 'POST',
                body: formData
            });


            if (!response.ok) {
                const contentType = response.headers.get('content-type');
                if (contentType && contentType.includes('application/json')) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || 'Неизвестная ошибка');
                } else {
                    const errorText = await response.text();
                    throw new Error(`Ошибка сервера: ${response.status} - ${errorText}`);
                }
            }

            const blob = await response.blob();
            
            this.downloadFile(blob, this.generateFileName());
            
            showNotification('Файлы успешно сгенерированы и скачаны!', 'success');
            this.resetForm();

        } catch (error) {
            this.showError(error.message || 'Произошла ошибка при обработке файла');
        } finally {
            if (this.submitButton) {
                this.submitButton.disabled = false;
                this.submitButton.innerHTML = originalText;
            }
            this.loader.hide();
        }
    }

    downloadFile(blob, filename) {
        const url = window.URL.createObjectURL(blob);
        const link = createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
    }

    generateFileName() {
        const today = new Date().toLocaleDateString('ru-RU').replace(/\//g, '-');
        return `Метражи_${today}.zip`;
    }

    resetForm() {
        if (this.fileInput) this.fileInput.value = '';
        this.hideFileInfo();
        this.disableSubmit();
    }

    showError(message) {
        this.clearErrors();
        
        let errorContainer = document.querySelector('.alert-danger');
        if (!errorContainer) {
            errorContainer = this.createErrorContainer();
        }
        
        errorContainer.innerHTML = `
            <i class="fas fa-exclamation-triangle me-2"></i>
            ${message}
        `;
        errorContainer.style.display = 'block';
        
    }

    createErrorContainer() {
        const container = createElement('div', {
            className: 'alert alert-danger mt-4 animate-fade-in'
        });
        container.setAttribute('role', 'alert');
        this.form.parentNode.appendChild(container);
        return container;
    }

    clearErrors() {
        const errorContainer = document.querySelector('.alert-danger');
        if (errorContainer) {
            errorContainer.style.display = 'none';
        }
    }

    setupDragAndDrop() {
        // Ищем контейнер для drag & drop
        const uploadContainer = this.form?.querySelector('.file-upload-container');
        
        if (!uploadContainer) {
            return;
        }


        // Предотвращаем стандартное поведение
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadContainer.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            }, false);
            
            document.body.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            }, false);
        });

        // Подсветка при наведении
        ['dragenter', 'dragover'].forEach(eventName => {
            uploadContainer.addEventListener(eventName, () => {
                this.highlight(uploadContainer);
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            uploadContainer.addEventListener(eventName, () => {
                this.unhighlight(uploadContainer);
            }, false);
        });

        // Обработка drop
        uploadContainer.addEventListener('drop', (e) => {
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                
                // Создаем новый FileList для input
                const dt = new DataTransfer();
                dt.items.add(files[0]);
                this.fileInput.files = dt.files;
                
                // Запускаем обработчик
                this.handleFileSelection(files[0]);
            }
        }, false);
        
    }

    highlight(container) {
        container.classList.add('drag-over');
        container.style.borderColor = 'var(--primary-color, #4361ee)';
        container.style.backgroundColor = 'rgba(67, 97, 238, 0.1)';
        container.style.transform = 'scale(1.02)';
        container.style.boxShadow = '0 15px 40px rgba(67, 97, 238, 0.3)';
    }

    unhighlight(container) {
        container.classList.remove('drag-over');
        container.style.borderColor = '';
        container.style.backgroundColor = '';
        container.style.transform = '';
        container.style.boxShadow = '';
    }

    // Методы для отладки
    getStatus() {
        return {
            formFound: !!this.form,
            fileInputFound: !!this.fileInput,
            submitButtonFound: !!this.submitButton,
            fileInfoFound: !!this.fileInfo,
            uploadLabelFound: !!this.uploadLabel,
            hasFile: !!(this.fileInput?.files?.length),
            fileName: this.fileInput?.files?.[0]?.name,
            uploadContainerFound: !!this.form?.querySelector('.file-upload-container')
        };
    }

    testFileSelection() {
        
        // Создаем тестовый файл
        const testFile = new File(['test content'], 'test.xlsx', {
            type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        });
        
        // Симулируем выбор файла
        const dt = new DataTransfer();
        dt.items.add(testFile);
        this.fileInput.files = dt.files;
        
        // Запускаем обработчик
        this.handleFileSelection(testFile);
    }

    forceFileSelection(file) {
        this.handleFileSelection(file);
    }
}