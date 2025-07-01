"""
Environment Variables Loader
---------------------------
وحدة آمنة لتحميل المتغيرات البيئية من مسار آمن خارج مجلد التطبيق
تقوم تلقائيًا بإنشاء وإعداد المجلد الآمن ونقل الملفات إليه
"""

import os
import logging
import shutil
import stat
from dotenv import load_dotenv

# إعداد السجلات
logger = logging.getLogger('cryptonel.env_loader')

def ensure_secure_directory():
    """
    إنشاء مجلد آمن للملفات البيئية إذا لم يكن موجودًا
    
    Returns:
        str: مسار المجلد الآمن
    """
    # مسار المجلد الآمن خارج مجلد التطبيق
    secure_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'secure_config')
    
    # تحقق من وجود المجلد
    if not os.path.exists(secure_dir):
        try:
            # إنشاء المجلد إذا لم يكن موجودًا
            os.makedirs(secure_dir, exist_ok=True)
            logger.info(f"Created secure directory: {secure_dir}")
            
            # ضبط أذونات المجلد (700 = rwx------)
            # ملاحظة: هذا سيعمل على Linux/Mac فقط
            try:
                os.chmod(secure_dir, stat.S_IRWXU)
                logger.info(f"Set secure permissions on directory: {secure_dir}")
            except Exception as e:
                logger.warning(f"Could not set permissions on directory: {e}")
        except Exception as e:
            logger.error(f"Failed to create secure directory: {e}")
            return None
    
    return secure_dir

def migrate_env_file(filename):
    """
    نقل ملف البيئة من المسار القديم إلى المسار الآمن إذا كان موجودًا فقط في المسار القديم
    
    Args:
        filename: اسم الملف (بدون المسار)
        
    Returns:
        bool: نجاح النقل
    """
    # المسار الآمن
    secure_dir = ensure_secure_directory()
    if not secure_dir:
        return False
        
    secure_path = os.path.join(secure_dir, filename)
    
    # المسار القديم
    legacy_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), filename)
    
    # إذا كان الملف موجودًا في المسار القديم وغير موجود في المسار الآمن، فقم بنقله
    if os.path.exists(legacy_path) and not os.path.exists(secure_path):
        try:
            # نسخ الملف (وليس نقله مباشرةً) للاحتفاظ بنسخة احتياطية
            shutil.copy2(legacy_path, secure_path)
            logger.info(f"Migrated {filename} to secure location")
            
            # ضبط أذونات الملف (600 = rw-------)
            try:
                os.chmod(secure_path, stat.S_IRUSR | stat.S_IWUSR)
                logger.info(f"Set secure permissions on {filename}")
            except Exception as e:
                logger.warning(f"Could not set permissions on {filename}: {e}")
                
            return True
        except Exception as e:
            logger.error(f"Failed to migrate {filename}: {e}")
            return False
    
    # إذا كان الملف موجودًا بالفعل في المسار الآمن
    elif os.path.exists(secure_path):
        # ضبط أذونات الملف للتأكد من أنها آمنة
        try:
            os.chmod(secure_path, stat.S_IRUSR | stat.S_IWUSR)
        except Exception:
            pass
        return True
        
    return False

def load_secure_env_file(filename):
    """
    تحميل ملف متغيرات بيئية من المسار الآمن، ونقله تلقائيًا إذا كان في المسار القديم
    
    Args:
        filename: اسم الملف (بدون المسار)
    
    Returns:
        bool: نجاح التحميل
    """
    # محاولة نقل الملف من المسار القديم إلى المسار الآمن إذا كان ضروريًا
    migrate_env_file(filename)
    
    # المسار الآمن
    secure_dir = ensure_secure_directory()
    if not secure_dir:
        return False
    
    secure_path = os.path.join(secure_dir, filename)
    
    # المسار القديم للتوافق مع الإصدارات السابقة
    legacy_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), filename)
    
    # محاولة التحميل من المسار الآمن أولاً
    if os.path.exists(secure_path):
        # استخدام ترميز UTF-8 عند تحميل الملف
        try:
            # تمرير معلمة encoding للتحكم في ترميز الملف
            load_dotenv(secure_path, encoding='utf-8')
            logger.info(f"Loaded environment variables from secure path: {filename}")
            return True
        except UnicodeDecodeError:
            # محاولة استخدام ترميز آخر إذا فشل UTF-8
            try:
                load_dotenv(secure_path, encoding='cp1256')  # ترميز عربي شائع
                logger.info(f"Loaded environment variables using alternate encoding from secure path: {filename}")
                return True
            except Exception as e:
                logger.error(f"Failed to load environment file with alternate encoding: {e}")
                return False
    
    # محاولة التحميل من المسار القديم إذا لم يوجد في المسار الآمن
    if os.path.exists(legacy_path):
        try:
            load_dotenv(legacy_path, encoding='utf-8')
            logger.warning(f"Using legacy path for environment file: {filename}. Please move to secure location.")
            return True
        except UnicodeDecodeError:
            # محاولة استخدام ترميز آخر إذا فشل UTF-8
            try:
                load_dotenv(legacy_path, encoding='cp1256')  # ترميز عربي شائع
                logger.warning(f"Using legacy path with alternate encoding for environment file: {filename}. Please move to secure location.")
                return True
            except Exception as e:
                logger.error(f"Failed to load legacy environment file with alternate encoding: {e}")
                return False
    
    logger.error(f"Environment file not found: {filename}")
    return False

# دالة تعيد تحميل ملفات البيئة (يمكن استدعاؤها من أي مكان في الكود)
def reload_env_files():
    """
    إعادة تحميل جميع ملفات البيئة المعروفة
    """
    env_files = ['clyne.env', 'ip.env', '.env']
    loaded_files = []
    
    for env_file in env_files:
        if load_secure_env_file(env_file):
            loaded_files.append(env_file)
            
    logger.info(f"Reloaded environment files: {', '.join(loaded_files)}")
    return loaded_files

# تحميل الملفات الأساسية عند استيراد الوحدة
load_secure_env_file('clyne.env')
load_secure_env_file('ip.env') 