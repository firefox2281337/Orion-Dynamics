from datetime import datetime, timedelta, date
from web.templates.nexus.autoreg.logic.sql_operations import load_sql_query, execute_sql_query
from web.templates.nexus.autoreg.logic.data_processing import ensure_columns_exist
from configparser import ConfigParser
import warnings
import polars as pl
import requests
import urllib3
import xlsxwriter
from requests.exceptions import RequestException
import logging
import pandas as pd


# Базовые методы
def get_config_value(section: str, key: str, file: str = r"C:\Users\EPopkov\Documents\Orion Dynamics\settings_nexus.ini") -> str:
    """Получает значение параметров из INI-файла."""
    config = ConfigParser()
    config.read(file, encoding="utf-8")
    return config.get(section, key, fallback=None)

def steps (self, current_step, total_steps, status):
    """Контроллирует обновление прогресс-бара
    
    Параметры:

    current_step - Увеличивает текущий шаг,
    total_steps - Общее количество шагов,
    status - Текст, что в данный момент выполняется."""
    current_step += 1
    self.progress_signal.emit(int((current_step / total_steps) * 100))
    self.status_signal.emit(status)
    return current_step

def create_df(file_path, ready_headers, correspondences):
    """Создание основного DataFrame"""
    source_data = pl.read_excel(file_path)

    if source_data.height == 0:
        return

    # создаём пустой result_data с нужными заголовками
    result_data = pl.DataFrame({header: [None] * source_data.height for header in ready_headers})

    reversed_correspondences = {v: k for k, v in correspondences.items()}
    for source_col, target_col in reversed_correspondences.items():
        if source_col in source_data.columns:
            result_data = result_data.with_columns(source_data[source_col].alias(target_col))

    return result_data


def create_combined_df(file_path, ready_headers, correspondences):
    """
    Создает DataFrame из листов Excel "Звонок рабочая" и "Автоинформатор рабочая",
    добавляет столбец "Тип базы" и объединяет их.
    """

    звонок_data = read_excel_sheet(file_path, "Звонок рабочая", ready_headers, correspondences, base_type="Звонок")
    автоинформатор_data = read_excel_sheet(file_path, "Автоинформатор рабочая", ready_headers, correspondences, base_type="Автоинформатор")

    all_data = []

    if звонок_data is not None:
        all_data.append(звонок_data)
    if автоинформатор_data is not None:
        all_data.append(автоинформатор_data)

    if not all_data:
        return None 

    result_data = pl.concat(all_data)

    return result_data

def read_excel_sheet(file_path, sheet_name_part, ready_headers, correspondences, base_type):
    """
    Читает лист Excel, создает DataFrame, добавляет столбец "Тип базы"
    """
    try:
        excel_file = pd.ExcelFile(file_path)
        sheet_names = excel_file.sheet_names
        sheet_name = next((name for name in sheet_names if sheet_name_part in name), None)
        if not sheet_name:
            return None

        source_data = pl.read_excel(file_path, sheet_name=sheet_name)

        if source_data.height == 0:
            return None

        result_data = pl.DataFrame({header: [None] * source_data.height for header in ready_headers})

        reversed_correspondences = {v: k for k, v in correspondences.items()}
        for source_col, target_col in reversed_correspondences.items():
            if source_col in source_data.columns:
                result_data = result_data.with_columns(source_data[source_col].alias(target_col))

        result_data = result_data.with_columns(pl.Series("Тип базы", [base_type] * source_data.height))

        return result_data

    except FileNotFoundError:
        return None
    except Exception as e:
        return None

def save_to_excel(file_path, dataframes_with_sheets):
    workbook = xlsxwriter.Workbook(file_path)
    header_format = workbook.add_format({'bold': True})

    for df, sheet_name in dataframes_with_sheets:
        if df is not None:
            worksheet = workbook.add_worksheet(sheet_name)

            column_widths = {}
            for col_num, column in enumerate(df.columns):
                worksheet.write(0, col_num, column, header_format)
                column_widths[col_num] = len(column) + 2

            for row_num, row in enumerate(df.rows(), start=1):
                for col_num, value in enumerate(row):
                    worksheet.write(row_num, col_num, value)
                    
                    value_length = len(str(value)) if value is not None else 0
                    if value_length + 2 > column_widths.get(col_num, 0):
                        column_widths[col_num] = value_length + 2

            for col_num, width in column_widths.items():
                worksheet.set_column(col_num, col_num, width)

    workbook.close()



# Форматировщики
def parse_and_format_date(date_input):
    """Установка правильного формата даты"""
    if isinstance(date_input, (datetime, date)):
        return date_input
    date_formats = ["%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y", "%Y.%m.%d", "%m-%d-%Y"]
    for fmt in date_formats:
        try:
            return datetime.strptime(date_input, fmt).date()
        except (ValueError, TypeError):
            continue
    return None

def clear_columns_dog():
    """Установка правильных символов"""
    pl.col("№ Договора К Пролонгации") \
        .str.replace("А", "A") \
        .str.replace("Е", "E") \
        .str.replace("Р", "P") \
        .alias("№ Договора К Пролонгации")
    
def clean_column(column):
    """Удаление лишних символов из столбцов"""
    return (column
        .fill_null("")
        .str.replace_all(r",.*", "")
        .str.replace_all(r"[(),#\-+ ]", "")
        .str.replace_all(r"не.*", "")
        .str.replace_all(r"О.*", "")
        .str.replace_all(r"\)$", "")
        .str.replace_all(r"Нетданных", "")
        .str.replace_all(r"79000000000", "")
        .str.replace_all(r"89000000000", "")
        .str.replace_all(r"79999999999", "")
        .str.replace_all(r"89999999999", "")
        .str.replace_all(r"None", "")
        .str.strip_chars())

def format_phone(col):
    """Форматирует номер телефона, если он длиннее 11 символов, меняет начальные цифры на 79"""
    return [pl.col(col).str.strip_chars().str.slice(0, 12).map_elements(lambda phone: int(f"79{phone[2:]}") if phone.startswith("7") and phone.isdigit() else None,
                                                                        return_dtype=pl.UInt64).alias(col)]

