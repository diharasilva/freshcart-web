import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-this-secret")
    MYSQL_HOST = os.getenv("MYSQL_HOST", "mysql-11076237-kalanidihara-c497.l.aivencloud.com")
    MYSQL_USER = os.getenv("MYSQL_USER", "avnadmin")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
    MYSQL_DB = os.getenv("MYSQL_DB", "dealz_super_db")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", 24414))
    MYSQL_CURSORCLASS = "DictCursor"
    
    # Add this line to handle Aiven SSL connection requirements:
    MYSQL_CUSTOM_OPTIONS = {'ssl': {'check_hostname': False}}

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True
    WTF_CSRF_TIME_LIMIT = 3600
    STORE_LATITUDE = float(os.getenv("STORE_LATITUDE", "6.8480"))
    STORE_LONGITUDE = float(os.getenv("STORE_LONGITUDE", "79.9265"))
    STORE_RADIUS_KM = float(os.getenv("STORE_RADIUS_KM", "2.0"))
