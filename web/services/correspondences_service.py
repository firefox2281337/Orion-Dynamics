# web/services/correspondences_service.py
"""
Сервис для работы с соответствиями заголовков
"""

import os
import pandas as pd
from pathlib import Path


class CorrespondencesService:
    """Сервис для управления соответствиями заголовков файлов"""
    
    def __init__(self, base_path=None):
        self.base_path = base_path or r"C:\Users\EPopkov\Documents\Orion Dynamics\nexus\references\correspondences\prolong"
        os.makedirs(self.base_path, exist_ok=True)
    
    def get_correspondence_file_path(self, register_type):
        """
        Получает путь к файлу соответствий для типа реестра
        
        Args:
            register_type: Тип реестра
            
        Returns:
            str: Путь к файлу соответствий
        """
        return os.path.join(self.base_path, f"{register_type}_correspondences.parquet")
    
    def load_correspondences(self, register_type):
        """
        Загружает соответствия для типа реестра
        
        Args:
            register_type: Тип реестра
            
        Returns:
            pandas.DataFrame: DataFrame с соответствиями или None
        """
        correspondence_path = self.get_correspondence_file_path(register_type)
        
        if not os.path.exists(correspondence_path):
            return None
        
        try:
            return pd.read_parquet(correspondence_path)
        except Exception as e:
            print(f"Ошибка загрузки соответствий: {str(e)}")
            return None
    
    def auto_map_headers(self, register_type, template_headers, file_headers):
        """
        Автоматически сопоставляет заголовки на основе файла соответствий
        
        Args:
            register_type: Тип реестра
            template_headers: Заголовки шаблона
            file_headers: Заголовки из файла
            
        Returns:
            dict: Словарь сопоставлений
        """
        correspondences_df = self.load_correspondences(register_type)
        mappings = {}
        
        if correspondences_df is not None:
            try:
                # Создаем словарь: Registry Header -> список Excel Headers
                correspondences_dict = {}
                for _, row in correspondences_df.iterrows():
                    registry_header = row['Registry Header']
                    excel_header = row['Excel Header']
                    
                    if registry_header not in correspondences_dict:
                        correspondences_dict[registry_header] = []
                    correspondences_dict[registry_header].append(excel_header)
                
                # Для каждого заголовка шаблона ищем первый подходящий Excel Header
                for registry_header in template_headers:
                    excel_headers_list = correspondences_dict.get(registry_header, [])
                    for excel_header in excel_headers_list:
                        if excel_header in file_headers:
                            mappings[registry_header] = excel_header
                            break
                            
            except Exception as e:
                print(f"Ошибка автоматического сопоставления: {str(e)}")
        
        return mappings
    
    def save_correspondences(self, register_type, mappings):
        """
        Сохраняет соответствия заголовков
        
        Args:
            register_type: Тип реестра
            mappings: Словарь сопоставлений
            
        Returns:
            bool: True если сохранение успешно
        """
        try:
            correspondence_path = self.get_correspondence_file_path(register_type)
            
            # Создаем новые данные
            new_data = pd.DataFrame({
                'Registry Header': list(mappings.keys()),
                'Excel Header': list(mappings.values())
            })
            
            # Если файл существует, объединяем данные
            if os.path.exists(correspondence_path):
                try:
                    existing_data = pd.read_parquet(correspondence_path)
                    
                    # Объединяем старые и новые данные
                    updated_data = pd.concat([existing_data, new_data], ignore_index=True)
                    updated_data = updated_data.drop_duplicates(
                        subset=['Registry Header', 'Excel Header'], 
                        keep='last'
                    )
                except Exception as e:
                    print(f"Ошибка объединения данных: {str(e)}")
                    updated_data = new_data
            else:
                updated_data = new_data
            
            # Сохраняем обновленные данные
            updated_data.to_parquet(correspondence_path, engine='pyarrow', index=False)
            return True
            
        except Exception as e:
            print(f"Ошибка сохранения соответствий: {str(e)}")
            return False
    
    def get_all_correspondences(self, register_type):
        """
        Получает все соответствия для типа реестра
        
        Args:
            register_type: Тип реестра
            
        Returns:
            dict: Словарь всех соответствий
        """
        correspondences_df = self.load_correspondences(register_type)
        
        if correspondences_df is None:
            return {}
        
        correspondences_dict = {}
        for _, row in correspondences_df.iterrows():
            registry_header = row['Registry Header']
            excel_header = row['Excel Header']
            
            if registry_header not in correspondences_dict:
                correspondences_dict[registry_header] = []
            correspondences_dict[registry_header].append(excel_header)
        
        return correspondences_dict
    
    def delete_correspondence(self, register_type, registry_header, excel_header=None):
        """
        Удаляет соответствие
        
        Args:
            register_type: Тип реестра
            registry_header: Заголовок реестра
            excel_header: Заголовок Excel (если None, удаляются все для registry_header)
            
        Returns:
            bool: True если удаление успешно
        """
        try:
            correspondences_df = self.load_correspondences(register_type)
            
            if correspondences_df is None:
                return False
            
            if excel_header is None:
                # Удаляем все соответствия для registry_header
                updated_data = correspondences_df[
                    correspondences_df['Registry Header'] != registry_header
                ]
            else:
                # Удаляем конкретное соответствие
                updated_data = correspondences_df[
                    ~((correspondences_df['Registry Header'] == registry_header) & 
                      (correspondences_df['Excel Header'] == excel_header))
                ]
            
            correspondence_path = self.get_correspondence_file_path(register_type)
            updated_data.to_parquet(correspondence_path, engine='pyarrow', index=False)
            return True
            
        except Exception as e:
            print(f"Ошибка удаления соответствия: {str(e)}")
            return False