def clean_phone_column(result_data, col_name_1, col_name_2):
    """Чистит дубликаты по столбцам

    Параметры:

    result_data - Основной DataFrame
    col_name_1 - Первый проверяемый столбец
    col_name_2 - Второй проверяемый столбец"""
    return result_data.with_columns(pl.when((result_data[col_name_1] == result_data[col_name_2]) | 
                (result_data[col_name_1].is_null()) |
                (result_data[col_name_2].is_null())).then(None).otherwise(result_data[col_name_2]).alias(col_name_2))

def calculate_product(bank, insurance_type):
    products = {
        ("Сбербанк", "Имущество граждан"): "Имущество граждан (Сбер)",
        ("Сбербанк", "Страхование граждан от несчастных случаев и болезней"): 
            "Страхование граждан от несчастных случаев и болезней (Сбер)",
        ("ВТБ", "Имущество граждан"): "ВТБ Ипотека Имущество",
        ("ВТБ", "Страхование граждан от несчастных случаев и болезней"): "ВТБ Ипотека НС",
        ('ПАО Банк "Санкт-Петербург"', "Страхование граждан от несчастных случаев и болезней"): "Ипотека Коммерческие банки",
        ('ПАО Банк "Санкт-Петербург"', "Имущество граждан"): "Ипотека Коммерческие банки",}
    return products.get((bank, insurance_type), None)

def final_format_ipo():
    return [pl.col("Дата окончания страхования").cast(pl.Date).dt.strftime("%d.%m.%Y").alias("Дата окончания страхования"),
            pl.col("Плановая дата звонка CTI").cast(pl.Date).dt.strftime("%d.%m.%Y").alias("Плановая дата звонка CTI"),
            pl.col("Прошлый период Страховая премия").cast(pl.Float64).map_elements(
                lambda x: f"{x:.2f}".replace(".", ",") if x is not None else None, return_dtype=pl.Utf8
            ).alias("Прошлый период Страховая премия"),
            pl.col("Прошлый период Страховая сумма").cast(pl.Float64).map_elements(
                lambda x: f"{x:.2f}".replace(".", ",") if x is not None else None, return_dtype=pl.Utf8
            ).alias("Прошлый период Страховая сумма"),
            pl.when(pl.col("Вид страхования") == "Страхование граждан от несчастных случаев и болезней")
            .then(pl.col("ФИО"))
            .otherwise(pl.col("Объект страхования"))
            .alias("Объект страхования")]

def set_lead_id_by_employee():
    def assign_lead_id(employee):
        employee_lower = (employee or "").lower()
        if "дегтярева" in employee_lower:
            return "2cc37bbd-e776-47f7-83f8-0cb58c52f60b"
        elif "иванова" in employee_lower:
            return "11fd2672-26fc-4f61-b216-d48e0d5f53c5"
        elif "лыкова" in employee_lower:
            return "84394113-6d2b-4fcf-9fdd-247329f6c0fb"
        elif "смирнова" in employee_lower:
            return "0f535546-c63f-4853-a6b7-7025845779d5"
        else:
            return None
    return [pl.col("Ответственный сотрудник ЦО Филиала").map_elements(assign_lead_id, return_dtype=pl.Utf8).alias("Ответственный за лид id")]

def set_lead_company_by_employee():
    def assign_lead_id(employee):
        employee_lower = (employee or "").lower()
        if "лыкова" in employee_lower:
            return "1.3 Mortage 15 мобилка"
        elif "смирнова" in employee_lower:
            return "1.3 Mortage 5 мобилка"
        else:
            return None
    return [pl.col("Ответственный сотрудник ЦО Филиала").map_elements(assign_lead_id, return_dtype=pl.Utf8).alias("Кампания")]


def final_format_osago():
    return [pl.col("Дата окончания страхования").cast(pl.Date).dt.strftime("%d.%m.%Y").alias("Дата окончания страхования"),
            pl.col("Плановая дата звонка CTI").cast(pl.Date).dt.strftime("%d.%m.%Y").alias("Плановая дата звонка CTI"),
            pl.col("Прошлый период Страховая премия").cast(pl.Float64).map_elements(
                lambda x: f"{x:.2f}".replace(".", ",") if x is not None else None, return_dtype=pl.Utf8
            ).alias("Прошлый период Страховая премия"),
            pl.col("Прошлый период Страховая сумма").cast(pl.Float64).map_elements(
                lambda x: f"{x:.2f}".replace(".", ",") if x is not None else None, return_dtype=pl.Utf8
            ).alias("Прошлый период Страховая сумма")]

def clean_column_strah(column):
    return (column
        .str.replace_all(r"1", "Второй год и более")
        .str.replace_all(r"2", "Второй год и более")
        .str.replace_all("3\\+", "Второй год и более")
        .str.replace_all(r"0", "1 год"))

def clean_column_category(column):
    return (column
        .str.replace_all(r"Категория ", ""))

def fix_columns_dealer(processed_data):
    columns_to_fill = ["Дилер", "Логин дилера", "Точка продаж", "Категория партнера", "Номер агентского договора"]
    for col in columns_to_fill:
        processed_data = processed_data.with_columns(processed_data[col].cast(pl.Utf8).fill_null("Нет данных"))
    processed_data = processed_data.with_columns(processed_data["Вид полиса"].cast(pl.Utf8))
    columns_to_clean = ["Вид полиса"]
    for col in columns_to_clean:
        if col in processed_data.columns:
            processed_data = processed_data.with_columns(clean_column_strah(pl.col(col)).alias(col))
    columns_to_clean = ["Категория партнера"]
    for col in columns_to_clean:
        if col in processed_data.columns:
            processed_data = processed_data.with_columns(clean_column_category(pl.col(col)).alias(col))
    return processed_data

def clean_column_fio(column):
    return column.str.replace_all(r"\(.*", "")

def clean_fio(result_data, columns_to_clean):
    for col in columns_to_clean:
        if col in result_data.columns:
            result_data = result_data.with_columns(clean_column_fio(pl.col(col)).alias(col))
    return result_data



# Операции со столбцами
def generate_external_id(number, result_data, base_type):
    """Генерация ID внешней системы"""
    base_number = "".join(number) if isinstance(number, set) else str(number)
    current_date = datetime.now().strftime("%d.%m.%Y")
    return (base_number + f"_{base_type}_{current_date}_" + pl.arange(1, len(result_data) + 1).cast(pl.Utf8)).alias("ID_внешней системы")

