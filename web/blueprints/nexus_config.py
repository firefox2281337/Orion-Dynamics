"""
Конфигурация страниц Nexus
Централизованное хранение всех конфигураций страниц
"""

# Базовая конфигурация кнопок
BUTTON_CONFIGS = {
    'main': [
        {
            'icon': 'fas fa-file-contract',
            'text': 'Автореестры',
            'url': '/nexus/autoreg',
            'message': 'Переход к модулю "Автореестры"'
        },
        {
            'icon': 'fas fa-calendar-day',
            'text': 'Автоежедневки',
            'url': '/nexus/autodailyes',
            'message': 'Переход к модулю "Автоежедневки"'
        },
        {
            'icon': 'fas fa-chart-line',
            'text': 'Loginom',
            'disabled': True,
            'badge': 'В разработке',
            'disabledMessage': 'Модуль "Loginom" находится в разработке'
        }
    ],
    
    'autoreg': [
        {
            'icon': 'fas fa-file-signature',
            'text': 'Пролонгация',
            'url': '/nexus/autoreg/prolong',
            'message': 'Переход к модулю "Пролонгация"'
        },
        {
            'icon': 'fas fa-search',
            'text': 'Потеряшки',
            'url': '/nexus/autoreg/olds',
            'message': 'Переход к модулю "Потеряшки"'
        },
        {
            'icon': 'fas fa-vial',
            'text': 'Пилоты',
            'url': '/nexus/autoreg/pilots',
            'message': 'Переход к модулю "Пилоты"'
        },
        {
            'icon': 'fas fa-arrow-left',
            'text': 'Назад',
            'url': '/nexus',
            'message': 'Возврат к модулю "Nexus"'
        }
    ],
    
    'prolong': [
        {
            'icon': 'fas fa-home',
            'text': 'Ипотека',
            'url': '/nexus/autoreg/prolong/ipoteka',
            'message': 'Переход к модулю "Ипотека"'
        },
        {
            'icon': 'fas fa-city',
            'text': 'Ипотека МСК',
            'url': '/nexus/autoreg/prolong/ipoteka-msk',
            'message': 'Переход к модулю "Ипотека МСК"'
        },
        {
            'icon': 'fas fa-car-crash',
            'text': 'КАСКО',
            'url': '/nexus/autoreg/prolong/kasko',
            'message': 'Переход к модулю "КАСКО"'
        },
        {
            'icon': 'fas fa-shield-alt',
            'text': 'КАСКО по ОСАГО',
            'url': '/nexus/autoreg/prolong/kasko-iz-osago',
            'message': 'Переход к модулю "КАСКО по ОСАГО"'
        },
        {
            'icon': 'fas fa-car',
            'text': 'ОСАГО',
            'url': '/nexus/autoreg/prolong/osago',
            'message': 'Переход к модулю "ОСАГО"'
        },
        {
            'icon': 'fas fa-heart',
            'text': 'МБГ',
            'url': '/nexus/autoreg/prolong/mbg',
            'message': 'Переход к модулю "МБГ"'
        },
        {
            'icon': 'fas fa-arrow-left',
            'text': 'Назад',
            'url': '/nexus/autoreg',
            'message': 'Возврат к модулю "Автореестры"'
        }
    ],
    
    'olds': [
        {
            'icon': 'fas fa-home',
            'text': 'Ипотека Потеряшки WA',
            'url': '/nexus/autoreg/olds/ipowa',
            'message': 'Переход к модулю "Ипотека Потеряшки WA"'
        },
        {
            'icon': 'fas fa-car',
            'text': 'ОСАГО Потеряшки WA',
            'url': '/nexus/autoreg/olds/osagowa',
            'message': 'Переход к модулю "ОСАГО Потеряшки WA"'
        },
        {
            'icon': 'fas fa-map-marker-alt',
            'text': 'ОСАГО Потеряшки 4.1 Москва',
            'url': '/nexus/autoreg/olds/osago41',
            'message': 'Переход к модулю "ОСАГО Потеряшки 4.1 Москва"'
        },
        {
            'icon': 'fas fa-arrow-left',
            'text': 'Назад',
            'url': '/nexus/autoreg',
            'message': 'Возврат к модулю "Автореестры"'
        }
    ],
    
    'pilots': [
        {
            'icon': 'fas fa-flag',
            'text': 'ОСАГО КЗ',
            'url': '/nexus/autoreg/pilots/osago_kz',
            'message': 'Переход к модулю "ОСАГО КЗ"'
        },
        {
            'icon': 'fas fa-exclamation-triangle',
            'text': 'Ипотека SOS',
            'url': '/nexus/autoreg/pilots/ipoteka_sos',
            'message': 'Переход к модулю "Ипотека SOS"'
        },
        {
            'icon': 'fas fa-university',
            'text': 'Ипотека ком. банки',
            'url': '/nexus/autoreg/pilots/ipoteka_kom_bank',
            'message': 'Переход к модулю "Ипотека ком. банки"'
        },
        {
            'icon': 'fas fa-hand-holding-usd',
            'text': 'Проект «Деньги вместо ремонта»',
            'url': '/nexus/autoreg/pilots/dvr',
            'message': 'Переход к модулю "ДВР"'
        },
        {
            'icon': 'fas fa-flag',
            'text': 'OneFactor',
            'url': '/nexus/autoreg/pilots/f1',
            'message': 'Переход к модулю "1f"'
        },
        {
            'icon': 'fas fa-arrow-left',
            'text': 'Назад',
            'url': '/nexus/autoreg',
            'message': 'Возврат к модулю "Автореестры"'
        }
    ],
    
    'autodailyes': [
        {
            'icon': 'fas fa-calendar-check',
            'text': 'Ежедневные',
            'url': '/nexus/autodailyes/dailyes',
            'message': 'Переход к модулю "Ежедневные"'
        },
        {
            'icon': 'fas fa-calendar-week',
            'text': 'Еженедельные',
            'url': '/nexus/autodailyes/weeks',
            'message': 'Переход к модулю "Еженедельные"'
        },
        {
            'icon': 'fas fa-arrow-left',
            'text': 'Назад',
            'url': '/nexus',
            'message': 'Возврат к модулю "Nexus"'
        }
    ],
    
    'dailyes': [
        {
            'icon': 'fas fa-robot',
            'text': 'Джарвис',
            'url': '/nexus/autodailyes/dailyes/autojarvis',
            'message': 'Переход к модулю "Джарвис"'
        },
        {
            'icon': 'fas fa-search',
            'text': 'Потеряшки',
            'url': '/nexus/autodailyes/dailyes/autoolds',
            'message': 'Переход к модулю "Потеряшки"'
        },
        {
            'icon': 'fas fa-handshake',
            'text': 'Сделки',
            'url': '/nexus/autodailyes/dailyes/autodeals',
            'message': 'Переход к модулю "Сделки"'
        },
        {
            'icon': 'fas fa-headset',
            'text': 'Веринт',
            'url': '/nexus/autodailyes/dailyes/autoverint',
            'message': 'Переход к модулю "Веринт"'
        },
        {
            'icon': 'fas fa-arrow-left',
            'text': 'Назад',
            'url': '/nexus/autodailyes',
            'message': 'Возврат к модулю "Автоежедневки"'
        }
    ],
    
    'weeks': [
        {
            'icon': 'fas fa-tasks',
            'text': 'Проверка кампаний',
            'url': '/nexus/autodailyes/weeks/autochekcompany',
            'message': 'Переход к модулю "Проверка кампаний"'
        },
        {
            'icon': 'fas fa-arrow-left',
            'text': 'Назад',
            'url': '/nexus/autodailyes',
            'message': 'Возврат к модулю "Автоежедневки"'
        }
    ]
}

