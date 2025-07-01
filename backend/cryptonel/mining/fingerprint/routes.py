"""
API routes for advanced fingerprinting system
"""

import logging
from flask import Blueprint, request, jsonify, session
import datetime
from backend.cryptonel.mining.mining_security import get_real_ip, get_ipinfo_data
import requests
import traceback
from flask_cors import cross_origin
import time
import re

# Import core fingerprinting modules
from .advanced_fingerprinting import get_advanced_device_fingerprint, calculate_fingerprint_similarity
from .anti_spoofing import detect_spoofing
from .fingerprint_storage import (
    store_fingerprint, get_stored_fingerprints, get_fingerprint_history,
    remove_fingerprint, check_device_limit, mark_fingerprint_trusted,
    get_user_devices, get_user_device_count, mining_db, update_fingerprint_history
)

# Configure logging
logger = logging.getLogger("fingerprint_routes")

# Create blueprint for routes
fingerprint_routes = Blueprint('fingerprint', __name__)

# Helper function to check user authentication
def check_mining_security():
    """
    Simple helper to check if user is authenticated
    Uses Flask's session to get user_id
    
    Returns:
        str: User ID if authenticated, None otherwise
    """
    return session.get('user_id')

def init_fingerprint_routes(parent_blueprint):
    """Initialize fingerprint routes as sub-routes of the parent blueprint"""
    # Mount fingerprint routes under the parent blueprint (typically mining_bp)
    parent_blueprint.register_blueprint(fingerprint_routes, url_prefix='/fingerprint')
    logger.info("Fingerprint routes initialized")

@fingerprint_routes.route('/collect', methods=['POST'])
def collect_fingerprint():
    """
    Collect device fingerprint from client
    
    This endpoint receives fingerprint data from the client's browser and
    stores it in the database for device tracking and security verification.
    """
    # Get user_id from session
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401
    
    # Get fingerprint data
    data = request.get_json() or {}
    
    # Use advanced fingerprinting module to generate fingerprint
    fingerprint_data = get_advanced_device_fingerprint(request)
    
    # Merge any additional data from request
    if data.get('fingerprint_data'):
        fingerprint_data.update(data.get('fingerprint_data'))
    
    # Check for spoofing attempts
    spoofing_check = detect_spoofing(fingerprint_data, fingerprint_data.get('ip_address'))
    fingerprint_data['spoofing_detected'] = spoofing_check.get('spoofing_detected', False)
    fingerprint_data['spoofing_checks'] = spoofing_check.get('checks', {})
    
    # Add additional checks for spoofing
    if spoofing_check.get('spoofing_detected'):
        logger.warning(f"Spoofing detected for user {user_id} with IP {fingerprint_data.get('ip_address')}")
        fingerprint_data['spoofing_score'] = spoofing_check.get('spoofing_score', 0)
    
    # Store fingerprint
    success, result = store_fingerprint(user_id, fingerprint_data)
    
    # Check device limits
    limit_reached, device_count = check_device_limit(user_id)
    
    # Prepare response
    if success:
        return jsonify({
            'status': 'success',
            'fingerprint_hash': result.get('fingerprint_hash'),
            'is_new_device': result.get('is_new', False),
            'device_count': device_count,
            'device_limit_reached': limit_reached,
            'device_type': fingerprint_data.get('device_type', 'unknown'),
            'spoofing_detected': fingerprint_data.get('spoofing_detected', False)
        })
    else:
        return jsonify({
            'status': 'error',
            'message': result if isinstance(result, str) else 'Error storing fingerprint',
            'device_count': device_count,
            'device_limit_reached': limit_reached
        }), 400

