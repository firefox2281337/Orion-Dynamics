/**
 * 💬 Менеджер тултипов Bootstrap
 */
export class TooltipManager {
    constructor() {
        this.tooltips = [];
        this.init();
    }

    init() {
        if (typeof bootstrap !== 'undefined') {
            this.initializeTooltips();
        } else {
        }
    }

    initializeTooltips() {
        const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        this.tooltips = Array.from(tooltipTriggerList).map(tooltipTriggerEl => 
            new bootstrap.Tooltip(tooltipTriggerEl)
        );
    }

    refresh() {
        this.dispose();
        this.initializeTooltips();
    }

    dispose() {
        this.tooltips.forEach(tooltip => tooltip.dispose());
        this.tooltips = [];
    }
}