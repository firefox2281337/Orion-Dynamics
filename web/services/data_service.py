# web/services/data_service.py
"""
Сервис для работы с данными и обработки бизнес-логики
"""

import io
import json
import requests
import polars as pl
import pandas as pd
from datetime import datetime, date, timedelta
from web.utils.logging_helper import log_error


class DataService:
    """Сервис для работы с данными"""
    
    def __init__(self):
        self.api_url = 'http://192.168.50.220:5000/sql/query'
    
    def get_kasko_prolongation_data(self, start_date=None, end_date=None, 
                                   insurance_type=None, channel=None, branch_code=None):
        """
        Получает данные о пролонгации КАСКО
        
        Args:
            start_date: Начальная дата
            end_date: Конечная дата
            insurance_type: Типы страхования
            channel: Канал продаж
            branch_code: Коды филиалов
            
        Returns:
            dict: Результаты запроса или None
        """
        try:
            from web.sql_models import megahelper_sql
            
            # Форматирование дат
            if isinstance(start_date, str):
                date_object = datetime.strptime(start_date, '%Y-%m-%d')
                period_start = date_object.strftime('%Y_%m')
            else:
                period_start = start_date or datetime.now().strftime('%Y_%m')

            if isinstance(end_date, str):
                date_object = datetime.strptime(end_date, '%Y-%m-%d')
                period_end = date_object.strftime('%Y_%m')
            else:
                period_end = end_date or datetime.now().strftime('%Y_%m')

            # Построение WHERE clause
            where_clauses = [
                f"p.yyyy_mm BETWEEN @period_start AND @period_end",
                "p.[База для пролонгации] <> 0",
                "p.sing_full IS NULL",
            ]

            if insurance_type:
                insurance_type_str = ', '.join(f"'{item.strip()}'" for item in insurance_type)
                where_clauses.append(f"p.вид IN ({insurance_type_str})")

            if channel:
                where_clauses.append(f"p.Saleschannelid_2015 in ({channel})")

            if branch_code:
                branch_code_str = ', '.join(f"'{item.strip()}'" for item in branch_code)
                where_clauses.append(f"p.[Код филиала] in ({branch_code_str})")

            where_clause = " AND ".join(where_clauses)
            sql_query = megahelper_sql(period_start, period_end, where_clause)
            
            payload = {
                "query": sql_query,
                "database": "ACTUAR2"
            }
            
            response = requests.post(self.api_url, json=payload)
            response.raise_for_status()
            response_json = response.json()

            if "results" not in response_json or not isinstance(response_json["results"], list):
                return None

            results = response_json["results"]
            if not results:
                return {"columns": [], "rows": []}

            if len(results) > 0 and "columns" in results[0] and "rows" in results[0]:
                return results[0]
            else:
                return None

        except requests.exceptions.RequestException as e:
            log_error(f"Ошибка запроса к API: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            log_error(f"Ошибка декодирования JSON: {str(e)}")
            return None
        except Exception as e:
            log_error(f"Общая ошибка в get_kasko_prolongation_data: {str(e)}")
            return None
    
    def execute_sql_query(self, contracts_string, query_type="contacts"):
        """
        Выполняет SQL запрос
        
        Args:
            contracts_string: Строка с номерами договоров
            query_type: Тип запроса (contacts, registration, passport)
            
        Returns:
            list: Результаты запроса
        """
        try:
            if query_type == "contacts":
                from web.sql_models import get_contacts_sql
                query = get_contacts_sql(contracts_string)
            elif query_type == "registration":
                query = f"""select * from public._subject_master_fl_address 
                           where subject_master_id in {contracts_string};"""
            elif query_type == "passport":
                query = f"""select subject_master_id, passport, passport_issue_org,
                           passport_issue_date,passport_kp from public._subject_master_fl_document 
                           where subject_master_id in {contracts_string};"""
            else:
                raise ValueError(f"Неподдерживаемый тип запроса: {query_type}")
            
            request_body = json.dumps({
                "query": query.replace('"', '""'),
                "database": "PostgreSQL"
            })
            
            response = requests.post(
                self.api_url,
                data=request_body,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            response_json = response.json()
            
            if "rows" in response_json:
                return response_json["rows"]
            else:
                log_error("Ответ сервера не содержит данных 'rows'")
                return None
                
        except requests.exceptions.RequestException as e:
            log_error(f"Ошибка при запросе: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            log_error(f"Ошибка при декодировании JSON: {str(e)}")
            return None
    
    def get_gender_from_patronymic(self, name: str):
        """Определяет пол по отчеству"""
        male_endings = [
            "ович", "евич", "ич", "ов", "ев", "ин", "ский", "овичи", "евичи", "ины", "яты", "ук", "ец", "ей",
            "инский", "еев", "овец", "ыш", "овичев", "ий", "ын", "уй", "их", "ек", "кевич", "сов", "аров",
            "зов", "итов", "ров", "овин", "инов", "я", "инский", "горов", "ор", "ус", "чук", "ый", "иненко",
            "инский", "еев", "ешкин", "енко", "овкин", "дьев", "енков", "ак", "ес", "оглы", "сон", "вар", "волод"]
        female_endings = [
            "овна", "евна", "ична", "ина", "ская", "ых", "ова", "ева", "ята", "ук", "ий", "ей", "их", "чук",
            "ек", "итова", "ас", "ина", "инская", "анна", "кова", "ова", "ян", "анова", "ина", "енко", "олина",
            "ая", "ю", "чевна", "анна", "очина", "ли", "унова", "цова", "лёвна", "кызы", "вна", "ушка", "а", "овина", "еевна"]

        if not name or name.strip() == "":
            return "Мужской"

        name = name.lower()

        if any(name.endswith(end) for end in male_endings):
            return "Мужской"

        if any(name.endswith(end) for end in female_endings):
            return "Женский"

        return "Мужской"
    
    def process_metragi(self, file):
        """
        Обрабатывает файл метражей
        
        Args:
            file: Загруженный файл
            
        Returns:
            list: Список файлов для скачивания
        """
        try:
            # Читаем Excel файл
            file_content = file.read()
            excel_file = io.BytesIO(file_content)
            leads = pl.DataFrame(pl.read_excel(excel_file))
            
            # Добавляем необходимые колонки
            leads = leads.with_columns([
                pl.lit(30).alias("Скидка по спец предложению"),
                pl.lit("3.3 НЦП Кросс пилот метражи").alias("Кампания"),
                pl.lit("РОССИЯ, Г. ДОРОГИЕ ПЛИНТУСА, ПР. ЗОЛОТОЙ КХНИ, Д. 8, КВ. 777").alias("Объект страхования"),
                pl.lit("Имущество граждан").alias("Вид страхования"),
                pl.lit("Имущество ФЛ Кросс").alias("Группа продукта"),
                pl.lit("Метражи").alias("Продукт"),
                pl.lit("Cross").alias("Тип лида"),
                pl.lit("Интернет-продажи").alias("Канал")
            ])

            # Генерируем ID
            current_date = datetime.now().strftime("%d.%m.%Y")
            leads = leads.with_columns(
                (f"1метражи_пилот_осоцкова_{current_date}_" + 
                 pl.arange(1, len(leads) + 1).cast(pl.Utf8)).alias("ID_внешней системы")
            )

            # Устанавливаем даты
            today = date.today()
            end_date = today + timedelta(days=7)
            leads = leads.with_columns([
                pl.lit(end_date).alias("Дата окончания страхования"),
                pl.lit(end_date).alias("Планируемая дата сделки")
            ])
            leads = leads.with_columns([
                pl.col("Дата окончания страхования").dt.strftime("%Y-%m-%d").alias("Дата окончания страхования"),
                pl.col("Дата окончания страхования").dt.strftime("%Y-%m-%d").alias("Планируемая дата сделки")
            ])

            # Получаем контактные данные
            contacts = self._process_contacts(leads)
            
            # Получаем адреса регистрации
            reg = self._process_registration(contacts)
            
            # Получаем паспортные данные
            passport = self._process_passport(contacts)
            
            # Создаем данные ипотеки
            ipo = self._create_ipoteka_data(leads)
            
            # Очищаем leads
            leads = self._clean_leads_data(leads)
            
            # Создаем файлы для скачивания
            download_files = []
            
            # Физ. лица
            mem_fl = io.BytesIO()
            contacts.write_excel(mem_fl)
            mem_fl.seek(0)
            download_files.append(('Физ. лица.xlsx', mem_fl.getvalue()))
            
            # Лиды
            mem_leads = io.BytesIO()
            leads.write_excel(mem_leads)
            mem_leads.seek(0)
            download_files.append(('Лиды.xlsx', mem_leads.getvalue()))
            
            # Ипотека
            mem_ipo = io.BytesIO()
            ipo.write_excel(mem_ipo)
            mem_ipo.seek(0)
            download_files.append(('Ипотека.xlsx', mem_ipo.getvalue()))
            
            # Паспортные данные
            mem_reg = io.BytesIO()
            passport.write_excel(mem_reg)
            mem_reg.seek(0)
            download_files.append(('Рег. документ.xlsx', mem_reg.getvalue()))
            
            # Адреса
            mem_adress = io.BytesIO()
            reg.write_excel(mem_adress)
            mem_adress.seek(0)
            download_files.append(('Адрес контакта.xlsx', mem_adress.getvalue()))
            
            return download_files
            
        except Exception as e:
            log_error(f"Ошибка обработки метражей: {str(e)}")
            raise
    
    def _process_contacts(self, leads):
        """Обрабатывает контактные данные"""
        contacts = leads.select("Номер договора", "№ Договора К Пролонгации")
        
        # Получаем данные по основным договорам
        contracts = (contacts.select(pl.col("Номер договора").cast(pl.Utf8).alias("Номер договора_str"))
                    .filter(pl.col("Номер договора_str").is_not_null() & (pl.col("Номер договора_str") != ""))
                    .with_columns(pl.format("('{}')", pl.col("Номер договора_str")).alias("Номер договора_quoted"))
                    .select(pl.col("Номер договора_quoted").str.concat(",").alias("contracts")))

        if not contracts.is_empty():
            contracts_string = contracts["contracts"].item()
            result_rows = self.execute_sql_query(contracts_string, "contacts")

            if result_rows:
                df_from_sql = pd.DataFrame(result_rows)
                if not df_from_sql.empty:
                    df_from_sql = df_from_sql.rename(columns={'contract_number': 'Номер договора'})
                    polars_df_from_sql = pl.from_pandas(df_from_sql)
                    contacts = contacts.join(polars_df_from_sql, on="Номер договора", how="left")

        # Обрабатываем данные и создаем финальную структуру
        contacts = self._finalize_contacts(contacts)
        return contacts
    
    def _process_registration(self, contacts):
        """Обрабатывает данные регистрации"""
        reg = contacts.select("Id записи в DWH")
        
        if not reg.is_empty():
            contracts = (reg.select(pl.col("Id записи в DWH").cast(pl.Utf8).alias("Id записи в DWH_str"))
                        .filter(pl.col("Id записи в DWH_str").is_not_null() & (pl.col("Id записи в DWH_str") != ""))
                        .with_columns(pl.format("'{}'", pl.col("Id записи в DWH_str")).alias("Id записи в DWH_quoted"))
                        .select(pl.format("({})", pl.col("Id записи в DWH_quoted").str.concat(", ")).alias("contracts")))

            if not contracts.is_empty():
                contracts_string = contracts["contracts"].item()
                result_rows = self.execute_sql_query(contracts_string, "registration")

                if result_rows:
                    df_from_sql_reg = pd.DataFrame(result_rows)
                    if not df_from_sql_reg.empty:
                        polars_df_from_sql = pl.from_pandas(df_from_sql_reg)
                        reg_1 = polars_df_from_sql.select("subject_master_id", "addr_full")
                        reg_1 = reg_1.with_columns([
                            pl.lit("Адрес регистрации").alias("Тип адреса"),
                            pl.lit("ИСТИНА").alias("Адреса нет в справочнике"),
                            pl.col("subject_master_id").cast(pl.Utf8).alias("subject_master_id")
                        ])
                        reg_1 = reg_1.rename({"addr_full": "Полный адрес"})
                        
                        reg = reg.with_columns(pl.col("Id записи в DWH").cast(pl.Utf8).alias("Id записи в DWH"))
                        reg = reg.join(reg_1, left_on="Id записи в DWH", right_on="subject_master_id", how="left")

        return reg
    
    def _process_passport(self, contacts):
        """Обрабатывает паспортные данные"""
        passport = contacts.select("Id записи в DWH")
        
        if not passport.is_empty():
            contracts = (passport.select(pl.col("Id записи в DWH").cast(pl.Utf8).alias("Id записи в DWH_str"))
                        .filter(pl.col("Id записи в DWH_str").is_not_null() & (pl.col("Id записи в DWH_str") != ""))
                        .with_columns(pl.format("'{}'", pl.col("Id записи в DWH_str")).alias("Id записи в DWH_quoted"))
                        .select(pl.format("({})", pl.col("Id записи в DWH_quoted").str.concat(", ")).alias("contracts")))

            if not contracts.is_empty():
                contracts_string = contracts["contracts"].item()
                result_rows = self.execute_sql_query(contracts_string, "passport")

                if result_rows:
                    df_from_sql_reg = pd.DataFrame(result_rows)
                    if not df_from_sql_reg.empty:
                        passport_1 = pl.from_pandas(df_from_sql_reg)
                        passport_1 = passport_1.with_columns(
                            pl.col("passport_issue_date").str.strptime(pl.Datetime, "%a, %d %b %Y %H:%M:%S GMT")
                            .dt.strftime("%d.%m.%Y").alias("passport_issue_date")
                        )
                        passport_1 = passport_1.with_columns([
                            pl.col("passport_issue_date").fill_null("Нет данных"),
                            pl.col("passport_issue_org").fill_null("Заглушка"),
                            pl.col("passport_kp").fill_null("Нет данных")
                        ])
                        passport_1 = passport_1.with_columns([
                            pl.col("passport").str.slice(0, 4).alias("Серия"),
                            pl.col("passport").str.slice(-6, 6).alias("Номер")
                        ])
                        passport_1 = passport_1.drop("passport")
                        passport_1 = passport_1.rename({
                            "passport_issue_date": "Дата выдачи",
                            "passport_issue_org": "Кем выдан",
                            "passport_kp": "Код подразделения"
                        })
                        passport_1 = passport_1.with_columns(pl.col("subject_master_id").cast(pl.Utf8).alias("subject_master_id"))
                        
                        passport = passport.join(passport_1, left_on="Id записи в DWH", right_on="subject_master_id", how="left")
                        passport = passport.with_columns(pl.lit("Паспорт РФ").alias("Тип документа"))

        return passport
    
    def _create_ipoteka_data(self, leads):
        """Создает данные ипотеки"""
        ipo = leads.select("ID_внешней системы")
        ipo = ipo.with_columns([
            pl.lit("РОССИЯ, Г. ДОРОГИЕ ПЛИНТУСА, ПР. ЗОЛОТОЙ КХНИ, Д. 8, КВ. 777").alias("Полный адрес"),
            pl.lit("Квартира").alias("Вид объекта"),
            pl.lit("2020").alias("Год постройки"),
            pl.lit("12").alias("Этажность здания"),
            pl.lit("40").alias("Площадь квартиры")
        ])
        return ipo
    
    def _finalize_contacts(self, contacts):
        """Финализирует обработку контактов"""
        contacts = contacts.select([
            "Номер договора", "mdm_id", "phone", "phone2", "email", "birth", "s_name", "f_name", "m_name"
        ])
        contacts = contacts.with_columns(pl.col("m_name").fill_null("-"))

        # Приводим типы данных
        for col in ["mdm_id", "phone", "phone2"]:
            if col in contacts.columns:
                contacts = contacts.with_columns(
                    pl.col(col).cast(pl.Float64).round(0).cast(pl.Int64).cast(pl.Utf8).alias(col)
                )
        
        contacts = contacts.with_columns(
            pl.col("birth").str.strptime(pl.Datetime, "%a, %d %b %Y %H:%M:%S GMT")
            .dt.strftime("%d.%m.%Y").alias("birth")
        )

        for col in ["Номер договора", "email", "s_name", "f_name", "m_name"]:
            contacts = contacts.with_columns(pl.col(col).cast(pl.Utf8).alias(col))
        
        contacts = contacts.with_columns(
            pl.format("{} {} {}", pl.col("s_name"), pl.col("f_name"), pl.col("m_name")).alias("ФИО")
        )
        contacts = contacts.with_columns(pl.lit("Россия").alias("Гражданство"))

        # Переименовываем колонки
        contacts = contacts.rename({
            "mdm_id": "Id записи в DWH",
            "phone": "Основной телефон",
            "phone2": "Мобильный телефон",
            "email": "Основной email",
            "birth": "Дата рождения",
            "s_name": "Фамилия",
            "f_name": "Имя",
            "m_name": "Отчество",
        })

        # Определяем пол и убираем дубликаты
        contacts = contacts.with_columns(
            pl.col("Отчество").map_elements(
                self.get_gender_from_patronymic, 
                return_dtype=pl.Utf8
            ).alias("Пол")
        ).unique(subset=["Id записи в DWH"], keep="first")

        return contacts
    
    def _clean_leads_data(self, leads):
        """Очищает данные лидов"""
        leads = leads.drop([
            "Номер договора", "№ Договора К Пролонгации", "Физ.лицо.Id", 
            "Физ.лицо.ФИО", "Физ.лицо.Фамилия", "Физ.лицо.Имя", "Физ.лицо.Отчество", 
            "Регион", "Банк"
        ])
        
        leads = leads.with_columns([
            pl.col("Дата окончания страхования").cast(pl.Date).dt.strftime("%d.%m.%Y").alias("Дата окончания страхования"),
            pl.col("Планируемая дата сделки").cast(pl.Date).dt.strftime("%d.%m.%Y").alias("Планируемая дата сделки"),
            (pl.col("Дата рождения") - 25569).cast(pl.Date).dt.strftime("%d.%m.%Y").alias("Дата рождения")
        ])
        
        return leads