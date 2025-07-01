"""
Advanced fingerprinting module for device identification

Implements comprehensive device fingerprinting techniques beyond basic user-agent detection
"""

import hashlib
import json
import logging
import re
import time
import os
from datetime import datetime
from flask import request, jsonify
from user_agents import parse

# Setup logging
logger = logging.getLogger("advanced_fingerprinting")

# Adjust similarity threshold and component weights
SIMILARITY_THRESHOLD = 0.8  # Increase threshold to reduce false positives

# Update component weights for better accuracy
weights = {
    "user_agent": 0.10,  # Reduce weight for user agent
    "canvas_fingerprint": 0.25,  # Increase weight for canvas fingerprint
    "webgl_fingerprint": 0.25,  # Increase weight for WebGL fingerprint
    "hardware_info": 0.15,
    "font_list": 0.10,
    "browser_features": 0.10,
    "screen_info": 0.05,
    "timezone_info": 0.05
}

def calculate_fingerprint_hash(components):
    """
    Calculate a deterministic hash from multiple fingerprint components
    
    Args:
        components: List of fingerprint components
        
    Returns:
        str: SHA-256 hash hexdigest
    """
    try:
        # Make sure we have at least some data
        if not components or all(not c for c in components):
            # Generate a unique fallback hash with timestamp to prevent empty hash
            fallback = f"fallback-{time.time()}"
            return hashlib.sha256(fallback.encode()).hexdigest()
            
        # Join all components with a separator and create a hash
        fingerprint_string = "|".join([str(c or "") for c in components])
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()
    except Exception as e:
        # Log the error but never return "error" as a hash
        logger.error(f"Error calculating fingerprint hash: {e}")
        # Generate a unique fallback hash with timestamp
        fallback = f"error-fallback-{time.time()}"
        return hashlib.sha256(fallback.encode()).hexdigest()

