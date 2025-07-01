"""
Startup Utilities
----------------
وحدة المساعدة لإعداد البيئة والتكوينات تلقائيًا عند بدء تشغيل النظام
"""

import os
import sys
import logging
import traceback
import time
from . import env_loader

logger = logging.getLogger('cryptonel.startup')

def ensure_secure_environment():
    """
    ضمان وجود بيئة آمنة وإعدادها بشكل صحيح
    - إنشاء المجلدات الآمنة
    - نقل الملفات البيئية
    - ضبط الأذونات
    
    Returns:
        bool: نجاح العملية
    """
    try:
        # إنشاء مجلد آمن
        secure_dir = env_loader.ensure_secure_directory()
        if not secure_dir:
            logger.error("Failed to create secure directory")
            return False
        
        # نقل الملفات البيئية المعروفة
        env_files = ['clyne.env', 'ip.env', '.env']
        migrated_files = []
        
        for env_file in env_files:
            # يتحقق إذا تم نقل الملف بنجاح ويضيفه إلى القائمة
            if env_loader.migrate_env_file(env_file):
                migrated_files.append(env_file)
        
        # تحميل الملفات بعد نقلها
        if migrated_files:
            logger.info(f"Successfully migrated environment files: {', '.join(migrated_files)}")
            # إعادة تحميل الملفات بعد النقل
            env_loader.reload_env_files()
        
        return True
        
    except Exception as e:
        logger.error(f"Error ensuring secure environment: {e}")
        logger.error(traceback.format_exc())
        return False

def cleanup_legacy_files(delay_days=7):
    """
    تنظيف الملفات القديمة بعد فترة من الزمن
    ينتظر فترة محددة بعد النقل قبل الحذف للتأكد من عمل النظام جيدًا
    
    Args:
        delay_days: عدد الأيام للانتظار قبل الحذف
    
    Returns:
        bool: نجاح العملية
    """
    try:
        env_files = ['clyne.env', 'ip.env', '.env']
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        for env_file in env_files:
            legacy_path = os.path.join(project_root, env_file)
            secure_path = os.path.join(os.path.dirname(project_root), 'secure_config', env_file)
            
            # إذا كان الملف موجودًا في كلا الموقعين
            if os.path.exists(legacy_path) and os.path.exists(secure_path):
                # افحص وقت التعديل لمعرفة متى تم نسخه
                secure_mtime = os.path.getmtime(secure_path)
                current_time = time.time()
                days_since_copy = (current_time - secure_mtime) / (60 * 60 * 24)
                
                # إذا مر وقت كافٍ، قم بحذف الملف القديم
                if days_since_copy >= delay_days:
                    try:
                        # قم بتغيير امتداد الملف فقط بدلاً من حذفه (للسلامة)
                        backup_path = legacy_path + ".old"
                        if os.path.exists(backup_path):
                            os.remove(backup_path)  # إزالة النسخة القديمة إذا كانت موجودة
                        
                        os.rename(legacy_path, backup_path)
                        logger.info(f"Renamed legacy file {env_file} to {env_file}.old after {days_since_copy:.1f} days")
                    except Exception as e:
                        logger.error(f"Error cleaning up legacy file {env_file}: {e}")
        
        return True
    except Exception as e:
        logger.error(f"Error in cleanup process: {e}")
        return False

def setup_secure_environment():
    """
    إعداد البيئة الآمنة وتنظيفها عند بدء التشغيل
    
    Returns:
        bool: نجاح العملية
    """
    # ضمان وجود البيئة الآمنة أولاً
    success = ensure_secure_environment()
    if not success:
        logger.warning("Secure environment setup had issues - check logs for details")
    
    # تنظيف الملفات القديمة إذا مر وقت كافٍ
    cleanup_success = cleanup_legacy_files()
    if not cleanup_success:
        logger.warning("Legacy file cleanup had issues - check logs for details")
    
    return success 