def set_prolong_year_olds(base_type):
    return pl.col("Дата окончания страхования").map_elements(lambda date: date.replace(year=int(get_year_prolong_olds(base_type))), return_dtype=pl.Date).alias("Дата окончания страхования")

def calculate_planned_call_date(base_type):
    """Расчет плановой даты звонка"""
    return pl.when(pl.col("Дата окончания страхования").is_not_null()) \
            .then(pl.col("Дата окончания страхования") - timedelta(days=get_planned_call_offset(base_type))) \
            .alias("Плановая дата звонка CTI")

def fix_columns_ipo_wa(result_data, base_type):
    result_data = result_data.with_columns([
                pl.when(pl.col("Тип базы").str.contains("Звонок"))
                .then(pl.when(pl.col("Дата окончания страхования").is_not_null())
                    .then(pl.col("Дата окончания страхования") - timedelta(days=int(get_planned_call_offset(base_type))+20))
                    .otherwise(None))
                .when(pl.col("Тип базы").str.contains("Автоинформатор"))
                .then(pl.when(pl.col("Дата окончания страхования").is_not_null())
                    .then(pl.col("Дата окончания страхования") - timedelta(days=int(get_planned_call_offset(base_type))))
                    .otherwise(None))
                .alias("Плановая дата звонка CTI"),
                pl.when(pl.col("Тип базы").str.contains("Звонок")).then(pl.lit("4.3 ТМ_Пилот")).when(pl.col("Тип базы").str.contains("Автоинформатор")).then(pl.lit("3.3 Автоинф Потеряшки Ипотека"))
                .otherwise(pl.lit("")).alias("Кампания"),
                pl.when(pl.col("Тип базы").str.contains("Автоинформатор")).then(pl.lit("Автоинформатор")).otherwise(pl.lit("")).alias("Дополнительные сведения"),
                pl.when(pl.col("Тип базы").str.contains("Автоинформатор")).then(pl.lit("Группа продаж Ипотека")).otherwise(pl.lit("Активный контакт-центр (АКЦ)")).alias("Ответственный отдел")])
    return result_data

def set_priority_osago(base_type):
    """Определение приоритета"""
    return pl.lit(get_priority(base_type)).alias("Приоритет")

def set_product(base_type):
    """Определение продукта"""
    return pl.lit(get_product(base_type)).alias("Продукт")

def set_type_of_insure(base_type):
    """Определение вида страхования"""
    return pl.lit(get_type_of_insurance(base_type)).alias("Вид страхования")

def set_departament(departament):
    """Определение ответственного отдела"""
    return pl.lit(departament).alias("Ответственный отдел")

def set_subdivision(subdivision):
    """Определение ответственного подразделения"""
    return pl.lit(subdivision).alias("Ответственное подразделение")

def set_links_osago(base_type):
    """Определение ссылки на проект"""
    return (pl.col("Ссылка на проект") + get_link(base_type) + pl.col("№ Договора К Пролонгации")).alias("Ссылка на проект")

def set_priority():
    """Определение приоритета"""
    return pl.when(pl.col("Дата окончания страхования").is_not_null()) \
            .then(pl.col("Дата окончания страхования")) \
            .alias("Приоритет")

def set_lead_type(base_type):
    """Добавление типа лида"""
    return pl.lit(get_lead_type(base_type)).alias("Тип лида")

def set_insurance_group(base_type):
    """Добавление группы продукта"""
    return pl.lit(get_insurance_group(base_type)).alias("Группа продукта")

def split_fio(fio):
    """Разбивает ФИО на Фамилию, Имя, Отчество"""
    parts = fio.split() if fio else []
    return parts + [""] * (3 - len(parts))

def make_fio():
    """Создает новые колонки с разделенным ФИО"""
    return [
        pl.col("ФИО").map_elements(lambda fio: split_fio(fio)[0], return_dtype=pl.Utf8).alias("Фамилия"),
        pl.col("ФИО").map_elements(lambda fio: split_fio(fio)[1], return_dtype=pl.Utf8).alias("Имя"),
        pl.col("ФИО").map_elements(lambda fio: split_fio(fio)[2], return_dtype=pl.Utf8).alias("Отчество"),
        pl.when(pl.col("ФИО").is_null() | (pl.col("ФИО") == ""))
        .then(pl.format("{} {} {}", pl.col("Фамилия"), pl.col("Имя"), pl.col("Отчество")))
        .otherwise(pl.col("ФИО"))
        .alias("ФИО")]

def set_correct_bank():
    def correct_bank(bank):
        bank_lower = (bank or "").lower()
        if "сбер" in bank_lower:
            return "Сбербанк"
        elif "втб" in bank_lower:
            return "ВТБ"
        elif "санкт-петербург" in bank_lower:
            return 'ПАО Банк "Санкт-Петербург"'
        else:
            return bank
    return [pl.col("Банк").map_elements(correct_bank, return_dtype=pl.Utf8).alias("Банк")]

def set_proba_prol(result_data: pl.DataFrame, base_type: str) -> pl.DataFrame:
    """Установка вероятности пролонгации
    
    Параметры:

    result_data - Основной DataFrame, 
    base_type - Тип базы для поиска справочника.

    Для отсутствующих значений в справочнике проставляется значение 0.5"""
    lookup_file_path = f'C:/Users/EPopkov/Documents/Orion Dynamics/nexus/references/Вероятность пролонгации {base_type}.parquet'
    contract_numbers_to_search = set(result_data["№ Договора К Пролонгации"].drop_nulls().unique().to_list())
    lookup_df = pl.scan_parquet(lookup_file_path)
    filtered_lookup_df = (lookup_df.filter(pl.col("contract_number").is_in(contract_numbers_to_search)).select(["contract_number", "proba_callibr"]))
    collected_df = filtered_lookup_df.collect()
    lookup_data = dict(zip(collected_df["contract_number"].to_list(), collected_df["proba_callibr"].to_list()))

    # Проставляем вероятности пролонгации (по умолчанию 0.5, если нет в справочнике)
    probabilities = [lookup_data.get(contract_number, 0.5) for contract_number in result_data["№ Договора К Пролонгации"]]
    return result_data.with_columns(
        pl.Series("Шт., вероятность пролонгации", probabilities, dtype=pl.Float64),
        pl.Series("Руб., вероятность пролонгации", probabilities, dtype=pl.Float64))

