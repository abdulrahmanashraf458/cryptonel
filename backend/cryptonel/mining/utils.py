from flask import request, session
from pymongo import MongoClient
import os
import logging
import datetime
from bson import ObjectId
from dotenv import load_dotenv
import hashlib
import random

# Load environment variables
load_dotenv()

# MongoDB connection
DATABASE_URL = os.getenv("DATABASE_URL")
client = MongoClient(DATABASE_URL)

# Database references
mining_db = client["cryptonel_mining"]
wallet_db = client["cryptonel_wallet"]

# Collections
mining_blocks = mining_db["mining_blocks"]
mining_violations = mining_db["mining_violations"]

logger = logging.getLogger("mining_utils")

def get_db_connection():
    """
    الحصول على اتصال بقاعدة البيانات
    """
    mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017/cryptonel")
    client = MongoClient(mongo_uri)
    db_name = mongo_uri.split("/")[-1]
    return client[db_name]

def get_user_id():
    """
    الحصول على معرف المستخدم الحالي من الجلسة
    """
    return session.get("user_id") or request.headers.get("X-User-ID")

def get_real_ip():
    """
    الحصول على عنوان IP الحقيقي للمستخدم
    """
    # محاولة الحصول على IP من الهيدرز
    if request.headers.get('X-Forwarded-For'):
        ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        ip = request.headers.get('X-Real-IP')
    else:
        # استخدام IP من الطلب المباشر
        ip = request.remote_addr
    
    return ip

def get_user_last_activity(user_id):
    """
    الحصول على آخر نشاط للمستخدم
    """
    db = get_db_connection()
    user_data = db.mining_activities.find_one({"user_id": user_id})
    
    if not user_data or "last_activity" not in user_data:
        return None
    
    return user_data["last_activity"]

def get_user_last_ip(user_id):
    """
    الحصول على آخر عنوان IP للمستخدم
    """
    last_activity = get_user_last_activity(user_id)
    
    if not last_activity:
        return None
    
    return last_activity.get("ip_address")

def get_users_with_device(device_fingerprint, exclude_user_id=None):
    """
    الحصول على قائمة المستخدمين الذين لديهم نفس بصمة الجهاز
    """
    db = get_db_connection()
    
    query = {"activities.device_fingerprint": device_fingerprint}
    
    if exclude_user_id:
        query["user_id"] = {"$ne": exclude_user_id}
    
    users = db.mining_activities.find(query, {"user_id": 1})
    
    return [user["user_id"] for user in users]

def recalculate_device_fingerprints():
    """
    إعادة حساب بصمات الأجهزة لكل المستخدمين
    تُستخدم هذه الدالة بعد تحديث خوارزمية توليد البصمات
    
    تتطلب هذه العملية وقتًا طويلاً، لذا يفضل تنفيذها كعملية في الخلفية
    """
    try:
        # نحصل على جميع سجلات المستخدمين
        all_users = list(mining_blocks.find({}))
        
        # عدّاد للمتابعة
        processed = 0
        errors = 0
        updated = 0
        
        # سجل بداية العملية
        logger.info(f"Starting device fingerprints recalculation for {len(all_users)} users")
        
        # معالجة كل مستخدم
        for user in all_users:
            try:
                user_id = user.get("user_id")
                
                # قائمة بالأنشطة المحدثة
                updated_activities = []
                
                # معالجة كل نشاط للمستخدم
                if "activities" in user:
                    for activity in user.get("activities", []):
                        # نحتفظ بمعلومات النشاط الأصلية
                        activity_copy = activity.copy()
                        
                        # إضافة النشاط المحدث إلى القائمة
                        updated_activities.append(activity_copy)
                
                # تحديث سجل المستخدم بالأنشطة المحدثة
                if updated_activities:
                    # تحديث آخر نشاط أيضًا
                    last_activity = updated_activities[-1]
                    
                    # تحديث قاعدة البيانات
                    mining_blocks.update_one(
                        {"user_id": user_id},
                        {
                            "$set": {
                                "activities": updated_activities,
                                "last_activity": last_activity,
                                "last_updated": datetime.datetime.now(datetime.timezone.utc)
                            }
                        }
                    )
                    updated += 1
                
                processed += 1
                
                # طباعة تحديث كل 100 مستخدم
                if processed % 100 == 0:
                    logger.info(f"Processed {processed}/{len(all_users)} users, {updated} updated, {errors} errors")
                
            except Exception as e:
                errors += 1
                logger.error(f"Error updating user {user.get('user_id')}: {e}")
        
        # سجل نهاية العملية
        logger.info(f"Device fingerprints recalculation completed: {processed} processed, {updated} updated, {errors} errors")
        
        return {
            "processed": processed,
            "updated": updated,
            "errors": errors
        }
    except Exception as e:
        logger.error(f"Error in recalculate_device_fingerprints: {e}")
        return {
            "error": str(e)
        }

