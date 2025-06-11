/**
 * 📤 File Upload компонент
 */
import { $, showNotification, createElement } from '../core/utils.js';

export class FileUpload {
    constructor(inputSelector, options = {}) {
        this.input = typeof inputSelector === 'string' ? 
            $(inputSelector) : inputSelector;
        
        this.options = {
            accept: '*',
            maxSize: 10 * 1024 * 1024, // 10MB по умолчанию
            multiple: false,
            dragAndDrop: true,
            onFileSelect: null,
            onError: null,
            onProgress: null,
            allowedTypes: [],
            ...options
        };

        this.files = [];
        this.dragCounter = 0;
        
        this.init();
    }

    init() {
        if (!this.input) {
            return;
        }

        this.setupFileInput();
        
        if (this.options.dragAndDrop) {
            this.setupDragAndDrop();
        }
    }

    setupFileInput() {
        // Настраиваем атрибуты input
        if (this.options.accept !== '*') {
            this.input.accept = this.options.accept;
        }
        
        if (this.options.multiple) {
            this.input.multiple = true;
        }

        // Обработчик изменения файлов
        this.input.addEventListener('change', (event) => {
            this.handleFiles(event.target.files);
        });
    }

    setupDragAndDrop() {
        const container = this.findUploadContainer();
        if (!container) return;

        // Предотвращаем стандартное поведение браузера
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            container.addEventListener(eventName, this.preventDefaults, false);
            document.body.addEventListener(eventName, this.preventDefaults, false);
        });

        // Подсветка при наведении
        ['dragenter', 'dragover'].forEach(eventName => {
            container.addEventListener(eventName, () => {
                this.dragCounter++;
                this.highlight(container);
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            container.addEventListener(eventName, () => {
                this.dragCounter--;
                if (this.dragCounter <= 0) {
                    this.dragCounter = 0;
                    this.unhighlight(container);
                }
            }, false);
        });

        // Обработка drop
        container.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            this.handleFiles(files);
        }, false);
    }

    findUploadContainer() {
        // Ищем контейнер для drag & drop
        let container = this.input.closest('.file-upload-container');
        if (!container) {
            container = this.input.closest('.upload-area');
        }
        if (!container) {
            container = this.input.parentElement;
        }
        return container;
    }

    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    highlight(container) {
        container.classList.add('drag-over');
        container.style.borderColor = 'var(--primary-color, #4361ee)';
        container.style.backgroundColor = 'rgba(67, 97, 238, 0.1)';
        container.style.transform = 'scale(1.02)';
    }

    unhighlight(container) {
        container.classList.remove('drag-over');
        container.style.borderColor = '';
        container.style.backgroundColor = '';
        container.style.transform = '';
    }

    handleFiles(files) {
        if (!files || files.length === 0) return;

        const fileArray = Array.from(files);
        
        // Валидация файлов
        for (const file of fileArray) {
            const validation = this.validateFile(file);
            if (!validation.valid) {
                this.handleError(validation.error);
                return;
            }
        }

        // Сохраняем файлы
        if (this.options.multiple) {
            this.files = [...this.files, ...fileArray];
        } else {
            this.files = [fileArray[0]];
        }

        // Уведомляем о выборе файлов
        if (this.options.onFileSelect) {
            this.options.onFileSelect(this.options.multiple ? this.files : this.files[0]);
        }

        // Обновляем input
        this.updateInputFiles();
    }

    validateFile(file) {
        // Проверка размера
        if (file.size > this.options.maxSize) {
            return {
                valid: false,
                error: `Файл "${file.name}" слишком большой. Максимальный размер: ${this.formatFileSize(this.options.maxSize)}`
            };
        }

        // Проверка типа файла
        if (this.options.allowedTypes.length > 0) {
            const fileExtension = file.name.split('.').pop().toLowerCase();
            const mimeType = file.type.toLowerCase();
            
            const isValidExtension = this.options.allowedTypes.some(type => 
                type.startsWith('.') ? type.slice(1) === fileExtension : type === mimeType
            );

            if (!isValidExtension) {
                return {
                    valid: false,
                    error: `Файл "${file.name}" имеет недопустимый формат. Разрешены: ${this.options.allowedTypes.join(', ')}`
                };
            }
        }

        return { valid: true };
    }

    updateInputFiles() {
        // Создаем новый FileList (hack для совместимости)
        const dt = new DataTransfer();
        this.files.forEach(file => dt.items.add(file));
        this.input.files = dt.files;
    }

    handleError(error) {
        
        if (this.options.onError) {
            this.options.onError(error);
        } else {
            showNotification(error, 'error');
        }
    }

    // Утилиты
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Публичные методы
    getFiles() {
        return this.files;
    }

    hasFile() {
        return this.files.length > 0;
    }

    reset() {
        this.files = [];
        this.input.value = '';
        
        // Убираем подсветку
        const container = this.findUploadContainer();
        if (container) {
            this.unhighlight(container);
        }
    }

    addFile(file) {
        const validation = this.validateFile(file);
        if (!validation.valid) {
            this.handleError(validation.error);
            return false;
        }

        if (this.options.multiple) {
            this.files.push(file);
        } else {
            this.files = [file];
        }

        this.updateInputFiles();
        
        if (this.options.onFileSelect) {
            this.options.onFileSelect(this.options.multiple ? this.files : this.files[0]);
        }

        return true;
    }

    removeFile(index) {
        if (index >= 0 && index < this.files.length) {
            this.files.splice(index, 1);
            this.updateInputFiles();
        }
    }

    // Загрузка файла с прогрессом
    async uploadFile(file, url, options = {}) {
        const formData = new FormData();
        formData.append(options.fieldName || 'file', file);

        // Добавляем дополнительные поля
        if (options.extraFields) {
            Object.entries(options.extraFields).forEach(([key, value]) => {
                formData.append(key, value);
            });
        }

        try {
            const response = await fetch(url, {
                method: 'POST',
                body: formData,
                ...options.fetchOptions
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return response;
        } catch (error) {
            this.handleError(`Ошибка загрузки файла: ${error.message}`);
            throw error;
        }
    }

    // Загрузка с прогрессом (более продвинутая версия)
    uploadWithProgress(file, url, options = {}) {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            const formData = new FormData();
            
            formData.append(options.fieldName || 'file', file);
            
            if (options.extraFields) {
                Object.entries(options.extraFields).forEach(([key, value]) => {
                    formData.append(key, value);
                });
            }

            // Отслеживание прогресса
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const percentComplete = (e.loaded / e.total) * 100;
                    if (this.options.onProgress) {
                        this.options.onProgress(percentComplete, e.loaded, e.total);
                    }
                }
            });

            xhr.addEventListener('load', () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    resolve(xhr.response);
                } else {
                    reject(new Error(`HTTP error! status: ${xhr.status}`));
                }
            });

            xhr.addEventListener('error', () => {
                reject(new Error('Network error'));
            });

            xhr.open('POST', url);
            xhr.send(formData);
        });
    }
}

// Утилитарные функции для совместимости
export function createFileUploadArea(containerId, options = {}) {
    const container = $(containerId);
    if (!container) return null;

    const input = container.querySelector('input[type="file"]');
    if (!input) {
        return null;
    }

    return new FileUpload(input, options);
}

export function validateFileType(file, allowedTypes) {
    if (!allowedTypes || allowedTypes.length === 0) return true;
    
    const fileExtension = file.name.split('.').pop().toLowerCase();
    const mimeType = file.type.toLowerCase();
    
    return allowedTypes.some(type => {
        if (type.startsWith('.')) {
            return type.slice(1) === fileExtension;
        }
        return type === mimeType;
    });
}

export function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}