def set_type_of_insurance():
    """Устанавливает вид страхования по принципу И - имущество, U - имущество, П - НСка"""
    return pl.col("Вид страхования").replace(["И", "U", "П"],["Имущество граждан", "Имущество граждан", "Страхование граждан от несчастных случаев и болезней"]).alias("Вид страхования")

def conversion_date_bitrth():
    """Преобразует дату рождения, полученную в формате 17-01-2024-13-22-11GMT из JSON"""
    return pl.when(pl.col("Дата рождения").is_not_null()).then(pl.col("Дата рождения").str.strptime(pl.Date, format="%a, %d %b %Y %H:%M:%S %Z", strict=False)).otherwise(None).alias("Дата рождения")

def get_client_age():
    """Получает возраст клиента, исходя из даты рождения и текущей даты + возврат даты в нормальный формат"""
    current_year = datetime.now().year
    return pl.when(pl.col("Дата рождения").is_not_null()).then(current_year - pl.col("Дата рождения").dt.year()).otherwise(None).alias("Возраст"), pl.col("Дата рождения").dt.strftime("%d.%m.%Y").alias("Дата рождения")

def set_discount_pc():
    """"Получает скидку к ПК, отталкивая от возраста, где >=60 лет скидка не предоставляется, от 50 до 59 скидка равна 0.7, от 18 до 50 скидка равна 0.5, так же учитывается вид страхования"""
    return pl.when(pl.col("Вид страхования") == "Страхование граждан от несчастных случаев и болезней").then(
        pl.when(pl.col("Возраст") >= 60).then(None)
        .when((pl.col("Возраст") >= 50) & (pl.col("Возраст") <= 59)).then(0.7)
        .when((pl.col("Возраст") >= 18) & (pl.col("Возраст") < 50)).then(
            pl.when(pl.col("Вид страхования") == "Страхование граждан от несчастных случаев и болезней").then(
                pl.when(pl.col("Возраст") >= 18).then(
                    pl.when(pl.col("Вид страхования") == "Страхование граждан от несчастных случаев и болезней").then(0.6)
                ).otherwise(None)))).otherwise(None).alias("Скидка к ПК")

def set_special_offer_discount():
    """Устанавливает скидку по спецпредложению отталкиваясь от скидки к ПК"""
    return pl.when(pl.col("Скидка к ПК").is_not_null()).then((1 - pl.col("Скидка к ПК")) * 100).otherwise(None).alias("Скидка по спецпредложению")

def set_region_and_filial(processed_data):
    """"Устанавливает регион и филиал"""
    lookup_data = pl.read_parquet("C:/Users/EPopkov/Documents/Orion Dynamics/nexus/references/Регионы и филиалы.parquet")
    lookup_dict_1 = dict(zip(lookup_data["Филиалы в исходнике"], lookup_data["Корректно"]))
    lookup_dict_2 = dict(zip(lookup_data["Корректно"], lookup_data["Регион корректно"]))
    return processed_data.with_columns([
        pl.col("Филиал ВСК").map_elements(lambda x: lookup_dict_1.get(x, x), return_dtype=pl.Utf8).alias("Филиал ВСК"),
        pl.col("Филиал ВСК").map_elements(lambda x: lookup_dict_2.get(x, x), return_dtype=pl.Utf8).alias("Регион")])

def set_region(processed_data):
    """"Устанавливает регион и филиал"""
    lookup_data = pl.read_parquet("C:/Users/EPopkov/Documents/Orion Dynamics/nexus/references/Регионы и филиалы.parquet")
    lookup_dict_2 = dict(zip(lookup_data["Корректно"], lookup_data["Регион корректно"]))
    return processed_data.with_columns([
        pl.col("Филиал ВСК").map_elements(lambda x: lookup_dict_2.get(x, x), return_dtype=pl.Utf8).alias("Регион")])

def set_region_and_filial_osago_kasko(processed_data):
    lookup_data = pl.read_parquet("C:/Users/EPopkov/Documents/Orion Dynamics/nexus/references/Регионы и филиалы.parquet")
    lookup_data2 = pl.read_parquet("C:/Users/EPopkov/Documents/Orion Dynamics/nexus/references/Регионы.parquet")
    lookup_dict_1 = dict(zip(lookup_data2["Название"], lookup_data2["Корректное название"]))
    lookup_dict_2 = dict(zip(lookup_data["Регион корректно"], lookup_data["Корректно"]))
    lookup_dict_3 = dict(zip(lookup_data["Филиалы в исходнике"], lookup_data["Корректно"]))
    lookup_dict_4 = dict(zip(lookup_data["Корректно"], lookup_data["Регион корректно"]))
    processed_data = processed_data.with_columns([pl.col("Филиал ВСК").map_elements(lambda x: lookup_dict_3.get(x, None), return_dtype=pl.Utf8).alias("Филиал ВСК Корректно")])
    
    found_mask = processed_data["Филиал ВСК Корректно"].is_not_null()
    not_found_mask = processed_data["Филиал ВСК Корректно"].is_null()
    
    processed_data = processed_data.with_columns([
        pl.when(found_mask)
        .then(pl.col("Филиал ВСК Корректно").map_elements(lambda x: lookup_dict_4.get(x, x), return_dtype=pl.Utf8))
        .otherwise(None)
        .alias("Регион")])
    processed_data = processed_data.with_columns([
        pl.when(not_found_mask)
        .then(pl.col("Филиал ВСК").map_elements(lambda x: lookup_dict_1.get(x, x), return_dtype=pl.Utf8))
        .otherwise(pl.col("Регион"))
        .alias("Регион")])
    processed_data = processed_data.with_columns([
        pl.when(not_found_mask)
        .then(pl.col("Регион").map_elements(lambda x: lookup_dict_2.get(x, x), return_dtype=pl.Utf8))
        .otherwise(pl.col("Филиал ВСК"))
        .alias("Филиал ВСК")])
    processed_data = processed_data.drop("Филиал ВСК Корректно")
    processed_data = processed_data.with_columns([pl.when(pl.col("Филиал ВСК").str.contains("ПРОФИТ:")).then(pl.lit("Москва")).otherwise(pl.col("Регион")).alias("Регион")])
    processed_data = processed_data.with_columns([pl.when(pl.col("Филиал ВСК").str.contains("Дирекция")).then(pl.lit("Москва")).otherwise(pl.col("Регион")).alias("Регион")])
    processed_data = processed_data.with_columns([pl.when(pl.col("Филиал ВСК").str.contains("ПРОФИТ:")).then(pl.lit("ГК")).otherwise(pl.col("Филиал ВСК")).alias("Филиал ВСК")])
    processed_data = processed_data.with_columns([pl.when(pl.col("Филиал ВСК").str.contains("Дирекция")).then(pl.lit("ГК")).otherwise(pl.col("Филиал ВСК")).alias("Филиал ВСК")])
    return processed_data