def get_advanced_device_fingerprint(request_obj):
    """
    Generate an advanced device fingerprint from the request
    
    Collects multiple signals to create a unique device fingerprint:
    - Canvas fingerprint
    - WebGL fingerprint
    - Audio fingerprint
    - Font detection
    - Hardware information
    - Browser features detection
    - Screen information
    - Timezone information
    - Request timing analysis (NEW)
    - Header consistency checks (NEW)
    
    Args:
        request_obj: Flask request object
        
    Returns:
        dict: Advanced device fingerprint data
    """
    try:
        # Get request data (POST body or GET parameters)
        request_data = request_obj.get_json() if request_obj.is_json else request_obj.form.to_dict()
        
        # Handle GET request with JSON in a parameter
        if not request_data and request_obj.args.get('fingerprint_data'):
            try:
                request_data = json.loads(request_obj.args.get('fingerprint_data'))
            except Exception:
                request_data = {}
        
        # Get user agent and parse it
        user_agent_string = request_obj.headers.get('User-Agent', '')
        browser_language = request_obj.headers.get('Accept-Language', '')
        
        # Generate browser fingerprint first - critical for identity tracking
        browser_fingerprint = hashlib.sha256(f"{user_agent_string}|{browser_language}".encode('utf-8')).hexdigest()
        
        # Extract fingerprint components from request data
        canvas_fingerprint = request_data.get('canvasFingerprint', '')
        webgl_fingerprint = request_data.get('webglFingerprint', '')
        audio_fingerprint = request_data.get('audioFingerprint', '')
        
        # NEW: Request timing fingerprint - measure request processing time
        # This is harder to spoof because it depends on the client's hardware performance
        request_start_time = request_data.get('requestStartTime', 0)
        request_end_time = request_data.get('requestEndTime', 0)
        current_time = int(time.time() * 1000)  # Current time in milliseconds
        
        # Calculate timing fingerprint
        timing_fingerprint = ""
        if request_start_time and request_end_time and (0 < request_end_time - request_start_time < 30000):
            # Valid timing data (processed within 30 seconds)
            request_duration = request_end_time - request_start_time
            # Hash the timing information
            timing_data = f"{request_start_time}|{request_end_time}|{request_duration}"
            timing_fingerprint = hashlib.sha256(timing_data.encode('utf-8')).hexdigest()
        else:
            # Generate a synthetic timing fingerprint based on user agent and current time
            # This ensures we always have a timing component
            timing_fingerprint = hashlib.sha256(f"timing_{user_agent_string}_{current_time // 86400000}".encode('utf-8')).hexdigest()
        
        # NEW: Header analysis - examine request headers for consistency and anomalies
        headers_fingerprint = _analyze_request_headers(request_obj)
        
        # If missing fingerprints, generate synthetic ones that are consistent per user agent
        if not canvas_fingerprint:
            logger.warning("Canvas fingerprint missing, generating synthetic one")
            canvas_fingerprint = hashlib.sha256(f"canvas_synthetic_{user_agent_string}".encode('utf-8')).hexdigest()
            
        if not webgl_fingerprint:
            logger.warning("WebGL fingerprint missing, generating synthetic one")
            webgl_fingerprint = hashlib.sha256(f"webgl_synthetic_{user_agent_string}".encode('utf-8')).hexdigest()
            
        if not audio_fingerprint:
            audio_fingerprint = hashlib.sha256(f"audio_synthetic_{user_agent_string}".encode('utf-8')).hexdigest()
        
        # Extract additional information
        fonts = request_data.get('fonts', [])
        if isinstance(fonts, list):
            font_list = ",".join(sorted(fonts))
        else:
            font_list = str(fonts)
            
        # Extract raw hardware info
        hardware_info = request_data.get('hardware', {})
        if not isinstance(hardware_info, dict):
            try:
                hardware_info = json.loads(hardware_info) if hardware_info else {}
            except:
                hardware_info = {}
        
        # If hardware info is empty, create some synthetic data
        if not hardware_info or not any(hardware_info.values()):
            hardware_info = {
                "processor": f"synthetic_{hashlib.md5(user_agent_string.encode()).hexdigest()[:8]}",
                "gpu": f"synthetic_gpu_{hashlib.md5(user_agent_string.encode()).hexdigest()[:8]}",
                "memory": "8",
                "platform": "Windows" if "Windows" in user_agent_string else (
                    "MacOS" if "Mac" in user_agent_string else (
                    "Linux" if "Linux" in user_agent_string else (
                    "Android" if "Android" in user_agent_string else (
                    "iOS" if "iPhone" in user_agent_string or "iPad" in user_agent_string else "Unknown"))))
            }
        
        # Improved processor info extraction
        processor_info = hardware_info.get('processor', '')
        gpu_info = hardware_info.get('gpu', '')
        memory = hardware_info.get('memory', '')
        platform = hardware_info.get('platform', '')
        
        # Extract advanced browser features
        browser_features = request_data.get('features', {})
        if not isinstance(browser_features, dict):
            try:
                browser_features = json.loads(browser_features) if browser_features else {}
            except:
                browser_features = {}
                
        # Screen information
        screen_info = request_data.get('screen', {})
        if not isinstance(screen_info, dict):
            try:
                screen_info = json.loads(screen_info) if screen_info else {}
            except:
                screen_info = {}
                
        # Timezone information
        timezone_info = request_data.get('timezone', {})
        if not isinstance(timezone_info, dict):
            try:
                timezone_info = json.loads(timezone_info) if timezone_info else {}
            except:
                timezone_info = {}
        
        # NEW: Extract WebRTC IPs for more accurate device identification
        webrtc_ips = request_data.get('webrtc_ips', [])
        if not isinstance(webrtc_ips, list):
            try:
                webrtc_ips = json.loads(webrtc_ips) if webrtc_ips else []
            except:
                webrtc_ips = []
                
        # NEW: Extract advanced hardware metrics that are difficult to spoof
        advanced_hardware = {
            "cores": hardware_info.get('cores', ''),
            "device_memory": hardware_info.get('deviceMemory', ''),
            "hardware_concurrency": hardware_info.get('hardwareConcurrency', ''),
            "device_pixel_ratio": screen_info.get('pixelRatio', ''),
            "touch_points": screen_info.get('touchPoints', '')
        }
        
        # Get IP address from request headers or remote address
        # Note: get_real_ip from mining_security should be called by the caller
        ip_address = request_obj.headers.get('X-Forwarded-For', '').split(',')[0].strip() or \
                    request_obj.headers.get('X-Real-IP', '') or \
                    request_obj.remote_addr or \
                    '127.0.0.1'
        
        # Parse user agent
        try:
            user_agent_obj = parse(user_agent_string)
            
            # Determine device type
            if user_agent_obj.is_mobile:
                device_type = "mobile"
            elif user_agent_obj.is_tablet:
                device_type = "tablet"
            else:
                device_type = "desktop"
        except:
            # Fallback device type detection if parsing fails
            if "mobile" in user_agent_string.lower() or "android" in user_agent_string.lower():
                device_type = "mobile"
            elif "tablet" in user_agent_string.lower() or "ipad" in user_agent_string.lower():
                device_type = "tablet"
            else:
                device_type = "desktop"
            
        # NEW: Enhanced spoofing checks with more comprehensive detection
        spoofing_checks = _detect_spoofing_attempts(request_obj, {
            "user_agent": user_agent_string,
            "browser_language": browser_language,
            "canvas_fingerprint": canvas_fingerprint,
            "webgl_fingerprint": webgl_fingerprint,
            "audio_fingerprint": audio_fingerprint,
            "timing_fingerprint": timing_fingerprint,
            "headers_fingerprint": headers_fingerprint,
            "hardware_info": hardware_info,
            "browser_features": browser_features,
            "screen_info": screen_info,
            "timezone_info": timezone_info
        })
        
        # NEW: Create a hardware-specific fingerprint that's more resistant to user agent spoofing
        hardware_fingerprint_components = [
            canvas_fingerprint,  # Canvas rendering is hardware-dependent
            webgl_fingerprint,   # WebGL is highly hardware-dependent
            audio_fingerprint,   # Audio processing can reveal hardware differences
            str(advanced_hardware), # Raw hardware information
            str(screen_info),     # Screen properties are hardware-dependent
            str(webrtc_ips)       # Local network configuration is difficult to spoof completely
        ]
        
        # Filter out empty components
        hardware_fingerprint_components = [c for c in hardware_fingerprint_components if c]
        
        # Generate hardware fingerprint hash
        hardware_fingerprint = hashlib.sha256("|".join(hardware_fingerprint_components).encode('utf-8')).hexdigest() if hardware_fingerprint_components else ""
        
        # Calculate fingerprint hash using multiple components (but don't let it fail)
        # This new approach weights hardware-based components more heavily than user agent
        fingerprint_components = [
            canvas_fingerprint,  # Hardware-dependent
            webgl_fingerprint,   # Hardware-dependent
            audio_fingerprint,   # Hardware-dependent
            timing_fingerprint,  # Partially hardware-dependent
            headers_fingerprint, # Partially software-dependent
            font_list,           # OS/hardware-dependent
            json.dumps(hardware_info) if hardware_info else "", # Hardware info
            json.dumps(browser_features) if browser_features else "", # Browser-specific
            json.dumps(screen_info) if screen_info else "",  # Hardware-dependent
            browser_fingerprint,  # User agent (least weight now)
        ]
        
        fingerprint_hash = calculate_fingerprint_hash(fingerprint_components)
        
        # Combine all information into a comprehensive fingerprint
        fingerprint_data = {
            "fingerprint_hash": fingerprint_hash,
            "hardware_fingerprint": hardware_fingerprint,  # NEW: Add hardware-specific fingerprint
            "device_type": device_type,
            "ip_address": ip_address,
            "user_agent": user_agent_string,
            "browser_language": browser_language,
            "browser_fingerprint": browser_fingerprint,  # Add browser fingerprint as a dedicated field
            "canvas_fingerprint": canvas_fingerprint,
            "webgl_fingerprint": webgl_fingerprint,
            "audio_fingerprint": audio_fingerprint,
            "timing_fingerprint": timing_fingerprint,  # NEW: Add timing fingerprint
            "headers_fingerprint": headers_fingerprint,  # NEW: Add headers fingerprint
            "font_list": font_list,
            "hardware_info": {
                "processor": processor_info,
                "gpu": gpu_info,
                "memory": memory,
                "platform": platform
            },
            "advanced_hardware": advanced_hardware,  # NEW: Add advanced hardware metrics
            "webrtc_ips": webrtc_ips,  # NEW: Add WebRTC IPs
            "browser_features": browser_features,
            "screen_info": screen_info,
            "timezone_info": timezone_info,
            "spoofing_detected": spoofing_checks["spoofing_detected"],
            "spoofing_checks": spoofing_checks["checks"],
            "spoofing_score": spoofing_checks["score"]  # NEW: Add numeric spoofing score
        }
        
        return fingerprint_data
        
    except Exception as e:
        logger.error(f"Error generating advanced device fingerprint: {e}")
        
        # Create a proper fallback fingerprint with reliable data
        user_agent_string = request_obj.headers.get('User-Agent', '')
        browser_language = request_obj.headers.get('Accept-Language', '')
        
        # Generate a reliable browser fingerprint
        browser_fingerprint = hashlib.sha256(f"{user_agent_string}|{browser_language}".encode('utf-8')).hexdigest()
        
        # Get approximate device type from user agent
        if "mobile" in user_agent_string.lower() or "android" in user_agent_string.lower():
            device_type = "mobile"
        elif "tablet" in user_agent_string.lower() or "ipad" in user_agent_string.lower():
            device_type = "tablet"
        else:
            device_type = "desktop"
            
        # Calculate fallback fingerprint hash that's unique and consistent
        fallback_hash = hashlib.sha256(f"fallback_{user_agent_string}_{browser_language}".encode()).hexdigest()
        
        # Generate synthetic fingerprints that are consistent for this user agent
        canvas_fp = hashlib.sha256(f"canvas_fallback_{user_agent_string}".encode()).hexdigest()
        webgl_fp = hashlib.sha256(f"webgl_fallback_{user_agent_string}".encode()).hexdigest()
        audio_fp = hashlib.sha256(f"audio_fallback_{user_agent_string}".encode()).hexdigest()
        timing_fp = hashlib.sha256(f"timing_fallback_{user_agent_string}_{int(time.time() // 86400)}".encode()).hexdigest()
        headers_fp = hashlib.sha256(f"headers_fallback_{user_agent_string}".encode()).hexdigest()
        
        return {
            "fingerprint_hash": fallback_hash,
            "browser_fingerprint": browser_fingerprint,  # Include browser fingerprint
            "device_type": device_type,
            "ip_address": request_obj.remote_addr or "127.0.0.1",
            "user_agent": user_agent_string,
            "browser_language": browser_language,
            "canvas_fingerprint": canvas_fp,
            "webgl_fingerprint": webgl_fp,
            "audio_fingerprint": audio_fp,
            "timing_fingerprint": timing_fp,  # NEW: Add timing fingerprint
            "headers_fingerprint": headers_fp,  # NEW: Add headers fingerprint
            "font_list": "fallback_fonts",
            "hardware_info": {
                "processor": "fallback_processor",
                "gpu": "fallback_gpu",
                "memory": "8",
                "platform": "Windows" if "Windows" in user_agent_string else "Unknown"
            },
            "browser_features": {},
            "screen_info": {},
            "timezone_info": {},
            "spoofing_detected": False,
            "spoofing_checks": {"error": "Used fallback fingerprinting due to error"},
            "spoofing_score": 0,
            "is_fallback": True
        }

