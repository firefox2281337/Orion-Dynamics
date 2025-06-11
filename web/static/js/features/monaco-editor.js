/**
 * 📝 Monaco Editor компонент
 */
import { showNotification } from '../core/utils.js';
import { MONACO_THEMES } from '../core/config.js';

export class MonacoEditor {
    constructor(containerId, options = {}) {
        this.container = typeof containerId === 'string' ? 
            document.querySelector(containerId) : containerId;
        this.editor = null;
        this.isLoaded = false;
        
        this.options = {
            language: 'sql',
            theme: 'vs',
            automaticLayout: true,
            minimap: { enabled: true },
            fontSize: 16,
            lineNumbers: 'on',
            scrollBeyondLastLine: false,
            wordWrap: 'on',
            tabSize: 2,
            insertSpaces: true,
            formatOnPaste: true,
            formatOnType: true,
            padding: { top: 10, bottom: 10 },
            lineHeight: 24,
            letterSpacing: 0.5,
            cursorBlinking: 'blink',
            cursorSmoothCaretAnimation: true,
            smoothScrolling: true,
            mouseWheelZoom: true,
            contextmenu: true,
            selectOnLineNumbers: true,
            roundedSelection: false,
            renderLineHighlight: 'all',
            matchBrackets: 'always',
            ...options
        };

        this.init();
    }

    async init() {
        if (!this.container) {
            return;
        }

        try {
            await this.loadMonaco();
            await this.createEditor();
            this.setupThemeSync();
        } catch (error) {
            showNotification('Ошибка загрузки редактора кода', 'error');
        }
    }

    loadMonaco() {
        return new Promise((resolve, reject) => {
            // Проверяем, загружен ли Monaco
            if (typeof monaco !== 'undefined') {
                resolve();
                return;
            }

            // Загружаем Monaco Editor
            const script = document.createElement('script');
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.34.1/min/vs/loader.min.js';
            script.onload = () => {
                require.config({ 
                    paths: { 
                        'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.34.1/min/vs' 
                    } 
                });
                
                require(['vs/editor/editor.main'], () => {
                    this.isLoaded = true;
                    resolve();
                });
            };
            script.onerror = () => reject(new Error('Не удалось загрузить Monaco Editor'));
            document.head.appendChild(script);
        });
    }

    async createEditor() {
        if (!this.isLoaded || !this.container) return;

        // Определяем тему на основе текущего состояния
        const currentTheme = this.getCurrentTheme();
        this.options.theme = MONACO_THEMES[currentTheme] || 'vs';

        this.editor = monaco.editor.create(this.container, this.options);

        // Настраиваем автоматическое изменение размера
        setTimeout(() => {
            if (this.editor) {
                this.editor.layout();
                this.editor.focus();
            }
        }, 100);

        // Обработчик изменения размера окна
        window.addEventListener('resize', () => {
            if (this.editor) {
                this.editor.layout();
            }
        });
    }

    setupThemeSync() {
        // Следим за изменениями темы приложения
        const observer = new MutationObserver(() => {
            this.syncTheme();
        });

        observer.observe(document.body, {
            attributes: true,
            attributeFilter: ['class']
        });

        // Следим за изменениями localStorage
        window.addEventListener('storage', (e) => {
            if (e.key === 'darkMode') {
                this.syncTheme();
            }
        });
    }

    syncTheme() {
        if (!this.editor || typeof monaco === 'undefined') return;

        const currentTheme = this.getCurrentTheme();
        const monacoTheme = MONACO_THEMES[currentTheme] || 'vs';
        
        monaco.editor.setTheme(monacoTheme);
        
        // Применяем тему ко всем редакторам на странице
        const editors = monaco.editor.getEditors();
        editors.forEach(() => monaco.editor.setTheme(monacoTheme));
    }

    getCurrentTheme() {
        // Проверяем localStorage
        if (localStorage.getItem('darkMode') === 'true') {
            return 'dark';
        }
        
        // Проверяем класс body
        if (document.body.classList.contains('dark-mode')) {
            return 'dark';
        }
        
        return 'light';
    }

    getValue() {
        return this.editor ? this.editor.getValue() : '';
    }

    setValue(value) {
        if (this.editor) {
            this.editor.setValue(value || '');
        }
    }

    focus() {
        if (this.editor) {
            this.editor.focus();
        }
    }

    layout() {
        if (this.editor) {
            this.editor.layout();
        }
    }

    dispose() {
        if (this.editor) {
            this.editor.dispose();
            this.editor = null;
        }
    }

    // Дополнительные методы для SQL редактора
    insertText(text) {
        if (!this.editor) return;
        
        const selection = this.editor.getSelection();
        const operation = {
            range: selection,
            text: text,
            forceMoveMarkers: true
        };
        this.editor.executeEdits('insert-text', [operation]);
    }

    getSelectedText() {
        if (!this.editor) return '';
        
        const selection = this.editor.getSelection();
        return this.editor.getModel().getValueInRange(selection);
    }

    formatCode() {
        if (this.editor) {
            this.editor.trigger('editor', 'editor.action.formatDocument');
        }
    }

    // Автодополнение для SQL
    setupSqlCompletion() {
        if (typeof monaco === 'undefined') return;

        monaco.languages.registerCompletionItemProvider('sql', {
            provideCompletionItems: (model, position) => {
                const suggestions = [
                    {
                        label: 'SELECT',
                        kind: monaco.languages.CompletionItemKind.Keyword,
                        insertText: 'SELECT ',
                        documentation: 'SELECT statement'
                    },
                    {
                        label: 'FROM',
                        kind: monaco.languages.CompletionItemKind.Keyword,
                        insertText: 'FROM ',
                        documentation: 'FROM clause'
                    },
                    {
                        label: 'WHERE',
                        kind: monaco.languages.CompletionItemKind.Keyword,
                        insertText: 'WHERE ',
                        documentation: 'WHERE clause'
                    },
                    {
                        label: 'ORDER BY',
                        kind: monaco.languages.CompletionItemKind.Keyword,
                        insertText: 'ORDER BY ',
                        documentation: 'ORDER BY clause'
                    },
                    {
                        label: 'GROUP BY',
                        kind: monaco.languages.CompletionItemKind.Keyword,
                        insertText: 'GROUP BY ',
                        documentation: 'GROUP BY clause'
                    }
                ];

                return { suggestions };
            }
        });
    }
}

// Глобальная функция для инициализации темы Monaco (совместимость)
export function initializeMonacoWithTheme() {
    if (typeof monaco === 'undefined') return 'vs';
    
    const isDarkMode = document.body.classList.contains('dark-mode') || 
                       localStorage.getItem('darkMode') === 'true';
    const theme = isDarkMode ? 'vs-dark' : 'vs';
    
    monaco.editor.setTheme(theme);
    return theme;
}

// Глобальная функция для обновления темы конкретного редактора
export function updateMonacoEditorTheme(editor) {
    if (!editor || typeof monaco === 'undefined') return;
    
    const isDarkMode = document.body.classList.contains('dark-mode') || 
                       localStorage.getItem('darkMode') === 'true';
    const theme = isDarkMode ? 'vs-dark' : 'vs';
    monaco.editor.setTheme(theme);
}