def set_correct_product_ipo():
    """Устанавливает корректный продукт по ипотеке, исходя из банка и вида страхования"""
    return pl.struct(["Банк", "Вид страхования"]).map_elements(lambda x: calculate_product(x["Банк"], x["Вид страхования"]), return_dtype=pl.Utf8).alias("Продукт")

def remove_lada(value):
    return value.replace(" (LADA)", "") if value else value

def replace_empty_with_other(value):
    return "Прочие" if value is None or value == "" else value

def to_proper_case(value):
    return value.title() if value else value

def format_object_insurance(marka, model, year):
    return f"{marka} {model},Год выпуска-{year}" if marka and model and year else ""

def fix_auto(processed_data):
    processed_data = processed_data.with_columns(pl.col("Марка").map_elements(remove_lada, return_dtype=pl.Utf8).alias("Марка"))
    processed_data = processed_data.with_columns([pl.col("Марка").map_elements(replace_empty_with_other, return_dtype=pl.Utf8).alias("Марка"),
                                                pl.col("Модель").map_elements(replace_empty_with_other, return_dtype=pl.Utf8).alias("Модель"),])
    processed_data = processed_data.with_columns([pl.col("Марка").map_elements(to_proper_case, return_dtype=pl.Utf8).alias("Марка"),
                                                pl.col("Модель").map_elements(to_proper_case, return_dtype=pl.Utf8).alias("Модель"),])
    processed_data = processed_data.with_columns(pl.col("Марка").replace(None, "Прочие"))
    processed_data = processed_data.with_columns(pl.col("Модель").replace(None, "Прочие"))
    if processed_data["Объект страхования"].is_not_null().all():
        processed_data = processed_data.with_columns(pl.col("Объект страхования").map_elements(lambda x: x[-4:] if isinstance(x, str) and len(x) >= 4 else x, return_dtype=pl.Utf8).alias("Год выпуска"))
    processed_data = processed_data.with_columns(pl.struct(["Марка", "Модель", "Год выпуска"])
                                                .map_elements(lambda x: format_object_insurance(x["Марка"], x["Модель"], str(x["Год выпуска"])), return_dtype=pl.Utf8)
                                                .alias("Объект страхования"))
    return processed_data



# Чтение справочников (вспомогательные методы)
def get_planned_call_offset(base_type):
    return int(get_config_value(base_type, "плановая дата звонка cti"))

def get_lead_type(base_type):
    return get_config_value(base_type, "тип лида")

def get_insurance_group(base_type):
    return get_config_value(base_type, "группа продукта")

def get_priority(base_type):
    return get_config_value(base_type, "приоритет")

def get_product(base_type):
    return get_config_value(base_type, "продукт")

def get_type_of_insurance(base_type):
    return get_config_value(base_type, "вид страхования")

def get_link(base_type):
    return get_config_value(base_type, "ссылка")

def get_year_prolong_olds(base_type):
    return get_config_value(base_type, "год")



# Создание отдельных файлов
# Физ. лица
def create_person_file(processed_data: pl.DataFrame) -> pl.DataFrame:
    person = pl.DataFrame({
        "Id записи в DWH": processed_data["id физ лица"],
        "ФИО": processed_data["ФИО"],
        "Фамилия": processed_data["Фамилия"],
        "Имя": processed_data["Имя"],
        "Отчество": processed_data["Отчество"],
        "Дата рождения": processed_data["Дата рождения"],
        "Основной телефон": processed_data["Основной телефон"],
        "Мобильный телефон": processed_data["Телефон 2"],
        "Рабочий телефон": processed_data["Телефон 3"],
        "Телефон для рассылки 1": processed_data["Основной телефон"],
        "Телефон для рассылки 2": processed_data["Телефон 2"],
        "Телефон для рассылки 3": processed_data["Телефон 3"],
        "Основной email": processed_data["Основной e-mail"],
        "Регион": processed_data["Регион"],})
    person = person.with_columns(pl.col("Отчество").map_elements(get_gender_and_unique, return_dtype=pl.Utf8).alias("Пол")).unique(subset=["Id записи в DWH"], keep="first")
    return person

def create_filial_person_file(filial_data: pl.DataFrame) -> pl.DataFrame:
    filial_person = pl.DataFrame({
                    "Id записи в DWH": filial_data["id физ лица"],
                    "ФИО": filial_data["ФИО"],
                    "Фамилия": filial_data["Фамилия"],
                    "Имя": filial_data["Имя"],
                    "Отчество": filial_data["Отчество"],
                    "Дата рождения": filial_data["Дата рождения"],
                    "Основной телефон": filial_data["Основной телефон"],
                    "Мобильный телефон": filial_data["Телефон 2"],
                    "Рабочий телефон": filial_data["Телефон 3"],
                    "Телефон для рассылки 1": filial_data["Основной телефон"],
                    "Телефон для рассылки 2": filial_data["Телефон 2"],
                    "Телефон для рассылки 3": filial_data["Телефон 3"],
                    "Основной email": filial_data["Основной e-mail"],
                    "Регион": filial_data["Регион"],})
    filial_person = filial_person.with_columns(pl.col("Отчество").map_elements(get_gender_and_unique, return_dtype=pl.Utf8).alias("Пол")).unique(subset=["Id записи в DWH"], keep="first")
    return filial_person