# NEW: Header analysis function
def _analyze_request_headers(request_obj):
    """
    Analyze request headers for anomalies and generate a fingerprint
    
    Args:
        request_obj: Flask request object
        
    Returns:
        str: Header fingerprint hash
    """
    try:
        # Extract headers
        header_keys = sorted(request_obj.headers.keys())
        header_values = [request_obj.headers.get(key, '') for key in header_keys]
        
        # Create a header string for fingerprinting
        header_string = "|".join([f"{key}:{value}" for key, value in zip(header_keys, header_values)])
        
        # Generate a hash from the header string
        return hashlib.sha256(header_string.encode('utf-8')).hexdigest()
    except Exception as e:
        logger.error(f"Error analyzing request headers: {e}")
        return hashlib.sha256(b"error_headers").hexdigest()

# NEW: Enhanced spoofing detection
def _detect_spoofing_attempts(request_obj, fingerprint_components):
    """
    Enhanced detection of spoofing and manipulation attempts
    
    Args:
        request_obj: Flask request object
        fingerprint_components: Dict of fingerprint components
        
    Returns:
        dict: Spoofing detection results
    """
    try:
        # Initialize results
        results = {
            "spoofing_detected": False,
            "checks": {},
            "score": 0  # Numeric score from 0-100
        }
        
        # Extract components
        user_agent = fingerprint_components.get("user_agent", "")
        browser_language = fingerprint_components.get("browser_language", "")
        canvas_fingerprint = fingerprint_components.get("canvas_fingerprint", "")
        webgl_fingerprint = fingerprint_components.get("webgl_fingerprint", "")
        audio_fingerprint = fingerprint_components.get("audio_fingerprint", "")
        timing_fingerprint = fingerprint_components.get("timing_fingerprint", "")
        headers_fingerprint = fingerprint_components.get("headers_fingerprint", "")
        hardware_info = fingerprint_components.get("hardware_info", {})
        browser_features = fingerprint_components.get("browser_features", {})
        screen_info = fingerprint_components.get("screen_info", {})
        timezone_info = fingerprint_components.get("timezone_info", {})
        
        # Initialize checks
        checks = {}
        violation_points = 0
        
        # Check 1: Synthetic fingerprints detection
        if canvas_fingerprint and canvas_fingerprint.startswith(("canvas_synthetic", "canvas_fallback")):
            checks["synthetic_canvas"] = True
            violation_points += 10
        
        if webgl_fingerprint and webgl_fingerprint.startswith(("webgl_synthetic", "webgl_fallback")):
            checks["synthetic_webgl"] = True
            violation_points += 10
            
        # Check 2: Browser inconsistencies
        if "Safari" in user_agent and "Chrome" in user_agent and "Edge" not in user_agent and "Edg/" not in user_agent:
            # Safari and Chrome reported together (suspicious unless it's Edge)
            checks["browser_inconsistency"] = "Safari and Chrome reported together"
            violation_points += 15
            
        if "Firefox" in user_agent and "iPhone" in user_agent:
            # Firefox doesn't exist on iOS
            checks["browser_inconsistency"] = "Firefox on iOS (impossible combination)"
            violation_points += 25
            
        # Check 3: Header inconsistencies
        accept_header = request_obj.headers.get("Accept", "")
        accept_encoding = request_obj.headers.get("Accept-Encoding", "")
        
        if "text/html" not in accept_header and "application/json" not in accept_header:
            # Most browsers have these accept types
            checks["suspicious_accept_header"] = True
            violation_points += 10
            
        if not accept_encoding:
            # Most browsers specify encoding
            checks["missing_accept_encoding"] = True
            violation_points += 5
            
        # Check 4: Browser feature inconsistencies
        if isinstance(browser_features, dict):
            # Look for automation signals
            if browser_features.get("webdriver") is True:
                checks["webdriver_present"] = True
                violation_points += 30
                
            if browser_features.get("automationActive") is True:
                checks["automation_active"] = True
                violation_points += 30
        
        # Check 5: Hardware/platform consistency
        if isinstance(hardware_info, dict) and hardware_info:
            platform = hardware_info.get("platform", "").lower()
            
            # Check if platform matches user agent
            platform_in_ua = False
            if platform == "windows" and "Windows" in user_agent:
                platform_in_ua = True
            elif platform == "macos" and ("Mac" in user_agent or "Macintosh" in user_agent):
                platform_in_ua = True
            elif platform == "linux" and "Linux" in user_agent:
                platform_in_ua = True
            elif platform == "android" and "Android" in user_agent:
                platform_in_ua = True
            elif platform == "ios" and ("iPhone" in user_agent or "iPad" in user_agent):
                platform_in_ua = True
                
            if not platform_in_ua and platform:
                checks["platform_mismatch"] = f"Reported {platform} but not found in User-Agent"
                violation_points += 20
        
        # Check 6: Virtual machine or emulator detection
        vm_indicators = ["vmware", "virtualbox", "qemu", "hyperv", "parallels", "xen"]
        if isinstance(hardware_info, dict):
            processor = str(hardware_info.get("processor", "")).lower()
            gpu = str(hardware_info.get("gpu", "")).lower()
            
            for indicator in vm_indicators:
                if indicator in processor or indicator in gpu:
                    checks["vm_detected"] = indicator
                    violation_points += 10
                    break
        
        # Check 7: Inconsistent timezone
        if isinstance(timezone_info, dict) and timezone_info:
            tz_offset = timezone_info.get("offset")
            tz_name = timezone_info.get("timezone")
            
            if tz_name and tz_offset is not None:
                # Very basic check for major inconsistencies
                if "America" in str(tz_name) and not (-12 <= int(tz_offset) <= -4):
                    checks["timezone_inconsistency"] = f"American timezone with offset {tz_offset}"
                    violation_points += 15
                elif "Europe" in str(tz_name) and not (-1 <= int(tz_offset) <= 3):
                    checks["timezone_inconsistency"] = f"European timezone with offset {tz_offset}"
                    violation_points += 15
                elif "Asia" in str(tz_name) and not (5 <= int(tz_offset) <= 12):
                    checks["timezone_inconsistency"] = f"Asian timezone with offset {tz_offset}"
                    violation_points += 15
        
        # Determine final spoofing score (cap at 100)
        spoofing_score = min(100, violation_points)
        
        # Set spoofing detected if score is above threshold
        spoofing_detected = spoofing_score >= 30
        
        # Prepare final result
        results["spoofing_detected"] = spoofing_detected
        results["checks"] = checks
        results["score"] = spoofing_score
        
        return results
    except Exception as e:
        logger.error(f"Error detecting spoofing attempts: {e}")
        return {"spoofing_detected": False, "checks": {"error": str(e)}, "score": 0}

