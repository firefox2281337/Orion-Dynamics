"""
Утилиты для работы с Nexus
Дополнительные функции для расширения функциональности
"""

from .nexus_config import PAGE_CONFIGS, BUTTON_CONFIGS, AUTOREG_CONFIGS, AUTODAILYES_CONFIGS

class NexusPageBuilder:
    """Класс для динамического создания страниц Nexus"""
    
    @staticmethod
    def create_custom_page(title, subtitle, buttons, show_steps=False, current_step=1, random_slogan=False):
        """Создание кастомной страницы"""
        return {
            'title': title,
            'subtitle': subtitle,
            'config': {
                'randomSlogan': random_slogan,
                'showSteps': show_steps,
                'currentStep': current_step,
                'buttons': buttons
            }
        }
    
    @staticmethod
    def add_back_button(buttons, back_url, back_message="Назад"):
        """Добавление кнопки "Назад" к списку кнопок"""
        back_button = {
            'icon': 'fas fa-arrow-left',
            'text': back_message,
            'url': back_url,
            'message': f'Возврат к {back_message.lower()}'
        }
        return buttons + [back_button]
    
    @staticmethod
    def create_button(icon, text, url=None, message=None, disabled=False, badge=None, disabled_message=None):
        """Создание отдельной кнопки"""
        button = {
            'icon': icon,
            'text': text
        }
        
        if disabled:
            button['disabled'] = True
            button['disabledMessage'] = disabled_message or f'{text} в разработке'
            if badge:
                button['badge'] = badge
        else:
            button['url'] = url
            button['message'] = message or f'Переход к модулю "{text}"'
        
        return button

def get_page_config(page_key):
    """Получение конфигурации страницы по ключу"""
    return PAGE_CONFIGS.get(page_key, PAGE_CONFIGS['main'])

def get_autodailyes_config(autodailyes_key):
    """Получение конфигурации автоежедневки по ключу"""
    return AUTODAILYES_CONFIGS.get(autodailyes_key, AUTODAILYES_CONFIGS['autodeals'])

def get_autoreg_config(autoreg_key):
    """Получение конфигурации автореестра по ключу"""
    return AUTOREG_CONFIGS.get(autoreg_key, AUTOREG_CONFIGS['ipoteka'])

def get_buttons_config(config_key):
    """Получение конфигурации кнопок по ключу"""
    return BUTTON_CONFIGS.get(config_key, [])

def extend_page_config(page_key, **kwargs):
    """Расширение существующей конфигурации страницы"""
    config = get_page_config(page_key).copy()
    
    for key, value in kwargs.items():
        if key in config:
            config[key] = value
        elif key in config['config']:
            config['config'][key] = value
    
    return config

# Предустановленные конфигурации для часто используемых типов страниц
PRESET_CONFIGS = {
    'processing_page': {
        'showSteps': True,
        'currentStep': 2,
        'randomSlogan': False
    },
    
    'mapping_page': {
        'showSteps': True,
        'currentStep': 3,
        'randomSlogan': False
    },
    
    'result_page': {
        'showSteps': True,
        'currentStep': 4,
        'randomSlogan': False
    }
}