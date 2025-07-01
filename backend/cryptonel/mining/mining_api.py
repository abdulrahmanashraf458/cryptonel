from flask import Blueprint, request, jsonify, session
from .utils import get_db_connection, get_user_id
from .security import process_security_check
from .mining_security import check_security_before_mining, is_blocked_from_mining, get_first_miner_by_device_fingerprint, get_advanced_fingerprint
from .utils import recalculate_device_fingerprints, reset_user_device_fingerprint
import logging
import threading
import datetime

logger = logging.getLogger("mining_api")

mining_api = Blueprint('mining_api', __name__)

@mining_api.route('/check', methods=['POST'])
def check_mining():
    """
    التحقق من إمكانية التعدين للمستخدم
    يتضمن فحص الأمان المحسن
    """
    user_id = get_user_id()
    if not user_id:
        return jsonify({"status": "error", "message": "User not authenticated"}), 401
    
    # الحصول على بيانات البصمة
    data = request.get_json()
    fingerprint_data = data.get('fingerprint_data', {})
    
    # استخدام الفحص الأمني المحسن للحصول على بصمة الجهاز
    device_data = get_advanced_fingerprint(user_id, request)
    device_fingerprint = device_data.get("device_fingerprint")
    ip_address = device_data.get("ip_address")
    
    # التحقق مما إذا كانت بصمة الجهاز مستخدمة بواسطة حساب آخر
    first_user = get_first_miner_by_device_fingerprint(device_fingerprint, ip_address)
    
    if first_user and first_user != user_id:
        # هذا الجهاز مستخدم بالفعل بواسطة حساب آخر
        logger.warning(f"Device reuse detected: User {user_id} tried to mine with device {device_fingerprint[:8]}... already used by {first_user}")
        
        # تحديث قاعدة البيانات لمنع المستخدم من التعدين
        db = get_db_connection()
        db.users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "mining_block": True,
                    "mining_block_reason": f"Device reuse detected. Original user: {first_user}",
                    "mining_block_timestamp": datetime.datetime.now(datetime.timezone.utc),
                    "mining_block_level": "high"
                }
            },
            upsert=True
        )
        
        # توثيق الانتهاك
        db.mining_violations.insert_one({
            "user_id": user_id,
            "violation_type": "device_reuse",
            "device_fingerprint": device_fingerprint,
            "ip_address": ip_address,
            "original_user": first_user,
            "timestamp": datetime.datetime.now(datetime.timezone.utc),
            "blocked": True,
            "block_reason": f"Device reuse detected. Original user: {first_user}"
        })
        
        return jsonify({
            "status": "security_violation",
            "message": "هذا الجهاز مسجل بالفعل لحساب آخر. يسمح فقط للحساب الأول الذي استخدم هذا الجهاز بالتعدين.",
            "can_mine": False
        }), 403
    
    # استخدام الفحص الأمني المحسن
    security_check = process_security_check(fingerprint_data)
    
    if security_check["status"] != "ok":
        return jsonify(security_check), 403
    
    # استمر في فحص ظروف التعدين الأخرى...
    # ...
    
    return jsonify({
        "status": "ok",
        "can_mine": True,
        "message": "Mining allowed"
    })