@fingerprint_routes.route('/verify', methods=['POST'])
def verify_fingerprint():
    """
    Verify a user's fingerprint against stored fingerprints
    
    Enhanced with tamper detection and improved security checks
    """
    try:
        # Get user authentication
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401
        
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Extract fingerprint data
        fingerprint_hash = data.get('fingerprint_hash')
        browser_fingerprint = data.get('browser_fingerprint')
        canvas_fingerprint = data.get('canvas_fingerprint')
        webgl_fingerprint = data.get('webgl_fingerprint')
        timing_fingerprint = data.get('timing_fingerprint')  # NEW: Get timing fingerprint
        
        # NEW: Check for tamper detection
        code_tampered = data.get('code_tampered', False)
        verification_token = data.get('verification_token')
        verification_timestamp = data.get('verification_timestamp')
        
        # Require at least one fingerprint type
        if not any([fingerprint_hash, browser_fingerprint, canvas_fingerprint, webgl_fingerprint]):
            return jsonify({"error": "No fingerprint data provided"}), 400
        
        # NEW: Check verification token if provided
        if verification_token and verification_timestamp:
            # Verify token is recent (within last 5 minutes)
            current_time = int(time.time() * 1000)
            if abs(current_time - verification_timestamp) > 300000:  # 5 minutes
                logger.warning(f"Outdated verification token from user {user_id}")
                return jsonify({
                    "status": "error",
                    "message": "Verification token expired",
                    "action": "refresh"
                }), 401
            
            # Verify token matches expected format (this is a basic check)
            user_agent = request.headers.get('User-Agent', '')
            if not re.match(r'^[0-9a-f]{64}$', verification_token):
                logger.warning(f"Invalid verification token format from user {user_id}")
                return jsonify({
                    "status": "error", 
                    "message": "Invalid verification token",
                    "action": "refresh"
                }), 401
        
        # NEW: Check for code tampering
        if code_tampered:
            logger.warning(f"Fingerprinting code tampering detected for user {user_id}")
            # Record tampering attempt
            record_security_event(user_id, "fingerprint_tampering", {
                "details": "Client reported fingerprinting code tampering",
                "user_agent": request.headers.get('User-Agent', ''),
                "ip_address": get_real_ip()
            })
            
            # We don't return an error immediately to prevent attackers from knowing
            # that we detected their tampering, but we record it and may take action later
        
        # Get stored fingerprints for this user
        stored_fingerprints = get_stored_fingerprints(user_id)
        if not stored_fingerprints:
            # No stored fingerprints, this is first time or fingerprints were cleared
            store_result, message = store_fingerprint(user_id, data)
            if store_result:
                return jsonify({
                    "status": "new_device",
                    "message": "New device registered successfully",
                    "device_count": get_user_device_count(user_id)
                })
            else:
                return jsonify({"error": message}), 400
        
        # Match fingerprint against stored fingerprints
        best_match = None
        best_score = 0
        
        for stored_fp in stored_fingerprints:
            # Calculate similarity score with multiple fingerprint components
            component_scores = []
            
            # Compare fingerprint hash if available
            if fingerprint_hash and stored_fp.get('fingerprint_hash'):
                if fingerprint_hash == stored_fp['fingerprint_hash']:
                    component_scores.append(1.0)  # Exact match
                else:
                    # Use fuzzy matching for the hash
                    hash_similarity = calculate_fuzzy_similarity(fingerprint_hash, stored_fp['fingerprint_hash'])
                    component_scores.append(hash_similarity)
            
            # Compare browser fingerprint
            if browser_fingerprint and stored_fp.get('browser_fingerprint'):
                if browser_fingerprint == stored_fp['browser_fingerprint']:
                    component_scores.append(1.0)  # Exact browser match is strong evidence
                else:
                    component_scores.append(0.0)  # Different browser is strong evidence against
            
            # Compare canvas fingerprint
            if canvas_fingerprint and stored_fp.get('canvas_fingerprint'):
                if canvas_fingerprint == stored_fp['canvas_fingerprint']:
                    component_scores.append(1.0)
                else:
                    # Canvas should be fairly stable, so different values reduce confidence
                    component_scores.append(0.2)
            
            # Compare WebGL fingerprint
            if webgl_fingerprint and stored_fp.get('webgl_fingerprint'):
                if webgl_fingerprint == stored_fp['webgl_fingerprint']:
                    component_scores.append(1.0)
                else:
                    # WebGL can vary more than canvas
                    component_scores.append(0.3)
            
            # NEW: Compare timing fingerprint
            if timing_fingerprint and stored_fp.get('timing_fingerprint'):
                if timing_fingerprint == stored_fp['timing_fingerprint']:
                    component_scores.append(1.0)
                else:
                    # Timing fingerprints can vary somewhat between sessions
                    component_scores.append(0.5)
            
            # Calculate overall similarity score
            if component_scores:
                # Give more weight to browser fingerprint
                score = sum(component_scores) / len(component_scores)
                
                # Track best match
                if score > best_score:
                    best_score = score
                    best_match = stored_fp
        
        # Determine if this is a known device
        threshold = 0.7  # Threshold for considering it a match
        
        if best_score >= threshold:
            # This is a known device
            # Update fingerprint last_seen time
            update_result = update_fingerprint_history(
                user_id, 
                best_match.get('fingerprint_hash'),
                data.get('device_type', 'unknown'),
                get_real_ip(),
                datetime.datetime.now(datetime.timezone.utc)
            )
            
            return jsonify({
                "status": "known_device",
                "message": "Device recognized",
                "score": best_score,
                "device_count": get_user_device_count(user_id),
                "device_fingerprint": best_match.get('fingerprint_hash')
            })
        else:
            # This is a new device
            # Check if user has reached device limit
            is_at_limit, limit_msg = check_device_limit(user_id, fingerprint_hash)
            
            if is_at_limit:
                # Record device limit reached event
                record_security_event(user_id, "device_limit_reached", {
                    "details": "User attempted to add device but reached limit",
                    "user_agent": request.headers.get('User-Agent', ''),
                    "ip_address": get_real_ip(),
                    "fingerprint_hash": fingerprint_hash,
                    "browser_fingerprint": browser_fingerprint
                })
                
                return jsonify({
                    "status": "device_limit_reached",
                    "message": limit_msg,
                    "device_count": get_user_device_count(user_id),
                    "max_devices": 5  # TODO: Get from settings
                }), 403
            
            # Store new fingerprint
            store_result, message = store_fingerprint(user_id, data)
            if store_result:
                return jsonify({
                    "status": "new_device",
                    "message": "New device registered successfully",
                    "device_count": get_user_device_count(user_id)
                })
            else:
                return jsonify({"error": message}), 400
    
    except Exception as e:
        logger.error(f"Error in verify_fingerprint: {e}\n{traceback.format_exc()}")
        return jsonify({"error": "System error"}), 500