def get_gender_and_unique(name: str) -> str:
    male_endings = [
        "ович", "евич", "ич", "ов", "ев", "ин", "ский", "овичи", "евичи", "ины", "яты", "ук", "ец", "ей", "инский", "еев", "овец", "ыш", "овичев", "ий", "ын", "уй", "их", "ек", "кевич", "сов", "аров", "зов",
        "итов", "ров", "овин", "инов", "я", "инский", "горов", "ор", "ус", "чук", "ый", "иненко", "инский", "еев", "ешкин", "енко", "овкин", "дьев", "енков", "ак", "ес", "оглы", "сон", "вар", "волод"]
    female_endings = [
        "овна", "евна", "ична", "ина", "ская", "ых", "ова", "ева", "ята", "ук", "ий", "ей", "их", "чук", "ек", "итова", "ас", "ина", "инская", "анна", "кова", "ова",
        "ян", "анова", "ина", "енко", "олина", "ая", "ю", "чевна", "анна", "очина", "ли", "унова", "цова", "лёвна", "кызы", "вна", "ушка", "а", "овина", "еевна"]
    if not name or name.strip() == "":
        return "о"
    name = name.lower()
    if any(name.endswith(end) for end in male_endings):
        return "Мужской"
    if any(name.endswith(end) for end in female_endings):
        return "Женский"
    return "о"

# Договоры
def create_contracts_file(processed_data:pl.DataFrame) -> pl.DataFrame:
    contracts = pl.DataFrame({
                    "Номер договора": processed_data["№ Договора К Пролонгации"],
                    "Вид страхования": processed_data["Вид страхования"],
                    "Канал продаж": processed_data["Канал"],
                    "Срок действия полиса": processed_data["Дата окончания страхования"],
                    "Страховая премия по договору": processed_data["Прошлый период Страховая премия"],
                    "Филиал ВСК": processed_data["Филиал ВСК"],
                    "Физ лицо.id записи в dwh": processed_data["id физ лица"],
                    "Вид полиса": processed_data["Вид полиса"],
                    "Шт., вероятность пролонгации": processed_data["Шт., вероятность пролонгации"],
                    "Руб., вероятность пролонгации": processed_data["Руб., вероятность пролонгации"],
                    "Ответственное подразделение": "Ипотека"})
    return contracts

def create_contracts_file_mbg(processed_data:pl.DataFrame) -> pl.DataFrame:
    contracts = pl.DataFrame({
                    "Номер договора": processed_data["№ Договора К Пролонгации"],
                    "Вид страхования": processed_data["Вид страхования"],
                    "Канал продаж": processed_data["Канал"],
                    "Срок действия полиса": processed_data["Дата окончания страхования"],
                    "Страховая премия по договору": processed_data["Прошлый период Страховая премия"],
                    "Филиал ВСК": processed_data["Филиал ВСК"],
                    "Физ лицо.id записи в dwh": processed_data["id физ лица"],
                    "Ответственное подразделение": "УДП Пролонгация"})
    return contracts

def create_contracts_file_kasko_osago(processed_data:pl.DataFrame, base_type) -> pl.DataFrame:
    contracts = pl.DataFrame({
                    "Номер договора": processed_data["№ Договора К Пролонгации"],
                    "Вид страхования": processed_data["Вид страхования"],
                    "Канал продаж": processed_data["Канал"],
                    "Срок действия полиса": processed_data["Дата окончания страхования"],
                    "Страховая премия по договору": processed_data["Прошлый период Страховая премия"],
                    "Филиал ВСК": processed_data["Филиал ВСК"],
                    "Физ лицо.id записи в dwh": processed_data["id физ лица"],
                    "VIN": processed_data["VIN"],
                    "Программа страхования": processed_data["Программа страхования"],
                    "Номер проекта": processed_data["Номер проекта"],
                    "Ответственное подразделение": f"{base_type}"})
    return contracts

def filial_contracts_kasko(filial_data:pl.DataFrame) -> pl.DataFrame:
    filial_contracts = pl.DataFrame({
                    "Номер договора": filial_data["№ Договора К Пролонгации"],
                    "Вид страхования": filial_data["Вид страхования"],
                    "Канал продаж": filial_data["Канал"],
                    "Срок действия полиса": filial_data["Дата окончания страхования"],
                    "Страховая премия по договору": filial_data["Прошлый период Страховая премия"],
                    "Филиал ВСК": filial_data["Филиал ВСК"],
                    "Физ лицо.id записи в dwh": filial_data["id физ лица"],
                    "VIN": filial_data["VIN"],
                    "Вид полиса": filial_data["Вид полиса"],
                    "Ответственное подразделение": "Филиал КАСКО"})
    return filial_contracts


def create_contracts_file_kasko(processed_data:pl.DataFrame, base_type) -> pl.DataFrame:
    contracts = pl.DataFrame({
                "Номер договора": processed_data["№ Договора К Пролонгации"],
                "Вид страхования": processed_data["Вид страхования"],
                "Канал продаж": processed_data["Канал"],
                "Срок действия полиса": processed_data["Дата окончания страхования"],
                "Страховая премия по договору": processed_data["Прошлый период Страховая премия"],
                "Филиал ВСК": processed_data["Филиал ВСК"],
                "Физ лицо.id записи в dwh": processed_data["id физ лица"],
                "VIN": processed_data["VIN"],
                "Вид полиса": processed_data["Вид полиса"],
                "Шт., Вероятность пролонгации": processed_data["Вероятность, шт."],
                "Руб., Вероятность пролонгации": processed_data["Вероятность, руб."],
                "Ответственное подразделение": f"{base_type}"})
    return contracts

