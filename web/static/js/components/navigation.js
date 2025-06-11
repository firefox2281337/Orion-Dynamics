/**
 * 🧭 Компонент навигации
 */
import { $$, delay } from '../core/utils.js';

export class Navigation {
    constructor() {
        this.navLinks = $$('.navbar-nav .nav-link');
        this.init();
    }

    init() {
        this.setupNavigation();
        this.setupAnimations();
    }

    setupNavigation() {
        this.navLinks.forEach(link => {
            link.addEventListener('click', (event) => {
                this.setActiveLink(link);
            });
        });
    }

    setActiveLink(activeLink) {
        this.navLinks.forEach(link => link.classList.remove('active'));
        activeLink.classList.add('active');
    }

    async setupAnimations() {
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-fade-in');
                }
            });
        }, observerOptions);

        document.querySelectorAll('.dashboard-card, .metric-card').forEach(card => {
            observer.observe(card);
        });
    }
}