# NEW: Helper function to record security events
def record_security_event(user_id, event_type, details=None):
    """
    Record security events for auditing and threat detection
    
    Args:
        user_id: User ID
        event_type: Type of security event
        details: Additional details about the event
    """
    try:
        # Use the security_events collection
        security_events = mining_db["security_events"]
        
        # Create event record
        event = {
            "user_id": user_id,
            "event_type": event_type,
            "timestamp": datetime.datetime.now(datetime.timezone.utc),
            "ip_address": get_real_ip(),
            "user_agent": request.headers.get('User-Agent', ''),
            "details": details or {}
        }
        
        # Insert event
        security_events.insert_one(event)
        
        # Log high priority events
        high_priority_events = ["fingerprint_tampering", "device_limit_reached", "spoofing_detected"]
        if event_type in high_priority_events:
            logger.warning(f"Security event {event_type} recorded for user {user_id}: {details}")
    except Exception as e:
        logger.error(f"Error recording security event: {e}")

# NEW: Helper function to calculate fuzzy similarity between strings
def calculate_fuzzy_similarity(str1, str2):
    """
    Calculate similarity between two strings
    Returns a value between 0 and 1, where 1 is identical
    """
    if not str1 or not str2:
        return 0.0
        
    if str1 == str2:
        return 1.0
        
    # Simple approach that doesn't require Levenshtein package
    # Compare first and last N characters
    n = 8  # Number of characters to compare
    
    start_match = str1[:n] == str2[:n]
    end_match = str1[-n:] == str2[-n:]
    
    if start_match and end_match:
        return 0.9
    elif start_match or end_match:
        return 0.6
    else:
        return 0.0
        
    # Uncomment this if you install python-Levenshtein package
    # try:
    #     import Levenshtein
    #     distance = Levenshtein.distance(str1, str2)
    #     max_len = max(len(str1), len(str2))
    #     return 1.0 - (distance / max_len)
    # except ImportError:
    #     # Fallback if Levenshtein is not available
    #     n = 8  # Number of characters to compare
    #     start_match = str1[:n] == str2[:n]
    #     end_match = str1[-n:] == str2[-n:]
    #     if start_match and end_match:
    #         return 0.9
    #     elif start_match or end_match:
    #         return 0.6
    #     else:
    #         return 0.0