def create_para_contracts_file_kasko(para_contracts_data:pl.DataFrame) -> pl.DataFrame:
    para_contracts = pl.DataFrame({
                "Номер договора": para_contracts_data["№ Договора К Пролонгации"],
                "Вид страхования": para_contracts_data["Вид страхования"],
                "Канал продаж": para_contracts_data["Канал"],
                "Срок действия полиса": para_contracts_data["Дата окончания страхования"],
                "Филиал ВСК": para_contracts_data["Филиал ВСК"],
                "Физ лицо.id записи в dwh": para_contracts_data["id физ лица"],
                "VIN": para_contracts_data["VIN"],
                "Страховая премия по договору": para_contracts_data["Прошлый период Страховая премия"],
                "Ответственное подразделение": "КАСКО",
                "Шт., Вероятность пролонгации": "0,6"})
    return para_contracts

def create_contracts_osago_kz_file(processed_data:pl.DataFrame) -> pl.DataFrame:
    contracts = pl.DataFrame({
                    "Номер договора": processed_data["№ Договора К Пролонгации"],
                    "Вид страхования": processed_data["Вид страхования"],
                    "Канал продаж": processed_data["Канал"],
                    "Срок действия полиса": processed_data["Дата окончания страхования"],
                    "Страховая премия по договору": processed_data["Прошлый период Страховая премия"],
                    "Филиал ВСК": processed_data["Филиал ВСК"],
                    "Физ лицо.id записи в dwh": processed_data["id физ лица"],
                    "VIN": processed_data["VIN"],
                    "Ответственное подразделение": "ОСАГО Пилот"})
    return contracts

def create_contracts_olds_osago_wa_file(processed_data:pl.DataFrame) -> pl.DataFrame:
    contracts = pl.DataFrame({
                    "Номер договора": processed_data["№ Договора К Пролонгации"],
                    "Вид страхования": processed_data["Вид страхования"],
                    "Канал продаж": processed_data["Канал"],
                    "Срок действия полиса": processed_data["Дата окончания страхования"],
                    "Страховая премия по договору": processed_data["Прошлый период Страховая премия"],
                    "Филиал ВСК": processed_data["Филиал ВСК"],
                    "Физ лицо.id записи в dwh": processed_data["id физ лица"],
                    "VIN": processed_data["VIN"],
                    "Ответственное подразделение": "Потеряшки",
                    "Номер сервисной карты": "3",
                    "Номер проекта": "0"})
    return contracts

# Связанные лиды
def create_linked_leads_file(self, processed_data:pl.DataFrame) -> pl.DataFrame:
    linked_leads = processed_data.clone()
    processed_data = processed_data.unique(subset=["id физ лица"], keep="first")
    matched_ids = linked_leads.join(
        processed_data.select(["ID_внешней системы"]),
        left_on="ID_внешней системы",
        right_on="ID_внешней системы",
        how="inner")["ID_внешней системы"]
    linked_leads = linked_leads.filter(~pl.col("ID_внешней системы").is_in(matched_ids))
    linked_leads = linked_leads.join(
        processed_data.select([pl.col("id физ лица"), pl.col("ID_внешней системы").alias("ID_внешней системы основа")]),
        left_on="id физ лица",
        right_on="id физ лица",
        how="left")
    task_number = "".join(self.number) if isinstance(self.number, set) else str(self.number)
    linked_leads = linked_leads.with_columns([
        (task_number + "_ипотека_связь_" + datetime.now().strftime("%d.%m.%Y") + "_" +
        pl.arange(1, len(linked_leads) + 1).cast(pl.Utf8)).alias("ID_внешней системы"),
        pl.lit("1.3 Ипотека связанные Лиды").alias("Кампания")])
    return linked_leads

# Парные лиды
def set_default_count_columns_para_leads(para_leads):
    para_leads = para_leads.drop("№ Договора К Пролонгации", "Плановая дата звонка CTI", "Приоритет", "Передан в АКЦ", "Вероятность, шт.", "Вероятность, руб.")
    para_leads = para_leads.rename({"ID_внешней системы": "ID_внешней системы основа", "Парный договор": "№ Договора К Пролонгации"})
    para_leads = para_leads.with_columns([pl.lit("ОСАГО ФЛ").alias("Продукт"),
        pl.lit("Обязательное страхование АГО ФЛ").alias("Вид страхования"),
        pl.lit("Обязательное страхование АГО").alias("Группа продукта"),
        pl.lit("1.1 Парное ОСАГО+НБ (для УП КАСКО)").alias("Кампания"),
        pl.lit("400000").alias("Прошлый период Страховая сумма"),
        pl.lit("").alias("Прошлый период Страховая премия")])
    para_leads = para_leads.with_columns(pl.col("№ Договора К Пролонгации").map_elements(lambda x: "Парное ОСАГО" if x is not None else "Новый бизнес", return_dtype=pl.Utf8).alias("Тип лида"))
    para_leads = para_leads.with_columns(pl.col("Тип лида").replace(None, "Новый бизнес"))
    return para_leads

def get_strah_prem_kasko(para_leads):
    server_url = "http://192.168.50.220:5000/sql/query"
    contract_numbers = para_leads["№ Договора К Пролонгации"].drop_nulls().unique().to_list()
    contracts_strss = ", ".join([f"'{contract}'" for contract in contract_numbers])
    sql_query = load_sql_query('C:/Users/EPopkov/Documents/Orion Dynamics/nexus/SQL/ACTUAR2 пара.txt', contracts_strss=contracts_strss)
    response_data = execute_sql_query(server_url, "ACTUAR2", sql_query)
    results = response_data['results'][0]
    columns = results['columns']
    rows = results['rows']

    df = pl.DataFrame(rows)
    data_dict_actuar2 = dict(
        zip(
            df["номер договора к пролонгации"].to_list(),
            zip(df["Премия"].to_list())))

    required_columns_actuar2 = ["№ Договора К Пролонгации", "Прошлый период Страховая премия"]
    
    para_leads = ensure_columns_exist(para_leads, required_columns_actuar2)
    para_leads = update_dataframe_from_actuar2(
        para_leads,
        data_dict_actuar2,
        mapping={
            "Прошлый период Страховая премия": 0})
    
    para_leads = para_leads.with_columns(pl.col("Прошлый период Страховая премия").map_elements(
            lambda x: None if not x.strip() else float(x),
            return_dtype=pl.Float64).alias("Прошлый период Страховая премия"))
    return para_leads
    
