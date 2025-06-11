/**
 * 💾 Модуль страницы загрузок
 */
import { $, $$, showNotification, debounce } from '../core/utils.js';

export class SoftwarePage {
    constructor() {
        this.searchInput = $('#searchInput');
        this.categoryBadges = $$('.category-badge');
        this.fileItems = $$('.file-item');
        this.emptyState = $('.empty-state');
        this.showAllBtn = $('#showAllFilesBtn');
        this.previewModal = $('#filePreviewModal');
        
        this.init();
    }

    init() {
        this.setupSearch();
        this.setupCategoryFilter();
        this.setupShowAllButton();
        this.setupPreviewModal();
        this.setupAnimations();
    }

    setupSearch() {
        if (!this.searchInput) return;

        const debouncedSearch = debounce((searchValue) => {
            this.filterFiles(searchValue.toLowerCase());
        }, 300);

        this.searchInput.addEventListener('input', (e) => {
            debouncedSearch(e.target.value);
        });
    }

    filterFiles(searchValue) {
        let found = false;
        
        this.fileItems.forEach(item => {
            const fileName = item.querySelector('.file-name')?.textContent.toLowerCase() || '';
            if (fileName.includes(searchValue)) {
                item.style.display = 'flex';
                found = true;
            } else {
                item.style.display = 'none';
            }
        });
        
        this.updateVisibility(found);
    }

    setupCategoryFilter() {
        this.categoryBadges.forEach(badge => {
            badge.addEventListener('click', () => {
                this.setActiveCategory(badge);
                this.filterByCategory(badge.dataset.category);
            });
        });
    }

    setActiveCategory(activeBadge) {
        this.categoryBadges.forEach(badge => badge.classList.remove('active'));
        activeBadge.classList.add('active');
    }

    filterByCategory(selectedCategory) {
        const fileBlocks = $$('.file-category-block');
        let found = false;
        
        if (selectedCategory === 'all') {
            fileBlocks.forEach(block => {
                block.style.display = 'block';
                block.querySelectorAll('.file-item').forEach(item => {
                    item.style.display = 'flex';
                    found = true;
                });
            });
        } else {
            this.fileItems.forEach(item => {
                if (item.dataset.category === selectedCategory) {
                    item.style.display = 'flex';
                    found = true;
                } else {
                    item.style.display = 'none';
                }
            });
            
            fileBlocks.forEach(block => {
                const visibleItems = block.querySelectorAll('.file-item[style*="flex"]');
                block.style.display = visibleItems.length > 0 ? 'block' : 'none';
            });
        }
        
        this.updateVisibility(found);
    }

    setupShowAllButton() {
        if (!this.showAllBtn) return;

        this.showAllBtn.addEventListener('click', () => {
            if (this.searchInput) this.searchInput.value = '';
            
            this.fileItems.forEach(item => item.style.display = 'flex');
            $$('.file-category-block').forEach(block => block.style.display = 'block');
            
            this.setActiveCategory($('.category-badge[data-category="all"]'));
            this.updateVisibility(true);
        });
    }

    updateVisibility(found) {
        if (!this.emptyState) return;

        const categoryBlocks = $$('.file-category-block');
        
        if (found) {
            this.emptyState.style.display = 'none';
            categoryBlocks.forEach(block => {
                const visibleItems = block.querySelectorAll('.file-item[style*="flex"]');
                if (visibleItems.length === 0) {
                    block.style.display = 'none';
                }
            });
        } else {
            this.emptyState.style.display = 'block';
            categoryBlocks.forEach(block => block.style.display = 'none');
        }
    }

    setupPreviewModal() {
        // Закрытие по клику вне области
        document.addEventListener('click', (e) => {
            if (e.target === this.previewModal) {
                this.closePreview();
            }
        });

        // Закрытие по Escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.previewModal?.classList.contains('active')) {
                this.closePreview();
            }
        });
    }

    setupAnimations() {
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }
            });
        }, observerOptions);

        this.fileItems.forEach((item, index) => {
            item.style.opacity = '0';
            item.style.transform = 'translateY(20px)';
            item.style.transition = `opacity 0.6s ease ${index * 0.1}s, transform 0.6s ease ${index * 0.1}s`;
            observer.observe(item);
        });
    }

    async previewFile(fileId) {
        if (!this.previewModal) return;

        const loading = $('#previewLoading');
        const content = $('#previewContent');
        const previewFileName = $('#previewFileName');
        const previewFileIcon = $('#previewFileIcon');
        const downloadBtn = $('#downloadBtn');
        
        this.previewModal.classList.add('active');
        if (loading) loading.style.display = 'block';
        if (content) content.innerHTML = loading?.outerHTML || '';
        
        document.body.style.overflow = 'hidden';
        
        try {
            const response = await fetch(`/files/preview/${fileId}`);
            if (!response.ok) {
                throw new Error(`Ошибка HTTP: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (previewFileName) previewFileName.textContent = data.name;
            if (previewFileIcon) previewFileIcon.className = `fas fa-${data.icon}`;
            if (content) content.innerHTML = this.generatePreviewContent(data);
            
            if (downloadBtn) {
                downloadBtn.onclick = () => this.downloadFile(fileId);
            }
            
        } catch (error) {
            if (content) {
                content.innerHTML = `
                    <div class="alert alert-warning">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        Не удалось загрузить предпросмотр: ${error.message}
                    </div>
                `;
            }
        }
    }

    generatePreviewContent(data) {
        switch (data.preview_type) {
            case 'text':
                return `<pre style="white-space: pre-wrap; background: #f8f9fa; padding: 1rem; border-radius: 8px;">${data.content}</pre>`;
            case 'image':
                return `<div class="text-center"><img src="${data.content}" alt="Preview" style="max-width: 100%; max-height: 60vh; object-fit: contain;"></div>`;
            case 'error':
            case 'unsupported':
            default:
                return `
                    <div class="alert alert-info">
                        <i class="fas fa-info-circle me-2"></i>
                        ${data.content || 'Предпросмотр недоступен для данного типа файла'}
                    </div>
                `;
        }
    }

    closePreview() {
        if (this.previewModal) {
            this.previewModal.classList.remove('active');
        }
        document.body.style.overflow = '';
    }

    downloadFile(fileId) {
        showNotification('Скачивание началось...', 'info');
        window.location.href = `/files/download/${fileId}`;
    }
}

// Экспортируем глобальные функции для совместимости
window.previewFile = (fileId) => {
    const page = window.OrionApp?.getComponent('softwarePage');
    if (page) page.previewFile(fileId);
};

window.downloadFile = (fileId) => {
    const page = window.OrionApp?.getComponent('softwarePage');
    if (page) page.downloadFile(fileId);
};

window.closePreview = () => {
    const page = window.OrionApp?.getComponent('softwarePage');
    if (page) page.closePreview();
};