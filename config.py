import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-this-secret")
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = 'xtdq7001#'  
    MYSQL_DB = 'dealz_super_db'
    MYSQL_CURSORCLASS = "DictCursor"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True
    WTF_CSRF_TIME_LIMIT = 3600
    STORE_LATITUDE = float(os.getenv("STORE_LATITUDE", "6.8480"))
    STORE_LONGITUDE = float(os.getenv("STORE_LONGITUDE", "79.9265"))
    STORE_RADIUS_KM = float(os.getenv("STORE_RADIUS_KM", "2.0"))