def calculate_fingerprint_similarity(fingerprint1, fingerprint2):
    """
    Calculate similarity score between two fingerprints
    
    Args:
        fingerprint1: First fingerprint dictionary
        fingerprint2: Second fingerprint dictionary
        
    Returns:
        float: Similarity score between 0.0 (completely different) and 1.0 (identical)
    """
    try:
        similarity_score = 0.0
        total_weight = 0.0
        
        # Compare user agent (partial string match)
        if fingerprint1.get("user_agent") and fingerprint2.get("user_agent"):
            ua1 = fingerprint1["user_agent"].lower()
            ua2 = fingerprint2["user_agent"].lower()
            
            # Calculate Jaccard similarity for user agent tokens
            tokens1 = set(re.split(r'\W+', ua1))
            tokens2 = set(re.split(r'\W+', ua2))
            
            if tokens1 and tokens2:
                intersection = len(tokens1.intersection(tokens2))
                union = len(tokens1.union(tokens2))
                ua_similarity = intersection / union if union > 0 else 0
                similarity_score += ua_similarity * weights["user_agent"]
                total_weight += weights["user_agent"]
        
        # Compare canvas fingerprint (exact match)
        if fingerprint1.get("canvas_fingerprint") and fingerprint2.get("canvas_fingerprint"):
            canvas_match = fingerprint1["canvas_fingerprint"] == fingerprint2["canvas_fingerprint"]
            similarity_score += (1.0 if canvas_match else 0.0) * weights["canvas_fingerprint"]
            total_weight += weights["canvas_fingerprint"]
            
        # Compare WebGL fingerprint (exact match)
        if fingerprint1.get("webgl_fingerprint") and fingerprint2.get("webgl_fingerprint"):
            webgl_match = fingerprint1["webgl_fingerprint"] == fingerprint2["webgl_fingerprint"]
            similarity_score += (1.0 if webgl_match else 0.0) * weights["webgl_fingerprint"]
            total_weight += weights["webgl_fingerprint"]
            
        # Compare hardware info
        if fingerprint1.get("hardware_info") and fingerprint2.get("hardware_info"):
            hw1 = fingerprint1["hardware_info"]
            hw2 = fingerprint2["hardware_info"]
            
            hw_matches = 0
            hw_total = 0
            
            for key in ["processor", "gpu", "memory", "platform"]:
                if hw1.get(key) and hw2.get(key):
                    hw_total += 1
                    if hw1[key] == hw2[key]:
                        hw_matches += 1
            
            if hw_total > 0:
                hw_similarity = hw_matches / hw_total
                similarity_score += hw_similarity * weights["hardware_info"]
                total_weight += weights["hardware_info"]
                
        # Compare font list
        if fingerprint1.get("font_list") and fingerprint2.get("font_list"):
            font_list1 = set(fingerprint1["font_list"].split(","))
            font_list2 = set(fingerprint2["font_list"].split(","))
            
            if font_list1 and font_list2:
                intersection = len(font_list1.intersection(font_list2))
                union = len(font_list1.union(font_list2))
                font_similarity = intersection / union if union > 0 else 0
                similarity_score += font_similarity * weights["font_list"]
                total_weight += weights["font_list"]
                
        # Compare browser features
        if fingerprint1.get("browser_features") and fingerprint2.get("browser_features"):
            bf1 = fingerprint1["browser_features"]
            bf2 = fingerprint2["browser_features"]
            
            if isinstance(bf1, dict) and isinstance(bf2, dict):
                bf_matches = 0
                bf_total = 0
                
                all_keys = set(bf1.keys()).union(set(bf2.keys()))
                for key in all_keys:
                    if key in bf1 and key in bf2:
                        bf_total += 1
                        if bf1[key] == bf2[key]:
                            bf_matches += 1
                
                if bf_total > 0:
                    bf_similarity = bf_matches / bf_total
                    similarity_score += bf_similarity * weights["browser_features"]
                    total_weight += weights["browser_features"]
                    
        # Compare screen info
        if fingerprint1.get("screen_info") and fingerprint2.get("screen_info"):
            screen1 = fingerprint1["screen_info"]
            screen2 = fingerprint2["screen_info"]
            
            if isinstance(screen1, dict) and isinstance(screen2, dict):
                screen_matches = 0
                screen_total = 0
                
                for key in ["width", "height", "colorDepth", "pixelRatio"]:
                    if key in screen1 and key in screen2:
                        screen_total += 1
                        if screen1[key] == screen2[key]:
                            screen_matches += 1
                
                if screen_total > 0:
                    screen_similarity = screen_matches / screen_total
                    similarity_score += screen_similarity * weights["screen_info"]
                    total_weight += weights["screen_info"]
                    
        # Compare timezone info
        if fingerprint1.get("timezone_info") and fingerprint2.get("timezone_info"):
            tz1 = fingerprint1["timezone_info"]
            tz2 = fingerprint2["timezone_info"]
            
            if isinstance(tz1, dict) and isinstance(tz2, dict):
                tz_matches = 0
                tz_total = 0
                
                for key in ["timezone", "offset"]:
                    if key in tz1 and key in tz2:
                        tz_total += 1
                        if tz1[key] == tz2[key]:
                            tz_matches += 1
                
                if tz_total > 0:
                    tz_similarity = tz_matches / tz_total
                    similarity_score += tz_similarity * weights["timezone_info"]
                    total_weight += weights["timezone_info"]
        
        # Normalize score based on available components
        if total_weight > 0:
            return similarity_score / total_weight
        else:
            return 0.0
            
    except Exception as e:
        logger.error(f"Error calculating fingerprint similarity: {e}")
        return 0.0