def update_dataframe_from_actuar2(df, data_dict, mapping):
    updated_rows = []
    for row in df.iter_rows(named=True):
        contract_number = row["№ Договора К Пролонгации"]
        if contract_number in data_dict:
            data = data_dict[contract_number]
            for key, value in mapping.items():
                if row.get(key) is None or row.get(key) == "":
                    row[key] = data[value]
        updated_rows.append(row)
    return pl.DataFrame(updated_rows)

def clear_para_leads(para_leads):
    columns_to_clear = ["Дата окончания страхования", "Прошлый период Страховая премия", "Прошлый период Страховая сумма", "Дилер", "Логин дилера", "Точка продаж", "Категория партнера", "Номер агентского договора"]
    para_leads = para_leads.with_columns([
        pl.when(pl.col("№ Договора К Пролонгации").is_null())
        .then(None)
        .otherwise(pl.col(col))
        .alias(col)
        for col in columns_to_clear])
    return para_leads

# Тачки
def create_cars(processed_data:pl.DataFrame) -> pl.DataFrame:
    cars = pl.DataFrame({
        "Лид.id": "",
        "Номер договора": processed_data["№ Договора К Пролонгации"],
        "Марка.id": processed_data["Марка"].cast(pl.Utf8),
        "Модель.id": processed_data["Модель"].cast(pl.Utf8),
        "Год выпуска ТС": processed_data["Год выпуска"],
        "VIN": processed_data["VIN"]})
    cars = cars.with_columns([
        pl.col("Марка.id").str.to_lowercase(),
        pl.col("Модель.id").str.to_lowercase()])
    lookup_data = pl.read_parquet("C:/Users/EPopkov/Documents/Orion Dynamics/nexus/references/Автострахование марка.parquet")
    lookup_data2 = pl.read_parquet("C:/Users/EPopkov/Documents/Orion Dynamics/nexus/references/Автострахование модель.parquet")
    lookup_data = lookup_data.with_columns([
        pl.col("Наименование").cast(pl.Utf8).str.to_lowercase(),
        pl.col("Id впр").cast(pl.Utf8)])
    lookup_data2 = lookup_data2.with_columns([
        pl.col("Наименование").cast(pl.Utf8).str.to_lowercase(),
        pl.col("Id впр").cast(pl.Utf8)])
    lookup_dict_1 = dict(zip(lookup_data["Наименование"], lookup_data["Id впр"]))
    lookup_dict_2 = dict(zip(lookup_data2["Наименование"], lookup_data2["Id впр"]))
    cars = cars.with_columns([
        pl.when(pl.col("Марка.id").is_in(lookup_dict_1.keys()))
        .then(pl.col("Марка.id").map_elements(lambda x: lookup_dict_1.get(x, x), return_dtype=pl.Utf8))
        .otherwise(None)
        .alias("Марка.id"),
        pl.when(pl.col("Модель.id").is_in(lookup_dict_2.keys()))
        .then(pl.col("Модель.id").map_elements(lambda x: lookup_dict_2.get(x, x), return_dtype=pl.Utf8))
        .otherwise(None)
        .alias("Модель.id")])
    
    cars = cars.with_columns(pl.col("Марка.id").replace(None, "039eed22-7197-4f4f-bc0d-2695aad459cd"))
    cars = cars.with_columns(pl.col("Модель.id").replace(None, "15408002-648c-44b6-bd98-00239f788646"))
    return cars

# Генерация коротких ссылок
def create_short_links(processed_data):
    
    # Отключение предупреждений
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    warnings.filterwarnings("ignore", category=DeprecationWarning)

    def get_token():
        auth_url = "https://auth.vsk.ru/auth/realms/users_auth/protocol/openid-connect/token"
        auth_payload = {"grant_type": "password", "client_id": "prod-keycloak_users_auth_lanshort_url_front-1",
                        "username": "Epopkov", "password": "88H77BTJKK03uV!"}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        try:
            response = requests.post(auth_url, data=auth_payload, headers=headers, verify=False)
            response.raise_for_status()
            return response.json().get("access_token")
        except RequestException as e:
            logging.error(f"Ошибка при получении токена: {e}")
            raise
        
    def create_short_urls_with_originals(token, links, max_retries=30, retry_delay=2):
        api_url = "https://prod.short-url2.apps.prd-okd-lan.vsk.ru/api/v1/url"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        expiration_date = (datetime.utcnow() + timedelta(days=365)).isoformat() + "Z"
        batch_size = 100
        short_links_dict = {}
        count = 0
        i = 0
        while i < len(links):
            count += 100
            batch_links = links[i:i + batch_size]
            payload = {"urls": [{"originalUrl": link, "expirationDate": expiration_date, "isExpiration": True,
                                "systemType": "short_url_ui", "userName": "epopkov"} for link in batch_links]}
            success = False
            for attempt in range(max_retries + 1):
                try:
                    response = requests.post(api_url, json=payload, headers=headers, verify=False)
                    response.raise_for_status()
                    response_data = response.json()
                    if isinstance(response_data, dict) and "data" in response_data:
                        for item in response_data["data"]:
                            original_url = item.get("originalUrl")
                            short_url = f"https://www.vsk.ru/l/{item['hash']}"
                            short_links_dict[original_url] = short_url
                        success = True
                        break
                    else:
                        raise Exception(f"Неподдерживаемый формат ответа сервера: {response_data}")
                except (RequestException, ValueError, Exception) as e:
                    if attempt < max_retries:
                        logging.warning(f"Ошибка при создании коротких ссылок (попытка {attempt + 1}/{max_retries + 1}): {e}.  Повторная попытка через {retry_delay} секунды...")
                        import time
                        time.sleep(retry_delay)
                    else:
                        logging.error(f"Не удалось создать короткие ссылки после {max_retries + 1} попыток: {e}")
                        success = False
                        break
            if success:
                i += batch_size
            else:
                logging.warning(f"Не удалось обработать пакет ссылок, повторная отправка")
        return short_links_dict
    
    def process_data(df):
        links = df["Ссылка на проект"].to_list()
        token = get_token()
        short_links_dict = create_short_urls_with_originals(token, links)
        short_links = [short_links_dict.get(link, link) for link in links]
        return df.with_columns(pl.Series("Ссылка на проект", short_links))
    
    processed_data = process_data(processed_data)
    return processed_data