# Конфигурация страниц
PAGE_CONFIGS = {
    'main': {
        'title': 'Nexus',
        'subtitle': '',
        'config': {
            'randomSlogan': True,
            'showSteps': False,
            'buttons': BUTTON_CONFIGS['main']
        }
    },
    
    'autoreg': {
        'title': 'Nexus - выбор типа базы',
        'subtitle': 'Выбор типа базы:',
        'config': {
            'randomSlogan': False,
            'showSteps': True,
            'currentStep': 1,
            'buttons': BUTTON_CONFIGS['autoreg']
        }
    },
    
    'prolong': {
        'title': 'Nexus - выбор типа лида',
        'subtitle': 'Выбор типа реестра:',
        'config': {
            'randomSlogan': False,
            'showSteps': True,
            'currentStep': 1,
            'buttons': BUTTON_CONFIGS['prolong']
        }
    },
    
    'olds': {
        'title': 'Nexus - выбор типа лида',
        'subtitle': 'Выбор типа реестра:',
        'config': {
            'randomSlogan': False,
            'showSteps': True,
            'currentStep': 1,
            'buttons': BUTTON_CONFIGS['olds']
        }
    },
    
    'pilots': {
        'title': 'Nexus - выбор типа лида',
        'subtitle': 'Выбор типа реестра:',
        'config': {
            'randomSlogan': False,
            'showSteps': True,
            'currentStep': 1,
            'buttons': BUTTON_CONFIGS['pilots']
        }
    },
    
    'autodailyes': {
        'title': 'Nexus - выбор периода',
        'subtitle': 'Выбор периодичности:',
        'config': {
            'randomSlogan': False,
            'showSteps': False,
            'buttons': BUTTON_CONFIGS['autodailyes']
        }
    },
    
    'dailyes': {
        'title': 'Nexus - выбор задачи',
        'subtitle': 'Выбор задачи:',
        'config': {
            'randomSlogan': False,
            'showSteps': False,
            'buttons': BUTTON_CONFIGS['dailyes']
        }
    },
    
    'weeks': {
        'title': 'Nexus - выбор задачи',
        'subtitle': 'Выбор задачи:',
        'config': {
            'randomSlogan': False,
            'showSteps': False,
            'buttons': BUTTON_CONFIGS['weeks']
        }}}