def find_matching_devices(fingerprint, device_list, threshold=0.85):
    """
    Find devices matching the provided fingerprint
    
    Args:
        fingerprint: Fingerprint to match
        device_list: List of device fingerprints to compare against
        threshold: Similarity threshold (0.0-1.0)
        
    Returns:
        list: Matching devices above threshold
    """
    if not fingerprint or not device_list:
        return []
        
    matches = []
    
    for device in device_list:
        similarity = calculate_fingerprint_similarity(fingerprint, device)
        if similarity >= threshold:
            # Add similarity score to device data
            device_copy = device.copy()
            device_copy["similarity_score"] = similarity
            matches.append(device_copy)
    
    # Sort by similarity (highest first)
    matches.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)
    return matches

def detect_spoofing(fingerprint_data):
    """
    Detect if fingerprint has signs of spoofing
    
    Args:
        fingerprint_data: Fingerprint data to analyze
        
    Returns:
        tuple: (is_spoofed, details)
    """
    if not fingerprint_data or not isinstance(fingerprint_data, dict):
        return False, {"error": "Invalid fingerprint data"}
        
    spoofing_detected = False
    details = {}
    
    # Check for direct spoofing flags
    if fingerprint_data.get("spoofing_detected"):
        spoofing_detected = True
        details["detected_by_client"] = fingerprint_data.get("spoofing_checks", {})
        
    # Additional server-side spoofing checks
    
    # 1. Check for inconsistent user agent
    user_agent = fingerprint_data.get("user_agent", "").lower()
    device_type = fingerprint_data.get("device_type", "")
    
    if user_agent and device_type:
        # Mobile device claiming to be desktop
        if "windows" in user_agent and device_type == "mobile":
            spoofing_detected = True
            details["ua_device_mismatch"] = True
            
        # Desktop device claiming to be mobile
        if ("android" in user_agent or "iphone" in user_agent) and device_type == "desktop":
            spoofing_detected = True
            details["ua_device_mismatch"] = True
    
    # 2. Check for canvas/webGL fingerprinting evasion
    if device_type == "desktop":
        if not fingerprint_data.get("canvas_fingerprint") and not fingerprint_data.get("webgl_fingerprint"):
            spoofing_detected = True
            details["fingerprinting_blocked"] = True
            
    # 3. Check for virtual machine or emulator indicators
    hardware_info = fingerprint_data.get("hardware_info", {})
    vm_indicators = ["vmware", "virtualbox", "virtual", "qemu", "xen", "parallels"]
    
    if isinstance(hardware_info, dict):
        processor = str(hardware_info.get("processor", "")).lower()
        gpu = str(hardware_info.get("gpu", "")).lower()
        
        for indicator in vm_indicators:
            if indicator in processor or indicator in gpu:
                spoofing_detected = True
                details["vm_detected"] = True
                break
                
    # 4. Check for inconsistent fonts
    # Most modern browsers have at least 20 standard fonts
    fonts = fingerprint_data.get("font_list", "")
    if isinstance(fonts, str) and fonts:
        font_count = len(fonts.split(","))
        if font_count < 10 and device_type == "desktop":
            spoofing_detected = True
            details["suspicious_fonts"] = True
    
    # 5. Inconsistent timezone information
    timezone_info = fingerprint_data.get("timezone_info", {})
    if isinstance(timezone_info, dict) and timezone_info:
        # Check for mismatched timezone and offset
        tz_name = timezone_info.get("timezone")
        tz_offset = timezone_info.get("offset")
        
        # Simple validation of common inconsistencies
        # This is a basic check - would need a timezone database for more complex validation
        if tz_name and tz_offset is not None:
            us_timezones = ["america", "us"]
            eu_timezones = ["europe", "berlin", "paris", "london", "rome"]
            asia_timezones = ["asia", "tokyo", "shanghai", "hong_kong"]
            
            tz_name_lower = str(tz_name).lower()
            
            # Check for major inconsistencies
            is_us = any(zone in tz_name_lower for zone in us_timezones)
            is_eu = any(zone in tz_name_lower for zone in eu_timezones)
            is_asia = any(zone in tz_name_lower for zone in asia_timezones)
            
            # Extremely simplified check for obvious mismatches
            if is_us and (tz_offset > -4 or tz_offset < -10):
                spoofing_detected = True
                details["timezone_mismatch"] = True
            elif is_eu and (tz_offset < 0 or tz_offset > 3):
                spoofing_detected = True
                details["timezone_mismatch"] = True
            elif is_asia and (tz_offset < 8 or tz_offset > 10):
                spoofing_detected = True
                details["timezone_mismatch"] = True
                
    # Combine results
    return spoofing_detected, details

