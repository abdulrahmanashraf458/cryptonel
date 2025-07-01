#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
نظام قراءة أنشطة التعدين
-------------------------
يوفر وظائف للوصول إلى سجلات أنشطة المستخدمين لاستخدامها في نظام اكتشاف البصمات الكاذبة
"""

import logging
import datetime
from pymongo import MongoClient
import os

# إعداد نظام التسجيل
logger = logging.getLogger(__name__)

def get_db_connection():
    """
    الحصول على اتصال بقاعدة البيانات
    
    Returns:
        pymongo.database.Database: كائن قاعدة البيانات أو None في حالة الفشل
    """
    try:
        # استخدام نفس رابط قاعدة البيانات من متغيرات البيئة
        mongodb_uri = os.environ.get('MONGODB_URI')
        if not mongodb_uri:
            logger.error("عنوان قاعدة البيانات غير متوفر")
            return None
            
        # إنشاء اتصال وإرجاع قاعدة البيانات
        client = MongoClient(mongodb_uri)
        db = client.get_default_database()
        return db
    except Exception as e:
        logger.error(f"خطأ في الاتصال بقاعدة البيانات: {str(e)}")
        return None

def get_last_user_activities(user_id, limit=5):
    """
    الحصول على آخر أنشطة المستخدم المسجلة
    
    Args:
        user_id: معرف المستخدم
        limit: الحد الأقصى لعدد الأنشطة المرجعة (الافتراضي = 5)
        
    Returns:
        list: قائمة بآخر الأنشطة، أو قائمة فارغة إذا لم يتم العثور على أنشطة
    """
    try:
        # الحصول على الاتصال بقاعدة البيانات
        client = MongoClient(os.environ.get('DATABASE_URL'))
        mining_db = client["cryptonel_mining"]
        activities_collection = mining_db["mining_activities"]
        
        # البحث عن سجل أنشطة المستخدم
        user_activities = activities_collection.find_one({"user_id": user_id})
        
        if not user_activities or "activities" not in user_activities:
            return []
            
        # استخراج آخر الأنشطة وترتيبها بالأحدث أولًا
        activities = user_activities.get("activities", [])
        sorted_activities = sorted(
            activities,
            key=lambda x: x.get("timestamp", datetime.datetime.min),
            reverse=True
        )
        
        # إرجاع حتى الحد المطلوب من الأنشطة
        return sorted_activities[:limit]
        
    except Exception as e:
        logger.error(f"خطأ في الحصول على أنشطة المستخدم {user_id}: {e}")
        return []

def get_latest_device_types(user_id):
    """
    الحصول على أنواع الأجهزة التي استخدمها المستخدم مؤخرًا
    
    Args:
        user_id: معرف المستخدم
        
    Returns:
        list: قائمة بأنواع الأجهزة الفريدة
    """
    try:
        # الحصول على آخر 10 أنشطة
        activities = get_last_user_activities(user_id, 10)
        
        # استخراج أنواع الأجهزة الفريدة
        device_types = set()
        for activity in activities:
            if "device_type" in activity and activity["device_type"]:
                device_types.add(activity["device_type"])
                
        return list(device_types)
    except Exception as e:
        logger.error(f"خطأ في الحصول على أنواع أجهزة المستخدم {user_id}: {str(e)}")
        return []

def get_user_ip_history(user_id, limit=10):
    """
    الحصول على تاريخ عناوين IP التي استخدمها المستخدم
    
    Args:
        user_id: معرف المستخدم
        limit: الحد الأقصى لعدد العناوين المسترجعة
        
    Returns:
        list: قائمة بعناوين IP الفريدة مع أوقات استخدامها
    """
    try:
        # الحصول على الأنشطة
        activities = get_last_user_activities(user_id, limit * 2)  # نحصل على عدد أكبر لضمان الحصول على عناوين مختلفة
        
        # تجميع العناوين مع أوقات استخدامها
        ip_history = {}
        for activity in activities:
            ip = activity.get("ip_address")
            timestamp = activity.get("timestamp")
            
            if ip and timestamp:
                if ip not in ip_history:
                    ip_history[ip] = timestamp
        
        # تحويل إلى قائمة مرتبة حسب الوقت
        ip_list = [{"ip": ip, "timestamp": time} for ip, time in ip_history.items()]
        sorted_list = sorted(ip_list, key=lambda x: x["timestamp"], reverse=True)
        
        return sorted_list[:limit]
    except Exception as e:
        logger.error(f"خطأ في الحصول على تاريخ عناوين IP للمستخدم {user_id}: {str(e)}")
        return [] 