# Конфигурация автоежедневок
AUTODAILYES_CONFIGS = {
    'autodeals': {
        'title': 'Автосделки - обработка файлов сделок',
        'mainTitle': 'Автосделки',
        'subtitle': 'Обработка файлов сделок',
        'icon': 'fas fa-handshake',
        'sectionTitle': 'Перетащите или выберите файлы',
        'initialStatusText': 'Файлы не выбраны',
        'config': {
            'multiple': True,
            'minFiles': 3,
            'backUrl': '/nexus/autodailyes/dailyes',
            'downloadPrefix': 'Сделки',
            'dragDropText': '''Перетащите сюда файлы:<br>
1. Файл сделок (должен начинаться с "Сделки").<br>
2. Файл проверки (должен начинаться с "Проверка").<br>
3. Файл сотрудников (должен начинаться с "empl").<br><br>
Также вместо перетаскивания можно нажать на область ЛКМ и выбрать файлы''',
            'apiEndpoints': {
                'process': '/registry/process',
                'status': '/registry/status',
                'download': '/registry/download',
                'cancel': '/registry/cancel'
            },
            'fileRules': [
                {'prefix': 'Сделки', 'type': 'Сделки', 'required': True},
                {'prefix': 'Проверка', 'type': 'Проверка', 'required': True},
                {'prefix': 'empl', 'type': 'Сотрудники', 'required': True}
            ],
            'statusTexts': {
                'empty': 'Файлы не выбраны'
            }
        }
    },
    
    'autojarvis': {
        'title': 'Автоджарвис - Обработка данных Ипотеки',
        'mainTitle': 'Автоджарвис',
        'subtitle': 'Обработка данных Ипотеки',
        'icon': 'fas fa-robot',
        'sectionTitle': 'Перетащите или выберите файлы',
        'initialStatusText': 'Файлы не выбраны',
        'config': {
            'multiple': True,
            'minFiles': 3,
            'backUrl': '/nexus/autodailyes/dailyes',
            'downloadPrefix': 'Джарвис',
            'dragDropText': '''Перетащите сюда файлы:<br>
1. Файлы продаж (должны начинаться с "Prodagi_VSK")<br>
2. Файл не пролонгированных (должен начинаться с "не+прол")<br>
3. Файл сотрудников (должен начинаться с "employ")<br><br>
Также вместо перетаскивания можно нажать на область ЛКМ и выбрать файлы''',
            'apiEndpoints': {
                'process': '/jarvis/process',
                'status': '/jarvis/status',
                'download': '/jarvis/download',
                'cancel': '/jarvis/cancel'
            },
            'fileRules': [
                {'prefix': 'Prodagi_VSK', 'type': 'Продажи VSK', 'required': True},
                {'prefix': 'не+прол', 'type': 'Не пролонгированные', 'required': True},
                {'prefix': 'employ', 'type': 'Сотрудники', 'required': True}
            ],
            'statusTexts': {
                'empty': 'Файлы не выбраны'
            }
        }
    },
    
    'autoolds': {
        'title': 'Автопотеряшки - Обработка потерянных договоров',
        'mainTitle': 'Автопотеряшки',
        'subtitle': 'Обработка потерянных договоров',
        'icon': 'fas fa-search',
        'sectionTitle': 'Перетащите или выберите файл',
        'initialStatusText': 'Файл не выбран',
        'config': {
            'multiple': False,
            'minFiles': 1,
            'backUrl': '/nexus/autodailyes/dailyes',
            'downloadPrefix': 'Потеряшки',
            'dragDropText': '''Перетащите сюда файл договоров:<br>
Файл должен начинаться с "Договора+по"<br><br>
Также вместо перетаскивания можно нажать на область ЛКМ и выбрать файл''',
            'apiEndpoints': {
                'process': '/lost_contracts/process',
                'status': '/lost_contracts/status',
                'download': '/lost_contracts/download',
                'cancel': '/lost_contracts/cancel'
            },
            'fileRules': [
                {'prefix': 'Договора+по', 'type': 'Договора', 'required': True}
            ],
            'statusTexts': {
                'empty': 'Файл не выбран'
            }
        }
    },
    
    'autoverint': {
        'title': 'Автоверинт - Обработка заметок РА',
        'mainTitle': 'Автоверинт',
        'subtitle': 'Обработка заметок РА',
        'icon': 'fas fa-headset',
        'sectionTitle': 'Перетащите или выберите файлы',
        'initialStatusText': 'Файлы не выбраны',
        'config': {
            'multiple': True,
            'minFiles': 2,
            'backUrl': '/nexus/autodailyes/dailyes',
            'downloadPrefix': 'Веринт',
            'dragDropText': '''Перетащите сюда файлы:<br>
1. Выгрузка из Verint (Название файла должно начинаться с "Речевая").<br>
2. Выгрузка из сущности Звонок (Название файла должно начинаться с "call").<br><br>
Также вместо перетаскивания можно нажать на область ЛКМ и выбрать файлы''',
            'apiEndpoints': {
                'process': '/processing/process',
                'status': '/processing/status',
                'download': '/processing/download',
                'cancel': '/processing/cancel'
            },
            'fileRules': [
                {'prefix': 'Речевая', 'type': 'Verint', 'required': True},
                {'prefix': 'call', 'type': 'Звонки', 'required': True}
            ],
            'statusTexts': {
                'empty': 'Файлы не выбраны'
            }
        }
    },
    
    'autochekcompany': {
        'title': 'Автокампании - Проверка кампаний',
        'mainTitle': 'Автокампании',
        'subtitle': 'Проверка кампаний',
        'icon': 'fas fa-tasks',
        'sectionTitle': 'Перетащите или выберите файл',
        'initialStatusText': 'Файл не выбран',
        'config': {
            'multiple': False,
            'minFiles': 1,
            'backUrl': '/nexus/autodailyes/weeks',
            'downloadPrefix': 'Проверка_кампаний',
            'dragDropText': '''Перетащите сюда файл кампаний:<br>
Файл должен начинаться с "cgr"<br><br>
Также вместо перетаскивания можно нажать на область ЛКМ и выбрать файл''',
            'apiEndpoints': {
                'process': '/campaigns/process',
                'status': '/campaigns/status',
                'download': '/campaigns/download',
                'cancel': '/campaigns/cancel'
            },
            'fileRules': [
                {'prefix': 'cgr', 'type': 'Кампании', 'required': True}
            ],
            'statusTexts': {
                'empty': 'Файл не выбран'
            }
        }
    }
}