def reset_user_device_fingerprint(user_id):
    """
    إعادة تعيين بصمة جهاز مستخدم محدد
    تستخدم عندما يتم تصنيف المستخدم بشكل خاطئ على أنه يستخدم جهازًا مسجلاً لمستخدم آخر
    """
    try:
        # 1. إنشاء بصمة جديدة فريدة
        current_time = datetime.datetime.now().timestamp()
        random_suffix = str(random.randint(100000, 999999))
        unique_seed = f"{user_id}_{current_time}_{random_suffix}_forced_reset"
        new_fingerprint = hashlib.sha256(unique_seed.encode('utf-8')).hexdigest()[:32]
        
        # 2. تحديث بصمة الجهاز في سجلات المستخدم
        user_record = mining_blocks.find_one({"user_id": user_id})
        if user_record and "activities" in user_record:
            activities = user_record["activities"]
            for activity in activities:
                activity["device_fingerprint"] = new_fingerprint
                
            if "last_activity" in user_record:
                last_activity = user_record["last_activity"]
                last_activity["device_fingerprint"] = new_fingerprint
                
                # تحديث قاعدة البيانات
                result = mining_blocks.update_one(
                    {"user_id": user_id},
                    {
                        "$set": {
                            "activities": activities,
                            "last_activity": last_activity,
                            "last_updated": datetime.datetime.now(datetime.timezone.utc)
                        }
                    }
                )
                
                if result.modified_count > 0:
                    logger.info(f"Successfully reset device fingerprint for user {user_id}")
                    
                    # 3. حذف سجلات المخالفات المتعلقة ببصمة الجهاز
                    violations_result = mining_violations.delete_many({"user_id": user_id})
                    logger.info(f"Deleted {violations_result.deleted_count} violation records for user {user_id}")
                    
                    # 4. إلغاء الحظر في جدول المستخدمين
                    unblock_result = wallet_db["users"].update_one(
                        {"user_id": user_id},
                        {
                            "$set": {
                                "mining_block": False,
                                "mining_block_reason": None,
                                "mining_unblocked_at": datetime.datetime.now(datetime.timezone.utc),
                                "mining_unblock_reason": "Device fingerprint reset"
                            }
                        }
                    )
                    
                    logger.info(f"User {user_id} mining block status updated: {unblock_result.modified_count} records modified")
                    
                    return {
                        "success": True,
                        "message": f"Device fingerprint reset for user {user_id}",
                        "new_fingerprint": new_fingerprint
                    }
                else:
                    logger.warning(f"No records updated for user {user_id}")
                    return {
                        "success": False,
                        "message": f"No records updated for user {user_id}"
                    }
        else:
            logger.warning(f"No user record found for user {user_id}")
            return {
                "success": False,
                "message": f"No user record found for user {user_id}"
            }
    except Exception as e:
        logger.error(f"Error resetting device fingerprint for user {user_id}: {e}")
        return {
            "success": False,
            "message": f"Error: {e}"
        } 