@fingerprint_routes.route('/devices', methods=['GET'])
def list_devices():
    """
    List all registered devices for the current user
    
    Returns the user's registered devices with details for device management.
    """
    # Get user_id from session
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401
    
    # Get stored fingerprints
    devices = get_stored_fingerprints(user_id=user_id)
    
    # Check device limit
    limit_reached, device_count = check_device_limit(user_id)
    
    # Format device data for response
    formatted_devices = []
    for device in devices:
        # Get last seen date
        last_seen = device.get('last_seen')
        if isinstance(last_seen, datetime.datetime):
            last_seen = last_seen.isoformat()
        
        # Format device info
        formatted_devices.append({
            'fingerprint_hash': device.get('fingerprint_hash'),
            'device_type': device.get('device_type', 'unknown'),
            'user_agent': device.get('user_agent', ''),
            'created_at': device.get('created_at').isoformat() if device.get('created_at') else None,
            'last_seen': last_seen,
            'trusted': device.get('trusted', False),
            # Include a shortened display_id for UI
            'display_id': device.get('fingerprint_hash', '')[-8:] if device.get('fingerprint_hash') else 'unknown'
        })
    
    return jsonify({
        'devices': formatted_devices,
        'device_count': device_count,
        'device_limit_reached': limit_reached,
        'max_devices': 3  # This should ideally come from settings
    })

@fingerprint_routes.route('/devices/<fingerprint_hash>', methods=['DELETE'])
def remove_device(fingerprint_hash):
    """
    Remove a device from user's registered devices
    
    Args:
        fingerprint_hash: Hash of the fingerprint to remove
    """
    # Get user_id from session
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401
    
    # Validate fingerprint hash
    if not fingerprint_hash or len(fingerprint_hash) < 32:
        return jsonify({'error': 'Invalid fingerprint hash'}), 400
    
    # Remove fingerprint
    success, message = remove_fingerprint(user_id, fingerprint_hash)
    
    if success:
        # Get updated device count
        _, device_count = check_device_limit(user_id)
        
        return jsonify({
            'status': 'success',
            'message': message,
            'device_count': device_count
        })
    else:
        return jsonify({
            'status': 'error',
            'message': message
        }), 400

@fingerprint_routes.route('/devices/<fingerprint_hash>/trust', methods=['POST'])
def trust_device(fingerprint_hash):
    """
    Mark a device as trusted
    
    Args:
        fingerprint_hash: Hash of the fingerprint to trust
    """
    # Get user_id from session
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401
    
    # Validate fingerprint hash
    if not fingerprint_hash or len(fingerprint_hash) < 32:
        return jsonify({'error': 'Invalid fingerprint hash'}), 400
    
    # Mark as trusted
    success = mark_fingerprint_trusted(user_id, fingerprint_hash)
    
    if success:
        return jsonify({
            'status': 'success',
            'message': 'Device marked as trusted'
        })
    else:
        return jsonify({
            'status': 'error',
            'message': 'Could not mark device as trusted'
        }), 400

@fingerprint_routes.route('/spoofing-check', methods=['POST'])
def check_spoofing():
    """
    Check if the current device is using spoofing techniques
    
    This endpoint is useful for testing anti-spoofing detection without
    registering or verifying a device.
    """
    # Get user_id from session
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401
    
    # Generate fingerprint from current request
    fingerprint_data = get_advanced_device_fingerprint(request)
    
    # Run spoofing detection
    spoofing_check = detect_spoofing(fingerprint_data, fingerprint_data.get('ip_address'))
    
    # Return results
    return jsonify({
        'spoofing_detected': spoofing_check.get('spoofing_detected', False),
        'spoofing_likelihood': spoofing_check.get('spoofing_likelihood', 0),
        'checks': spoofing_check.get('checks', {}),
        'detection_count': spoofing_check.get('detection_count', 0),
        'fingerprint_data': {
            'device_type': fingerprint_data.get('device_type', 'unknown'),
            'canvas_present': bool(fingerprint_data.get('canvas_fingerprint')),
            'webgl_present': bool(fingerprint_data.get('webgl_fingerprint')),
            'audio_present': bool(fingerprint_data.get('audio_fingerprint')),
            'timezone_info': fingerprint_data.get('timezone_info', {})
        }
    })