# Конфигурация автореестров
AUTOREG_CONFIGS = {
    'ipoteka': {
        'title': 'Автореестры - Ипотека',
        'subtitle': 'Ипотека',
        'icon': 'fas fa-home',
        'config': {
            'registerType': 'Ипотека',
            'backUrl': '/nexus/autoreg/prolong',
            'multipleFiles': False,
            'templateHeaders': [
                "id физ лица", "№ Договора К Пролонгации", "ФИО", "Фамилия", "Имя", "Отчество",
                "Дата рождения", "Основной телефон", "Телефон 2", "Телефон 3", "Основной e-mail", "Банк",
                "Ответственный за лид id", "Ответственный сотрудник ЦО Филиала",
                "Ответственный сотрудник Агент", "Номер агентского договора",
                "Дата окончания страхования", "Прошлый период Страховая премия",
                "Прошлый период Страховая сумма", "Канал"
            ]
        }
    },
    
    'ipoteka_msk': {
        'title': 'Автореестры - Ипотека МСК',
        'subtitle': 'Ипотека МСК',
        'icon': 'fas fa-city',
        'config': {
            'registerType': 'Ипотека_мск',
            'backUrl': '/nexus/autoreg/prolong',
            'templateHeaders': [
                "id физ лица", "№ Договора К Пролонгации", "ФИО", "Фамилия", "Имя", "Отчество",
                "Дата рождения", "Основной телефон", "Телефон 2", "Телефон 3", "Основной e-mail", "Банк",
                "Ответственный за лид id", "Ответственный сотрудник ЦО Филиала",
                "Ответственный сотрудник Агент", "Номер агентского договора",
                "Дата окончания страхования", "Прошлый период Страховая премия",
                "Прошлый период Страховая сумма", "Канал"
            ]
        }
    },
    
    'kasko': {
        'title': 'Автореестры - КАСКО',
        'subtitle': 'КАСКО',
        'icon': 'fas fa-car-crash',
        'config': {
            'registerType': 'КАСКО',
            'backUrl': '/nexus/autoreg/prolong',
            'templateHeaders': [
                "id физ лица", "№ Договора К Пролонгации", "ФИО", "Фамилия", "Имя", "Отчество", "Дата рождения", "Основной телефон",
                "Телефон 2", "Телефон 3", "Основной e-mail", "Филиал ВСК", "Регион", "Объект страхования", "Марка", "Модель", "Год выпуска",
                "VIN", "Дата окончания страхования", "Прошлый период Страховая премия", "Прошлый период Страховая сумма", "Канал",
                "Ответственный сотрудник ЦО Филиала", "Ответственный сотрудник Агент", "Дилер", "Логин дилера", "Точка продаж", "Категория партнера", 
                "Номер агентского договора", "Вид полиса", "Передан в АКЦ", "Парный договор", "Вероятность, шт.", "Вероятность, руб."
            ]
        }
    },
    
    'kasko_iz_osago': {
        'title': 'Автореестры - КАСКО по ОСАГО',
        'subtitle': 'КАСКО по ОСАГО',
        'icon': 'fas fa-shield-alt',
        'config': {
            'registerType': 'КАСКО_ИЗ_ОСАГО_4_1',
            'backUrl': '/nexus/autoreg/prolong',
            'templateHeaders': [
                "id физлицо", "№ Договора К Пролонгации", "ФИО", "Фамилия", "Имя", "Отчество", "Дата рождения", "Филиал ВСК", 
                "Регион", "Основной телефон", "Телефон 2", "Телефон 3", "Основной e-mail", "Объект страхования", "Марка", "Модель", 
                "Год выпуска", "VIN", "Дата окончания страхования", "Прошлый период Страховая премия", "Прошлый период Страховая сумма", 
                "Новый период страховая премия", "Канал", "Ссылка на проект", "Дополнительные сведения"
            ]
        }
    },
    
    'osago': {
        'title': 'Автореестры - ОСАГО',
        'subtitle': 'ОСАГО',
        'icon': 'fas fa-car',
        'config': {
            'registerType': 'ОСАГО',
            'backUrl': '/nexus/autoreg/prolong',
            'templateHeaders': [
                "id физ лица", "№ Договора К Пролонгации", "ФИО", "Фамилия", "Имя", "Отчество", "Дата рождения", "Основной телефон", "Телефон 2", "Телефон 3",
                "Основной e-mail", "Филиал ВСК", "Регион", "Объект страхования", "Марка", "Модель", "Год выпуска", "VIN", "Ссылка на проект",
                "Дата окончания страхования", "Прошлый период Страховая премия", "Прошлый период Страховая сумма", "Новый период Страховая премия",
                "Промокод", "Канал", "Номер проекта", "Программа страхования"
            ]
        }
    },
    
    'mbg': {
        'title': 'Автореестры - МБГ',
        'subtitle': 'МБГ',
        'icon': 'fas fa-heart',
        'config': {
            'registerType': 'МБГ',
            'backUrl': '/nexus/autoreg/prolong',
            'templateHeaders': [
                "id физ лица", "ФИО", "Фамилия", "Имя", "Отчество", "Регион", "Филиал ВСК", "Дата рождения", 
                "Основной телефон", "Телефон 2", "Телефон 3", "Основной e-mail", 
                "№ Договора К Пролонгации", "Дата окончания страхования", "Прошлый период Страховая премия", 
                "Прошлый период Страховая сумма", "Канал"
            ]
        }
    },
    
    # Потеряшки
    'ipoteka_wa': {
        'title': 'Автореестры - Ипотека Потеряшки WA',
        'subtitle': 'Ипотека Потеряшки WA',
        'icon': 'fas fa-home',
        'config': {
            'registerType': 'Ипотека_WA',
            'backUrl': '/nexus/autoreg/olds',
            'templateHeaders': [
                "id физ лица", "ФИО", "Фамилия", "Имя", "Отчество", "Дата рождения", "Основной телефон", "Телефон 2", "Основной e-mail", "Филиал ВСК", "Другой полис",
                "Кредитный договор Дата", "Банк", "Дата окончания страхования", "Прошлый период Страховая премия", "Прошлый период Страховая сумма", "Канал", "Тип базы"
            ]
        }
    },
    
    'osago_wa': {
        'title': 'Автореестры - ОСАГО Потеряшки WA',
        'subtitle': 'ОСАГО Потеряшки WA',
        'icon': 'fas fa-car',
        'config': {
            'registerType': 'ОСАГО_WA',
            'backUrl': '/nexus/autoreg/olds',
            'templateHeaders': [
                "id физлицо", "№ Договора К Пролонгации", "ФИО", "Фамилия", "Имя", "Отчество", "Дата рождения", "Филиал ВСК", 
                "Регион", "Основной телефон", "Телефон 2", "Телефон 3", "Основной e-mail", "Объект страхования", "Марка", "Модель", 
                "Год выпуска", "VIN", "Дата окончания страхования", "Прошлый период Страховая премия", "Прошлый период Страховая сумма", 
                "Новый период страховая премия", "Канал", "Ссылка на проект", "Дополнительные сведения"
            ]
        }
    },
    
    'osago_4_1_up': {
        'title': 'Автореестры - ОСАГО Потеряшки 4.1 Москва',
        'subtitle': 'ОСАГО Потеряшки 4.1 Москва',
        'icon': 'fas fa-map-marker-alt',
        'config': {
            'registerType': 'ОСАГО_4_1',
            'backUrl': '/nexus/autoreg/olds',
            'templateHeaders': [
                "id физлицо", "№ Договора К Пролонгации", "ФИО", "Фамилия", "Имя", "Отчество", "Дата рождения", "Филиал ВСК", 
                "Регион", "Основной телефон", "Телефон 2", "Телефон 3", "Основной e-mail", "Объект страхования", "Марка", "Модель", 
                "Год выпуска", "VIN", "Дата окончания страхования", "Прошлый период Страховая премия", "Прошлый период Страховая сумма", 
                "Новый период страховая премия", "Канал", "Ссылка на проект", "Дополнительные сведения"
            ]
        }
    },
    
    # Пилоты
    'ipoteka_kom_bank': {
        'title': 'Автореестры - Ипотека ком. банки',
        'subtitle': 'Ипотека ком. банки',
        'icon': 'fas fa-university',
        'config': {
            'registerType': 'Ипотека_ком_банки',
            'backUrl': '/nexus/autoreg/pilots',
            'templateHeaders': [
                "id физ лица", "№ Договора К Пролонгации", "ФИО", "Фамилия", "Имя", "Отчество",
                "Дата рождения", "Основной телефон", "Телефон 2", "Телефон 3", "Основной e-mail", "Банк",
                "Ответственный за лид id", "Ответственный сотрудник ЦО Филиала",
                "Ответственный сотрудник Агент", "Номер агентского договора",
                "Дата окончания страхования", "Прошлый период Страховая премия",
                "Прошлый период Страховая сумма", "Канал"
            ]
        }
    },
    
    'ipoteka_sos': {
        'title': 'Автореестры - Ипотека SOS',
        'subtitle': 'Ипотека SOS',
        'icon': 'fas fa-exclamation-triangle',
        'config': {
            'registerType': 'Ипотека_SOS',
            'backUrl': '/nexus/autoreg/pilots',
            'templateHeaders': [
                "№ Договора К Пролонгации", "ФИО", "Фамилия", "Имя", "Отчество", "Дата рождения", "Основной телефон", 
                "Телефон 2", "Телефон 3", "Основной e-mail", "Банк", "Дата окончания страхования", "Канал", "Вид полиса", 
                "Дополнительные сведения", "Ссылка на проект в CTI"
            ]
        }
    },
    
    'f1': {
        'title': 'Автореестры - OneFactor',
        'subtitle': 'OneFactor',
        'icon': 'fas fa-flag',
        'config': {
            'registerType': 'f1',
            'backUrl': '/nexus/autoreg/pilots',
            'multipleFiles': True,
            'requiredFilesCount': 4,
            'uploadEndpoint': '/processing/combined-upload-excel',
            'dragDropEnabled': True,
            'dragDropText': '''Перетащите сюда 4 файла Excel или нажмите для выбора:<br>
    • ipot_akc_YYYYMMDD.xls<br>
    • ipot_mos_YYYYMMDD.xls<br>
    • kasko_akc_YYYYMMDD.xls<br>
    • kasko_mos_YYYYMMDD.xls<br><br>
    <small>Поддерживаются форматы: .xls, .xlsx</small>''',
            'requiredFiles': [
                {'prefix': 'ipot_akc_', 'name': 'Ипотека АКЦ', 'required': True},
                {'prefix': 'ipot_mos_', 'name': 'Ипотека МОС', 'required': True},
                {'prefix': 'kasko_akc_', 'name': 'КАСКО АКЦ', 'required': True},
                {'prefix': 'kasko_mos_', 'name': 'КАСКО МОС', 'required': True}
            ],
            'templateHeaders': [
                "id физ лица", "Тип лида", "Продукт", "Группа продукта", "Вид страхования", "ФИО", "Фамилия", 
                "Имя", "Отчество", "Дата рождения", "Основной телефон", "Телефон 2", "Телефон 3", "Основной e-mail", 
                "Филиал ВСК", "Регион", "Другой полис", "Дополнительные сведения", "Тип базы"
            ]
        }
    },
    
    'osago_kz': {
        'title': 'Автореестры - ОСАГО КЗ',
        'subtitle': 'ОСАГО КЗ',
        'icon': 'fas fa-flag',
        'config': {
            'registerType': 'ОСАГО_КЗ',
            'backUrl': '/nexus/autoreg/pilots',
            'templateHeaders': [
                "id физ лица", "№ Договора К Пролонгации", "ФИО", "Фамилия", "Имя", "Отчество", "Дата рождения", "Основной телефон", "Телефон 2", "Телефон 3",
                "Основной e-mail", "Филиал ВСК", "Регион", "Объект страхования", "Марка", "Модель", "Год выпуска", "VIN", "Ссылка на проект",
                "Дата окончания страхования", "Прошлый период Страховая премия", "Прошлый период Страховая сумма", "Новый период Страховая премия",
                "Промокод", "Канал", "Номер проекта", "Программа страхования"
            ]
        }
    },
    
    'dvr': {
        'title': 'Автореестры - Проект «Деньги вместо ремонта»',
        'subtitle': 'Проект «Деньги вместо ремонта»',
        'icon': 'fas fa-hand-holding-usd',
        'config': {
            'registerType': 'ДВР',
            'backUrl': '/nexus/autoreg/pilots',
            'templateHeaders': [
                "Примечания", "Продукт", "Филиал ВСК", "ФИО", "Фамилия", "Имя", "Отчество", "Основной телефон", "Телефон 2", "Телефон 3", "Основной e-mail",
                "Другой полис", "Дата начала страхования/дата заключения", "Кредитный договор Дата", 
                "Прошлый период Страховая сумма", "Марка", "Модель", "Год выпуска", "СтраховаяСумма", "Риск", "ТипСобытия", "Стадия"
            ]
        }
    }
}