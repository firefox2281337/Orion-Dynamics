from datetime import datetime
from flask import Blueprint, render_template, request
from web.utils.logging_helper import log_user_access
from .nexus_config import PAGE_CONFIGS, AUTOREG_CONFIGS, AUTODAILYES_CONFIGS
from .nexus_utils import get_page_config, get_autoreg_config, get_autodailyes_config, NexusPageBuilder

nexus_bp = Blueprint('nexus', __name__)

def log_page_access(page_name):
    """Общая функция для логирования доступа к страницам"""
    log_user_access(
        page=page_name,
        client_ip=request.remote_addr,
        current_time=datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
        message=f"Пользователь зашёл на {page_name}"
    )

def render_nexus_page(page_key, template_name):
    """Универсальная функция рендеринга страниц Nexus"""
    log_page_access(template_name)
    page_data = PAGE_CONFIGS.get(page_key, PAGE_CONFIGS['main'])
    return render_template('nexus/main.html', page_data=page_data)

def render_autodailyes_page(autodailyes_key, template_name):
    """Универсальная функция рендеринга автоежедневок"""
    log_page_access(template_name)
    autodailyes_data = get_autodailyes_config(autodailyes_key)
    return render_template('nexus/autodailyes.html', autodailyes_data=autodailyes_data)

def render_autoreg_page(autoreg_key, template_name):
    """Универсальная функция рендеринга автореестров"""
    log_page_access(template_name)
    autoreg_data = get_autoreg_config(autoreg_key)
    return render_template('nexus/autoreg.html', autoreg_data=autoreg_data)

@nexus_bp.route('/')
def nexus_main():
    """Главная страница Nexus"""
    return render_nexus_page('main', 'main.html')

@nexus_bp.route('/autoreg')
def nexus_autoreg():
    """Страница выбора типа автореестра"""
    return render_nexus_page('autoreg', 'autoreg_type_leads.html')

@nexus_bp.route('/autoreg/prolong')
def nexus_autoreg_prolong():
    """Страница пролонгации"""
    return render_nexus_page('prolong', 'autoreg_prolong_type_register.html')

@nexus_bp.route('/autoreg/olds')
def nexus_autoreg_olds():
    """Страница потеряшек"""
    return render_nexus_page('olds', 'autoreg_olds_type_register.html')

@nexus_bp.route('/autoreg/pilots')
def nexus_autoreg_pilots():
    """Страница пилотов"""
    return render_nexus_page('pilots', 'autoreg_pilots_type_register.html')

@nexus_bp.route('/autodailyes')
def nexus_autodailyes():
    """Страница выбора периодичности"""
    return render_nexus_page('autodailyes', 'autodailyes_select_task_period.html')

@nexus_bp.route('/autodailyes/dailyes')
def nexus_autodailyes_dailyes():
    """Страница ежедневных задач"""
    return render_nexus_page('dailyes', 'autodailyes_select_task_dailyes.html')

@nexus_bp.route('/autodailyes/weeks')
def nexus_autodailyes_weeks():
    """Страница еженедельных задач"""
    return render_nexus_page('weeks', 'autodailyes_select_task_weeks.html')

@nexus_bp.route('/autoreg/prolong/ipoteka')
def nexus_autoreg_prolong_ipoteka():
    """Страница ипотечной пролонгации"""
    return render_autoreg_page('ipoteka', 'ipoteka.html')

@nexus_bp.route('/autoreg/prolong/ipoteka-msk')
def nexus_autoreg_prolong_ipoteka_msk():
    """Страница московской ипотечной пролонгации"""
    return render_autoreg_page('ipoteka_msk', 'ipoteka_msk.html')

@nexus_bp.route('/autoreg/prolong/kasko')
def nexus_autoreg_prolong_kasko():
    """Страница пролонгации КАСКО"""
    return render_autoreg_page('kasko', 'kasko.html')

@nexus_bp.route('/autoreg/prolong/kasko-iz-osago')
def nexus_autoreg_prolong_kasko_iz_osago():
    """Страница пролонгации КАСКО из ОСАГО"""
    return render_autoreg_page('kasko_iz_osago', 'kasko_iz_osago.html')

@nexus_bp.route('/autoreg/prolong/osago')
def nexus_autoreg_prolong_osago():
    """Страница пролонгации ОСАГО"""
    return render_autoreg_page('osago', 'osago.html')

@nexus_bp.route('/autoreg/prolong/mbg')
def nexus_autoreg_prolong_mbg():
    """Страница пролонгации MBG"""
    return render_autoreg_page('mbg', 'mbg.html')

@nexus_bp.route('/autoreg/olds/ipowa')
def nexus_autoreg_olds_ipowa():
    """Страница ипотечных потеряшек WA"""
    return render_autoreg_page('ipoteka_wa', 'ipoteka_wa.html')

@nexus_bp.route('/autoreg/olds/osagowa')
def nexus_autoreg_olds_osagowa():
    """Страница ОСАГО потеряшек WA"""
    return render_autoreg_page('osago_wa', 'osago_wa.html')

@nexus_bp.route('/autoreg/olds/osago41')
def nexus_autoreg_olds_osago41():
    """Страница ОСАГО потеряшек 4.1"""
    return render_autoreg_page('osago_4_1_up', 'osago_4_1_up.html')

@nexus_bp.route('/autoreg/pilots/ipoteka_kom_bank')
def nexus_autoreg_pilots_ipoteka_kom_bank():
    """Страница ипотеки коммерческих банков"""
    return render_autoreg_page('ipoteka_kom_bank', 'ipoteka_kom_bank.html')

@nexus_bp.route('/autoreg/pilots/ipoteka_sos')
def nexus_autoreg_pilots_ipoteka_sos():
    """Страница ипотеки SOS"""
    return render_autoreg_page('ipoteka_sos', 'ipoteka_sos.html')

@nexus_bp.route('/autoreg/pilots/f1')
def nexus_autoreg_pilots_f1():
    """Страница OneFactor"""
    return render_autoreg_page('f1', 'f1.html')

@nexus_bp.route('/autoreg/pilots/osago_kz')
def nexus_autoreg_pilots_osago_kz():
    """Страница ОСАГО КЗ"""
    return render_autoreg_page('osago_kz', 'osago_kz.html')

@nexus_bp.route('/autoreg/pilots/dvr')
def nexus_autoreg_pilots_dvr():
    """Страница проекта ДВР"""
    return render_autoreg_page('dvr', 'dvr.html')

@nexus_bp.route('/autodailyes/dailyes/autoverint')
def nexus_autodailyes_dailyes_autoverint():
    """Страница автоматизации Verint"""
    return render_autodailyes_page('autoverint', 'autoverint.html')

@nexus_bp.route('/autodailyes/dailyes/autoolds')
def nexus_autodailyes_dailyes_autoolds():
    """Страница автоматизации старых записей"""
    return render_autodailyes_page('autoolds', 'autoolds.html')

@nexus_bp.route('/autodailyes/dailyes/autojarvis')
def nexus_autodailyes_dailyes_autojarvis():
    """Страница автоматизации Jarvis"""
    return render_autodailyes_page('autojarvis', 'autojarvis.html')

@nexus_bp.route('/autodailyes/dailyes/autodeals')
def nexus_autodailyes_dailyes_autodeals():
    """Страница автоматизации сделок"""
    return render_autodailyes_page('autodeals', 'autodeals.html')

@nexus_bp.route('/autodailyes/weeks/autochekcompany')
def nexus_autodailyes_weeks_autochekcompany():
    """Страница автоматической проверки компаний"""
    return render_autodailyes_page('autochekcompany', 'autochekcompany.html')