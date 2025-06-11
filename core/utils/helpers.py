import psutil
import platform

def get_server_uptime():
    """Получение времени работы сервера"""
    if platform.system() == "Windows":
        from ctypes import windll
        seconds = windll.kernel32.GetTickCount64() / 1000
    else:
        with open('/proc/uptime', 'r') as f:
            seconds = float(f.readline().split()[0])
    
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if days > 0:
        return f"{int(days)}д {int(hours)}ч {int(minutes)}м"
    elif hours > 0:
        return f"{int(hours)}ч {int(minutes)}м"
    else:
        return f"{int(minutes)}м {int(seconds)}с"

def get_cpu_usage():
    """Получение загрузки процессора"""
    return int(psutil.cpu_percent(interval=1))

def get_memory_usage():
    """Получение использования памяти"""
    return int(psutil.virtual_memory().percent)

def get_disk_usage():
    """Получение использования диска"""
    return int(psutil.disk_usage('/').percent)