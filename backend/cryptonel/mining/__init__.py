"""
Mining module for Cryptonel with enhanced security
"""

import os
from flask import Blueprint

# تعريف المتغيرات التي سيتم تعيينها لاحقاً
mining_bp = None
init_mining = None

# تجنب الاستيراد الدائري هنا - سيتم استيراد mining_bp من mining.py عند تهيئة الوحدة

# استيراد الوحدات
from .mining_api import mining_api

def init_app(app):
    """
    تهيئة تطبيق التعدين وتسجيل نقاط النهاية
    """
    # تسجيل البلوبرنت
    app.register_blueprint(mining_api, url_prefix='/api/mining')
    
    # تهيئة نظام التعدين الأساسي
    # استيراد mining هنا لتجنب الاستيراد الدائري
    from backend.cryptonel.mining.mining import mining_bp as bp, init_app as init_mining
    global mining_bp
    mining_bp = bp
    init_mining(app)
    
    # تهيئة نظام البصمة المتقدم
    try:
        from backend.cryptonel.mining.fingerprint import init_fingerprint
        init_fingerprint(app)
    except ImportError as e:
        print(f"Warning: Could not initialize advanced fingerprinting module: {e}")
    
    return app 