@fingerprint_routes.route('/api/mining/ip-check', methods=['GET'])
@cross_origin()
def check_ip_detection():
    """
    Diagnostic endpoint to check IP detection and geolocation
    
    Returns detailed information about the client's IP address
    """
    try:
        # Get the real IP address using enhanced detection
        detected_ip = get_real_ip()
        
        # Try alternative methods if localhost detected
        external_ip = None
        if detected_ip in ["127.0.0.1", "::1", "localhost"] or detected_ip.startswith("192.168.") or detected_ip.startswith("10."):
            try:
                # Try multiple external IP detection services
                services = [
                    'https://api.ipify.org',
                    'https://ifconfig.me/ip',
                    'https://api.my-ip.io/ip',
                    'https://checkip.amazonaws.com'
                ]
                
                for service in services:
                    try:
                        response = requests.get(service, timeout=3)
                        if response.status_code == 200:
                            external_ip = response.text.strip()
                            if external_ip and len(external_ip) > 7:  # Basic validation
                                break
                    except Exception:
                        continue
            except Exception as e:
                logger.error(f"Error getting external IP: {e}")
        
        # Use external IP if detected
        if external_ip and external_ip not in ["127.0.0.1", "::1", "localhost"]:
            detected_ip = external_ip
        
        # Get IP info data
        ip_info = get_ipinfo_data(detected_ip)
        
        # Create base response
        response = {
            "ip_address": detected_ip,
            "detection_method": "enhanced_detection",
            "headers": {
                "user_agent": request.headers.get("User-Agent", ""),
                "accept_language": request.headers.get("Accept-Language", ""),
                "cf_connecting_ip": request.headers.get("CF-Connecting-IP", ""),
                "x_forwarded_for": request.headers.get("X-Forwarded-For", ""),
                "x_real_ip": request.headers.get("X-Real-IP", "")
            },
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "ip_info": ip_info
        }
        
        if external_ip:
            response["external_ip_detection"] = {
                "detected": True,
                "external_ip": external_ip
            }
        
        # Advanced fingerprinting info
        try:
            fingerprint_data = get_advanced_device_fingerprint(request)
            response["fingerprint"] = {
                "hash": fingerprint_data.get("fingerprint_hash", ""),
                "device_type": fingerprint_data.get("device_type", ""),
                "browser_info": {
                    "canvas_fingerprint": fingerprint_data.get("canvas_fingerprint", ""),
                    "webgl_fingerprint": fingerprint_data.get("webgl_fingerprint", ""),
                    "language": fingerprint_data.get("browser_language", "")
                },
                "spoofing_detected": fingerprint_data.get("spoofing_detected", False),
                "spoofing_checks": fingerprint_data.get("spoofing_checks", {})
            }
        except Exception as e:
            response["fingerprint_error"] = str(e)
        
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error in IP check endpoint: {e}")
        return jsonify({"error": str(e)}), 500

@fingerprint_routes.route('/api/mining/device-manager', methods=['GET'])
@cross_origin()
def get_user_device_list():
    """Get list of registered devices for the current user"""
    try:
        # Get user ID from query string or session
        user_id = request.args.get('user_id')
        if not user_id:
            # Try to get from session
            user_id = session.get('user_id')
            if not user_id:
                return jsonify({"error": "User ID required"}), 400
        
        # Get current device fingerprint
        current_fingerprint = get_advanced_device_fingerprint(request)
        current_device_hash = current_fingerprint.get("fingerprint_hash", "")
        
        # Get all registered devices for user
        devices = get_user_devices(user_id)
        
        # Mark current device
        for device in devices:
            device["is_current_device"] = (device["fingerprint_hash"] == current_device_hash)
            
            # Add time_ago string for easier display
            last_seen = device.get("last_seen")
            if last_seen:
                # Calculate time ago string
                device["time_ago"] = _get_time_ago(last_seen)
        
        # Get max devices limit
        max_devices = 3  # Can be changed or made configurable
        
        return jsonify({
            "devices": devices,
            "current_device": current_device_hash,
            "device_count": len(devices),
            "max_devices": max_devices,
            "can_add_more": len(devices) < max_devices
        })
    except Exception as e:
        logger.error(f"Error getting user devices: {e}")
        return jsonify({"error": str(e)}), 500