def add_fingerprint_headers(options=None):
    """
    Add fingerprinting data to request headers
    
    Args:
        options: Request options (headers, etc)
        
    Returns:
        dict: Updated request options with fingerprinting headers
    """
    try:
        if options is None:
            options = {}
            
        if 'headers' not in options:
            options['headers'] = {}
            
        # Generate all fingerprinting data
        fingerprint_data = _generate_client_fingerprint_data()
        
        # Add fingerprinting data to headers
        options['headers']['X-Fingerprint-Data'] = json.dumps(fingerprint_data)
        
        return options
    except Exception as e:
        logger.error(f"Error adding fingerprint headers: {e}")
        return options or {}

def _generate_client_fingerprint_data():
    """
    Generate fingerprinting data on the client side
    For use with the JavaScript library
    
    Returns:
        dict: Fingerprinting data
    """
    # This is a client-side function implemented in JavaScript
    # Here, we just return a placeholder to be replaced by actual client-side data
    return {
        "placeholder": "This will be replaced by client-side data"
    }

def getAllFingerprints():
    """
    Get all fingerprinting data from the client browser
    Public function for use in JavaScript
    
    Returns:
        dict: Complete fingerprinting data
    """
    # This is a client-side function implemented in JavaScript
    # Here, we just return a placeholder to be replaced by actual client-side data
    return {
        "placeholder": "This will be replaced by client-side data"
    } 