@mining_api.route('/status', methods=['GET'])
def mining_status():
    """الحصول على حالة التعدين للمستخدم"""
    user_id = get_user_id()
    if not user_id:
        return jsonify({"status": "error", "message": "User not authenticated"}), 401
    
    db = get_db_connection()
    user_status = db.user_mining_status.find_one({"user_id": user_id})
    
    if not user_status:
        # إذا لم يتم العثور على حالة، قم بإنشاء حالة افتراضية
        return jsonify({
            "total_mined": "0.00000000",
            "can_mine": True,
            "hours_remaining": 0,
            "wallet_balance": "0.00000000",
            "mining_session_hours": 1,
            "mining_conditions": "normal"
        })
    
    # إعادة حالة التعدين
    return jsonify({
        "total_mined": user_status.get("total_mined", "0.00000000"),
        "last_mined": user_status.get("last_mined"),
        "today_mined": user_status.get("today_mined", 0),
        "daily_mining_rate": user_status.get("daily_mining_rate", 1),
        "hourly_mining_rate": user_status.get("hourly_mining_rate", 0.5),
        "can_mine": user_status.get("can_mine", True),
        "hours_remaining": user_status.get("hours_remaining", 0),
        "wallet_balance": user_status.get("wallet_balance", "0.00000000"),
        "mining_session_hours": user_status.get("mining_session_hours", 1),
        "boosted_mining": user_status.get("boosted_mining", False),
        "mining_conditions": user_status.get("mining_conditions", "normal"),
        "security_violation": user_status.get("security_violation", False),
        "mining_block": user_status.get("mining_block", False)
    })

@mining_api.route('/check-security', methods=['GET'])
def check_mining_security():
    """Check mining security for the current user"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    # Check if user is blocked from mining
    is_blocked = is_blocked_from_mining(user_id)
    if is_blocked:
        # Get user info to determine block reason
        db = get_db_connection()
        user_info = db.users.find_one({"user_id": user_id})
        block_reason = user_info.get("mining_block_reason", "Security violation detected")
        
        return jsonify({"allowed": False, "reason": block_reason})
    
    # Check all security rules
    violation, violation_details = check_security_before_mining(user_id)
    if violation:
        return jsonify({
            "allowed": False,
            "reason": violation_details.get("reason", "Security policy violation"),
            "details": violation_details
        })
    
    return jsonify({
        "allowed": True,
        "user_id": user_id
    })

@mining_api.route('/recalculate-fingerprints', methods=['POST'])
def recalculate_fingerprints_api():
    """
    إعادة حساب بصمات الأجهزة لجميع المستخدمين
    هذه العملية ثقيلة وتستغرق وقتًا طويلاً، لذلك تعمل في الخلفية
    """
    try:
        # التحقق من أن المستخدم مسؤول
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401
        
        # Check if user is admin
        from pymongo import MongoClient
        import os
        from dotenv import load_dotenv
        
        # Load environment variables
        load_dotenv()
        
        # MongoDB connection
        DATABASE_URL = os.getenv("DATABASE_URL")
        client = MongoClient(DATABASE_URL)
        
        # Get user from database
        user = client["cryptonel_wallet"]["users"].find_one({"user_id": user_id})
        if not user or not user.get("is_admin", False):
            return jsonify({"error": "Unauthorized access"}), 403
        
        # Start recalculation in a background thread
        thread = threading.Thread(target=recalculate_device_fingerprints)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "success": True,
            "message": "Fingerprint recalculation started in the background"
        })
    except Exception as e:
        logger.error(f"Error starting fingerprint recalculation: {e}")
        return jsonify({"error": "System error", "details": str(e)}), 500

@mining_api.route('/reset-device-fingerprint/<user_id>', methods=['POST'])
def reset_fingerprint_api(user_id):
    """
    إعادة تعيين بصمة جهاز مستخدم محدد
    تُستخدم لحل مشكلة التشابه الخاطئ بين بصمات الأجهزة
    """
    try:
        # التحقق من أن المستخدم مسؤول
        requester_id = session.get('user_id')
        if not requester_id:
            return jsonify({"error": "Not authenticated"}), 401
            
        # استدعاء خدمة إعادة تعيين البصمة
        result = reset_user_device_fingerprint(user_id)
        
        if result.get("success", False):
            return jsonify({
                "success": True,
                "message": result.get("message", "Device fingerprint reset successfully")
            })
        else:
            return jsonify({
                "success": False,
                "message": result.get("message", "Error resetting device fingerprint")
            }), 400
    except Exception as e:
        logger.error(f"Error in reset-fingerprint API: {e}")
        return jsonify({"error": "System error", "details": str(e)}), 500 