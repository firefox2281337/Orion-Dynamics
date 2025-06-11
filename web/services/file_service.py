# web/services/file_service.py
"""
Сервис для работы с файлами
"""

import os
import json
import zipfile
import base64
import py7zr
import mammoth
from pathlib import Path
from docx import Document
from core.config.db_config import DATA_PATH, FILES_DIR


class FileService:
    """Сервис для работы с файлами"""
    
    def __init__(self):
        self.data_path = DATA_PATH
        self.files_dir = FILES_DIR
    
    def load_files(self):
        """Загрузка списка файлов из JSON"""
        try:
            with open(self.data_path, encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return []
    
    def get_file_by_id(self, file_id):
        """Получение файла по ID"""
        files = self.load_files()
        return next((f for f in files if f['id'] == file_id), None)
    
    def get_file_path(self, filename):
        """Получение полного пути к файлу"""
        return os.path.join(self.files_dir, filename)
    
    def get_file_type(self, extension):
        """Определение типа файла по расширению"""
        mapping = {
            '.zip': 'archive',
            '.rar': 'archive',
            '.7z': 'archive',
            '.docx': 'document',
            '.doc': 'document',
            '.pdf': 'document',
            '.txt': 'text',
            '.md': 'text',
            '.jpg': 'image',
            '.jpeg': 'image',
            '.png': 'image',
            '.gif': 'image',
            '.svg': 'image',
            '.mp3': 'audio',
            '.wav': 'audio',
            '.mp4': 'video',
            '.avi': 'video',
            '.py': 'code',
            '.js': 'code',
            '.html': 'code',
            '.css': 'code',
            '.json': 'code'
        }
        return mapping.get(extension.lower(), 'other')
    
    def get_file_icon(self, extension):
        """Определение иконки файла по типу"""
        mapping = {
            '.zip': 'file-archive',
            '.rar': 'file-archive',
            '.7z': 'file-archive',
            '.docx': 'file-word',
            '.doc': 'file-word',
            '.pdf': 'file-pdf',
            '.txt': 'file-alt',
            '.md': 'file-alt',
            '.jpg': 'file-image',
            '.jpeg': 'file-image',
            '.png': 'file-image',
            '.gif': 'file-image',
            '.svg': 'file-image',
            '.mp3': 'file-audio',
            '.wav': 'file-audio',
            '.mp4': 'file-video',
            '.avi': 'file-video',
            '.py': 'file-code',
            '.js': 'file-code',
            '.html': 'file-code',
            '.css': 'file-code',
            '.json': 'file-code'
        }
        return mapping.get(extension.lower(), 'file')
    
    def format_size(self, size_bytes):
        """Форматирование размера файла"""
        if size_bytes < 0:
            return "0 B"
            
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    def format_date(self, date_tuple):
        """Форматирование даты из tuple в строку"""
        year, month, day, hour, minute, second = date_tuple
        return f"{day:02d}.{month:02d}.{year} {hour:02d}:{minute:02d}"
    
    def create_preview(self, file_id):
        """Создание превью файла"""
        file_info = self.get_file_by_id(file_id)
        if not file_info:
            return None
        
        file_path = self.get_file_path(file_info['filename'])
        file_ext = os.path.splitext(file_info['filename'])[1].lower()
        
        preview_data = {
            'name': file_info['filename'],
            'type': file_info.get('type', self.get_file_type(file_ext)),
            'icon': file_info.get('icon', self.get_file_icon(file_ext)),
            'content': '',
            'preview_type': 'text'
        }
        
        try:
            if file_ext == '.zip':
                preview_data.update(self._create_zip_preview(file_path))
            elif file_ext == '.7z':
                preview_data.update(self._create_7z_preview(file_path))
            elif file_ext == '.docx':
                preview_data.update(self._create_docx_preview(file_path))
            elif file_ext in ['.txt', '.md', '.py', '.js', '.html', '.css', '.json']:
                preview_data.update(self._create_text_preview(file_path))
            elif file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.svg']:
                preview_data.update(self._create_image_preview(file_path, file_ext))
            elif file_ext == '.pdf':
                preview_data.update(self._create_pdf_preview(file_id))
            else:
                preview_data['content'] = f'Preview for {file_ext} files is not supported.'
                preview_data['preview_type'] = 'unsupported'
                
        except Exception as e:
            preview_data['content'] = f'Error creating preview: {str(e)}'
            preview_data['preview_type'] = 'error'
        
        return preview_data
    
    def _create_zip_preview(self, file_path):
        """Создание превью для ZIP файлов"""
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            file_list = []
            total_size = 0
            for info in zip_ref.infolist():
                file_size = info.file_size
                total_size += file_size
                file_list.append({
                    'name': info.filename,
                    'size': self.format_size(file_size),
                    'date': self.format_date(info.date_time),
                    'is_dir': info.filename.endswith('/')
                })
            
            return {
                'preview_type': 'zip',
                'content': {
                    'files': file_list,
                    'total_files': len(file_list),
                    'total_size': self.format_size(total_size)
                }
            }
    
    def _create_7z_preview(self, file_path):
        """Создание превью для 7Z файлов"""
        try:
            with py7zr.SevenZipFile(file_path, mode='r') as z:
                file_list = []
                total_size = 0
                
                file_infos = z.list()
                
                for file_info in file_infos:
                    filename = file_info.filename
                    is_dir = filename.endswith('/')
                    file_size = file_info.uncompressed if hasattr(file_info, 'uncompressed') else 0
                    total_size += file_size
                    
                    date_info = file_info.creationtime if hasattr(file_info, 'creationtime') else None
                    if date_info:
                        date_str = date_info.strftime('%d.%m.%Y %H:%M')
                    else:
                        date_str = 'Unknown'
                    
                    file_list.append({
                        'name': filename,
                        'size': self.format_size(file_size),
                        'date': date_str,
                        'is_dir': is_dir
                    })
                
                return {
                    'preview_type': 'zip',
                    'content': {
                        'files': file_list,
                        'total_files': len(file_list),
                        'total_size': self.format_size(total_size)
                    }
                }
        except Exception as e:
            return {
                'content': f'Error reading 7z file: {str(e)}',
                'preview_type': 'error'
            }
    
    def _create_docx_preview(self, file_path):
        """Создание превью для DOCX файлов"""
        with open(file_path, 'rb') as docx_file:
            result = mammoth.extract_raw_text(docx_file)
            text = result.value
            
            doc = Document(file_path)
            core_props = doc.core_properties
            
            return {
                'preview_type': 'docx',
                'content': {
                    'text': text[:2000] + ('...' if len(text) > 2000 else ''),
                    'metadata': {
                        'author': core_props.author or 'Unknown',
                        'created': core_props.created.strftime('%Y-%m-%d %H:%M:%S') if core_props.created else 'Unknown',
                        'modified': core_props.modified.strftime('%Y-%m-%d %H:%M:%S') if core_props.modified else 'Unknown',
                        'title': core_props.title or 'No title',
                        'pages': len(doc.paragraphs) // 20 + 1
                    }
                }
            }
    
    def _create_text_preview(self, file_path):
        """Создание превью для текстовых файлов"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read(5000)
                return {
                    'content': content + ('...' if len(content) == 5000 else '')
                }
        except UnicodeDecodeError:
            return {
                'content': 'Unable to display the content of this text file.'
            }
    
    def _create_image_preview(self, file_path, file_ext):
        """Создание превью для изображений"""
        with open(file_path, 'rb') as img_file:
            img_data = base64.b64encode(img_file.read()).decode('utf-8')
            return {
                'preview_type': 'image',
                'content': f'data:image/{file_ext[1:]};base64,{img_data}'
            }
    
    def _create_pdf_preview(self, file_id):
        """Создание превью для PDF файлов"""
        return {
            'preview_type': 'pdf',
            'content': f'/raw/{file_id}'
        }