@fingerprint_routes.route('/api/mining/device-manager', methods=['POST'])
@cross_origin()
def register_new_device():
    """Register current device for the user"""
    try:
        # Get user ID from request body or session
        data = request.get_json()
        user_id = data.get('user_id') if data else None
        
        if not user_id:
            # Try to get from session
            user_id = session.get('user_id')
            if not user_id:
                return jsonify({"error": "User ID required"}), 400
        
        # Get current device fingerprint
        fingerprint_data = get_advanced_device_fingerprint(request)
        
        # Get real IP and update fingerprint
        real_ip = get_real_ip()
        if real_ip and real_ip != fingerprint_data.get("ip_address"):
            fingerprint_data["original_ip"] = fingerprint_data.get("ip_address")
            fingerprint_data["ip_address"] = real_ip
        
        # Store fingerprint
        success, result = store_fingerprint(user_id, fingerprint_data)
        
        if success:
            return jsonify({
                "success": True, 
                "message": "Device registered successfully",
                "device_hash": fingerprint_data.get("fingerprint_hash", "")
            })
        else:
            return jsonify({
                "success": False,
                "error": result.get("error", "Unknown error"),
                "details": result
            }), 400
    except Exception as e:
        logger.error(f"Error registering device: {e}")
        return jsonify({"error": str(e)}), 500

@fingerprint_routes.route('/api/mining/device-manager', methods=['DELETE'])
@cross_origin()
def remove_user_device():
    """Remove a registered device"""
    try:
        # Get user ID and device hash from query string or session
        user_id = request.args.get('user_id')
        device_hash = request.args.get('device_hash')
        
        if not user_id:
            # Try to get from session
            user_id = session.get('user_id')
            if not user_id:
                return jsonify({"error": "User ID required"}), 400
        
        if not device_hash:
            return jsonify({"error": "Device hash required"}), 400
        
        # Verify this isn't the current device
        current_fingerprint = get_advanced_device_fingerprint(request)
        current_device_hash = current_fingerprint.get("fingerprint_hash", "")
        
        if current_device_hash == device_hash:
            return jsonify({
                "success": False,
                "error": "Cannot remove current device",
                "message": "You cannot remove the device you are currently using."
            }), 400
        
        # Remove device
        success = remove_fingerprint(user_id, device_hash)
        
        if success:
            return jsonify({
                "success": True,
                "message": "Device removed successfully"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to remove device"
            }), 400
    except Exception as e:
        logger.error(f"Error removing device: {e}")
        return jsonify({"error": str(e)}), 500

def _get_time_ago(timestamp):
    """Convert timestamp to human-readable time ago string"""
    try:
        now = datetime.datetime.utcnow()
        delta = now - timestamp
        
        # Days
        if delta.days > 0:
            if delta.days == 1:
                return "yesterday"
            elif delta.days < 7:
                return f"{delta.days} days ago"
            elif delta.days < 30:
                weeks = delta.days // 7
                return f"{weeks} week{'s' if weeks > 1 else ''} ago"
            elif delta.days < 365:
                months = delta.days // 30
                return f"{months} month{'s' if months > 1 else ''} ago"
            else:
                years = delta.days // 365
                return f"{years} year{'s' if years > 1 else ''} ago"
        
        # Hours
        hours = delta.seconds // 3600
        if hours > 0:
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        
        # Minutes
        minutes = (delta.seconds % 3600) // 60
        if minutes > 0:
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        
        # Seconds
        return "just now"
    except Exception:
        return "unknown" 