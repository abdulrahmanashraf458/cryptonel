"""
Module for detecting fingerprint spoofing and fraud attempts
"""

import re
import logging
import json
from backend.cryptonel.mining.mining_security import memcached_cached, IPAnalyzer

# Configure logging
logger = logging.getLogger("anti_spoofing")

class SpoofingDetector:
    """
    Enhanced spoofing detection with improved user agent validation
    and device fingerprinting checks
    """
    
    # Browser-OS inconsistencies to detect
    BROWSER_OS_INCONSISTENCIES = [
        # Safari only runs on Apple OS
        {"browser": "Safari", "disallowed_os": ["Windows", "Linux", "Android"], "min_version": 12},
        # Chrome doesn't exist on old IE Windows
        {"browser": "Chrome", "disallowed_os": ["Windows NT 5.1", "Windows NT 5.0"], "min_version": 49},
        # IE only exists on Windows
        {"browser": "MSIE", "disallowed_os": ["Mac", "iPhone", "Linux", "Android"], "max_version": 11},
        # Firefox on iOS doesn't exist (only WebKit allowed)
        {"browser": "Firefox", "disallowed_os": ["iPhone", "iPad"], "min_version": 60},
        # Edge specific checks
        {"browser": "Edge", "disallowed_os": ["iPhone", "iPad", "Android"], "min_version": 79},
        # Mobile browser checks
        {"browser": "Samsung Internet", "disallowed_os": ["Windows", "Mac", "iPhone", "iPad"], "min_version": 10},
        {"browser": "UCBrowser", "disallowed_os": ["Mac"], "min_version": 10},
        # Additional browser checks
        {"browser": "Opera", "disallowed_os": ["iPhone", "iPad"], "min_version": 60},
        {"browser": "Yandex", "disallowed_os": ["iPhone", "iPad"], "min_version": 10},
        {"browser": "Vivaldi", "disallowed_os": ["iPhone", "iPad"], "min_version": 1},
        {"browser": "Brave", "disallowed_os": ["iPhone", "iPad"], "min_version": 1},
        {"browser": "SamsungBrowser", "disallowed_os": ["Windows", "Mac", "iPhone", "iPad"], "min_version": 10},
        {"browser": "QQBrowser", "disallowed_os": ["Mac"], "min_version": 10},
        {"browser": "Maxthon", "disallowed_os": ["iPhone", "iPad"], "min_version": 1},
        {"browser": "Puffin", "disallowed_os": ["iPhone", "iPad"], "min_version": 1},
        {"browser": "Sogou Explorer", "disallowed_os": ["Mac", "iPhone", "iPad"], "min_version": 1}
    ]
    
    # Unusual header combinations that suggest spoofing
    SUSPICIOUS_HEADER_COMBOS = [
        # Desktop headers with mobile browser strings
        {"header": "User-Agent", "contains": "Mobile", "conflict_header": "X-Screen-Info", "conflict_pattern": r"1920"},
        # Mobile UA with desktop screen resolution
        {"header": "User-Agent", "contains": "Android|iPhone", "conflict_header": "X-Screen-Info", "conflict_pattern": r"2560|1920"},
        # Touch points inconsistency
        {"header": "User-Agent", "contains": "iPhone|Android", "conflict_header": "X-Touch-Points", "conflict_value": "0"},
        # NEW: Additional inconsistencies
        {"header": "User-Agent", "contains": "iPhone", "conflict_header": "X-Screen-Width", "conflict_value": "1920"},
        {"header": "User-Agent", "contains": "Android", "conflict_header": "X-Browser-Feature-Notification", "conflict_value": "not-implemented"},
        {"header": "Accept-Language", "contains": "ar", "conflict_header": "X-Timezone-Offset", "conflict_pattern": r"^-7|-8|-9|-10|-11|-12"}
    ]
    
    # Hardware-software inconsistencies
    HARDWARE_INCONSISTENCIES = [
        # ARM processor reported but Intel/AMD in user agent
        {"hardware": "processor_info", "pattern": r"ARM", "ua_conflict": r"Intel|AMD|x86_64"},
        # Intel/AMD processor but ARM in user agent
        {"hardware": "processor_info", "pattern": r"Intel|AMD", "ua_conflict": r"ARM|aarch64"},
        # NEW: Additional hardware inconsistencies
        {"hardware": "gpu_info", "pattern": r"Apple|M1|M2", "ua_conflict": r"Windows|Linux|Android"},
        {"hardware": "gpu_info", "pattern": r"Nvidia|GeForce", "ua_conflict": r"iPhone|iPad"},
        {"hardware": "memory", "pattern": r"^(1|2)$", "ua_conflict": r"Firefox/9[0-9]|Chrome/11[0-9]"}
    ]
    
    # Known headless browser, automation, and fingerprint blocking indicators
    HEADLESS_INDICATORS = [
        # Headless browsers and automation tools
        "HeadlessChrome",
        "Chrome-Lighthouse",
        "PhantomJS",
        "Headless",
        "Zombie.js",
        "Nightmare",
        "Puppeteer",
        "Selenium",
        "Webdriver",
        "Playwright",
        "Cypress",
        "TestCafe",
        "Protractor",
        "WebDriver",
        "Selenide",
        "Watir",
        "Cucumber",
        "Appium",
        "Detox",
        "Jest",
        "Mocha",
        "Jasmine",
        "Karma",
        "Ava",
        "Tape",
        
        # Fingerprint blocking extensions
        "CanvasBlocker",
        "Canvas Defender",
        "Chameleon",
        "Random User-Agent",
        "User-Agent Switcher",
        "Trace",
        "Privacy Badger",
        "Privacy Possum",
        "NoScript",
        "ScriptSafe",
        "uBlock Origin",
        "uMatrix",
        "Decentraleyes",
        "Disable WebRTC",
        "HTTPS Everywhere",
        "Privacy Settings",
        "WebRTC Leak Prevent",
        "Canvas Fingerprint Defender",
        "Fingerprint Spoofing",
        "Anti Fingerprinting",
        "Anti-Fingerprint",
        "AntiFingerprint",
        "Fingerprint Protection"
    ]
    
    # Known VPN/Proxy/Tor indicators
    PROXY_INDICATORS = [
        "vpn", "proxy", "tor", "anonymizer", "anonymizing", "anonymize",
        "anonymization", "anonym", "anonymity", "anonymously", "anonymouse",
        "hide", "hiding", "hidden", "mask", "masking", "masked", "cloak",
        "cloaking", "cloaked", "conceal", "concealing", "concealed", "obfuscate",
        "obfuscating", "obfuscated", "obfuscation", "spoof", "spoofing", "spoofed",
        "fake", "faking", "faked", "falsify", "falsifying", "falsified", "falsification",
        "decoy", "decoying", "decoyed", "decoyment", "decoying", "decoyed", "decoyment",
        "camouflage", "camouflaging", "camouflaged", "camouflagic", "camouflagist",
        "camouflet", "camoufleur", "camouflet", "camoufleur", "camouflet", "camoufleur",
        "camouflet", "camoufleur", "camouflet", "camoufleur", "camouflet", "camoufleur"
    ]
    
    # Known automation frameworks
    AUTOMATION_FRAMEWORKS = [
        "selenium", "puppeteer", "playwright", "cypress", "testcafe", "protractor",
        "webdriverio", "nightwatch", "taiko", "testcafe", "testcafe-testing-library",
        "testcafe-browser-provider-browserstack", "testcafe-browser-provider-saucelabs",
        "testcafe-browser-provider-crossbrowsertesting", "testcafe-browser-provider-lambdatest",
        "testcafe-browser-provider-browserstack", "testcafe-browser-provider-saucelabs",
        "testcafe-browser-provider-crossbrowsertesting", "testcafe-browser-provider-lambdatest",
        "testcafe-browser-provider-browserstack", "testcafe-browser-provider-saucelabs",
        "testcafe-browser-provider-crossbrowsertesting", "testcafe-browser-provider-lambdatest"
    ]
    
    # NEW: Browser features that must be consistent with user agent
    BROWSER_FEATURE_CONSISTENCY = [
        {"ua_pattern": r"Chrome/(\d+)", "feature": "chrome_version", "min_version": 70},
        {"ua_pattern": r"Firefox/(\d+)", "feature": "firefox_version", "min_version": 60},
        {"ua_pattern": r"Safari/(\d+)", "feature": "safari_version", "min_version": 12},
        {"ua_pattern": r"Edg/(\d+)", "feature": "edge_version", "min_version": 79}
    ]
    
    # NEW: Enhanced VM detection patterns
    VM_INDICATORS = [
        # VMWare
        {"component": "canvas", "pattern": r"VMware"},
        {"component": "webgl", "pattern": r"VMware|SVGA3D|llvmpipe"},
        {"component": "hardware", "pattern": r"VMware|Virtual|QEMU|KVM"},
        # VirtualBox
        {"component": "hardware", "pattern": r"VirtualBox|Oracle|VBoxSVGA"},
        {"component": "webgl", "pattern": r"VirtualBox|VBOX"},
        # Xen
        {"component": "hardware", "pattern": r"Xen|XenSource"},
        # QEMU
        {"component": "hardware", "pattern": r"QEMU|KVM|Bochs|TCG"},
        {"component": "webgl", "pattern": r"QEMU|Mesa|llvmpipe|softpipe"},
        # Parallels
        {"component": "hardware", "pattern": r"Parallels"},
        # Hyper-V
        {"component": "hardware", "pattern": r"Hyper-V|Microsoft Virtual"},
        # Generic VM indicators
        {"component": "hardware", "pattern": r"Virtual HD|vCPU|VM Platform|hypervisor"},
        {"component": "features", "pattern": r"vmware|virtualbox|qemu|xen|hyperv|kvm"}
    ]
    
    # NEW: Detect timing inconsistencies
    @staticmethod
    def detect_timing_inconsistency(timing_data, request_headers=None):
        """
        Enhanced timing anomaly detection with improved automation detection
        
        Args:
            timing_data: Dict containing timing information
            request_headers: Optional request headers for additional context
            
        Returns:
            dict: Timing anomaly detection results with enhanced scoring
        """
        results = {"anomalies": [], "score": 0, "flags": []}
        
        try:
            if not timing_data or not isinstance(timing_data, dict):
                return results
                
            # Check for missing or invalid timing data
            required_timing_fields = ["navigationStart", "loadEventEnd", "domComplete", "domInteractive"]
            missing_fields = [field for field in required_timing_fields if field not in timing_data]
            
            if missing_fields:
                results["anomalies"].append(f"missing_timing_fields: {', '.join(missing_fields)}")
                results["score"] += 20 * len(missing_fields)
                results["flags"].append("incomplete_timing_data")
            
            # Check request timing data
            if "requestTime" in timing_data:
                request_time = timing_data.get("requestTime", 0)
                
                # Check for impossibly fast operations (automated)
                if 0 < request_time < 5:  # Less than 5ms is suspicious
                    results["anomalies"].append("impossibly_fast_request")
                    results["score"] += 50  # Increased from 30
                    results["flags"].append("automation_suspected")
                # Check for human-like timing patterns
                elif 5 <= request_time <= 50:  # Suspiciously fast but possible
                    results["anomalies"].append("suspiciously_fast_request")
                    results["score"] += 20
                
                # Check for too precise timing (automated)
                if isinstance(request_time, float):
                    # Check for round numbers (common in automation)
                    if request_time % 10 == 0:
                        results["anomalies"].append("suspiciously_round_timing")
                        results["score"] += 15
                    # Check for too many decimal places (unlikely in real browsers)
                    if len(str(request_time).split('.')[-1]) > 3:
                        results["anomalies"].append("excessively_precise_timing")
                        results["score"] += 10
            
            # Check for page load timing consistency
            if "navigationStart" in timing_data and "loadEventEnd" in timing_data:
                load_time = timing_data.get("loadEventEnd", 0) - timing_data.get("navigationStart", 0)
                
                # Check for impossibly fast page loads
                if 0 < load_time < 10:  # Less than 10ms is suspicious
                    results["anomalies"].append("impossibly_fast_page_load")
                    results["score"] += 40
                    results["flags"].append("automation_suspected")
                # Check for suspiciously consistent load times
                elif 10 < load_time < 100:  # Suspiciously fast but possible
                    results["anomalies"].append("suspiciously_fast_page_load")
                    results["score"] += 20
            
            # Check if the performance API was spoofed
            if "domComplete" in timing_data and "domInteractive" in timing_data:
                dom_complete = timing_data.get("domComplete", 0)
                dom_interactive = timing_data.get("domInteractive", 0)
                
                if dom_complete < dom_interactive:
                    results["anomalies"].append("impossible_timing_sequence")
                    results["score"] += 60  # Increased from 40
                    results["flags"].append("timing_spoofing_detected")
                
                # Check for suspiciously similar timings
                if 0 < dom_complete - dom_interactive < 5:  # Unrealistically close timings
                    results["anomalies"].append("suspiciously_similar_timings")
                    results["score"] += 30
            
            # Check for missing or zero timing values that should be present
            for field in ["connectStart", "connectEnd", "domLoading", "domContentLoadedEventStart"]:
                if field in timing_data and timing_data[field] == 0:
                    results["anomalies"].append(f"zero_value_timing: {field}")
                    results["score"] += 15
            
            # Check for unrealistic timing patterns
            if "responseStart" in timing_data and "requestStart" in timing_data:
                response_time = timing_data["responseStart"] - timing_data["requestStart"]
                if response_time < 0:  # Negative response time is impossible
                    results["anomalies"].append("negative_response_time")
                    results["score"] += 50
                    results["flags"].append("timing_spoofing_detected")
            
            # Check for missing performance timing API data
            if not any(key in timing_data for key in ["navigationStart", "loadEventEnd"]):
                results["anomalies"].append("missing_performance_timing_data")
                results["score"] += 30
                results["flags"].append("timing_api_tampering")
            
            # Check for inconsistencies between timing sources
            if "now" in timing_data and "performanceNow" in timing_data:
                diff = abs(timing_data["now"] - timing_data["performanceNow"])
                if diff > 1000:  # More than 1 second difference is suspicious
                    results["anomalies"].append("inconsistent_timing_sources")
                    results["score"] += 25
            
            # Check for automation patterns in timing data
            if "timingData" in timing_data and isinstance(timing_data["timingData"], dict):
                # Look for patterns that suggest automation
                for key, value in timing_data["timingData"].items():
                    if isinstance(value, (int, float)) and value > 0:
                        # Check for suspiciously round numbers (common in automation)
                        if value % 100 == 0:
                            results["anomalies"].append(f"suspiciously_round_{key}")
                            results["score"] += 10
                        # Check for suspiciously similar values
                        elif any(abs(value - v) < 5 for k, v in timing_data["timingData"].items() 
                               if k != key and isinstance(v, (int, float)) and v > 0):
                            results["anomalies"].append(f"suspiciously_similar_{key}")
                            results["score"] += 15
            
            # Check for missing or invalid timing events
            required_events = ["domLoading", "domInteractive", "domComplete", "loadEventStart", "loadEventEnd"]
            missing_events = [event for event in required_events if event not in timing_data]
            
            if missing_events:
                results["anomalies"].append(f"missing_timing_events: {', '.join(missing_events)}")
                results["score"] += 10 * len(missing_events)
                results["flags"].append("incomplete_timing_events")
            
            # Check for unrealistic timing sequences
            timing_sequence = [
                ("navigationStart", "fetchStart"),
                ("fetchStart", "domainLookupStart"),
                ("domainLookupStart", "domainLookupEnd"),
                ("domainLookupEnd", "connectStart"),
                ("connectStart", "connectEnd"),
                ("connectEnd", "requestStart"),
                ("requestStart", "responseStart"),
                ("responseStart", "responseEnd"),
                ("responseEnd", "domLoading"),
                ("domLoading", "domInteractive"),
                ("domInteractive", "domContentLoadedEventStart"),
                ("domContentLoadedEventStart", "domContentLoadedEventEnd"),
                ("domContentLoadedEventEnd", "domComplete"),
                ("domComplete", "loadEventStart"),
                ("loadEventStart", "loadEventEnd")
            ]
            
            for start, end in timing_sequence:
                if start in timing_data and end in timing_data:
                    duration = timing_data[end] - timing_data[start]
                    if duration < 0:  # Negative duration is impossible
                        results["anomalies"].append(f"negative_duration_{start}_to_{end}")
                        results["score"] += 30
                        results["flags"].append("invalid_timing_sequence")
            
            # Check for missing or zero navigation start
            if "navigationStart" not in timing_data or timing_data["navigationStart"] == 0:
                results["anomalies"].append("missing_or_zero_navigation_start")
                results["score"] += 40
                results["flags"].append("timing_tampering_detected")
            
            # Check for missing or zero load event end
            if "loadEventEnd" not in timing_data or timing_data["loadEventEnd"] == 0:
                results["anomalies"].append("missing_or_zero_load_event_end")
                results["score"] += 30
                results["flags"].append("timing_tampering_detected")
            
            # Check for missing or zero dom complete
            if "domComplete" not in timing_data or timing_data["domComplete"] == 0:
                results["anomalies"].append("missing_or_zero_dom_complete")
                results["score"] += 25
            
            # Check for missing or zero dom interactive
            if "domInteractive" not in timing_data or timing_data["domInteractive"] == 0:
                results["anomalies"].append("missing_or_zero_dom_interactive")
                results["score"] += 25
            
            # Check for missing or zero dom loading
            if "domLoading" not in timing_data or timing_data["domLoading"] == 0:
                results["anomalies"].append("missing_or_zero_dom_loading")
                results["score"] += 20
            
            # Check for missing or zero dom content loaded event start
            if "domContentLoadedEventStart" not in timing_data or timing_data["domContentLoadedEventStart"] == 0:
                results["anomalies"].append("missing_or_zero_dom_content_loaded_event_start")
                results["score"] += 15
            
            # Check for missing or zero dom content loaded event end
            if "domContentLoadedEventEnd" not in timing_data or timing_data["domContentLoadedEventEnd"] == 0:
                results["anomalies"].append("missing_or_zero_dom_content_loaded_event_end")
                results["score"] += 15
            
            # Check for missing or zero load event start
            if "loadEventStart" not in timing_data or timing_data["loadEventStart"] == 0:
                results["anomalies"].append("missing_or_zero_load_event_start")
                results["score"] += 15
            
            # Check for missing or zero fetch start
            if "fetchStart" not in timing_data or timing_data["fetchStart"] == 0:
                results["anomalies"].append("missing_or_zero_fetch_start")
                results["score"] += 15
            
            # Check for missing or zero domain lookup start
            if "domainLookupStart" not in timing_data or timing_data["domainLookupStart"] == 0:
                results["anomalies"].append("missing_or_zero_domain_lookup_start")
                results["score"] += 15
            
            # Check for missing or zero domain lookup end
            if "domainLookupEnd" not in timing_data or timing_data["domainLookupEnd"] == 0:
                results["anomalies"].append("missing_or_zero_domain_lookup_end")
                results["score"] += 15
            
            # Check for missing or zero connect start
            if "connectStart" not in timing_data or timing_data["connectStart"] == 0:
                results["anomalies"].append("missing_or_zero_connect_start")
                results["score"] += 15
            
            # Check for missing or zero connect end
            if "connectEnd" not in timing_data or timing_data["connectEnd"] == 0:
                results["anomalies"].append("missing_or_zero_connect_end")
                results["score"] += 15
            
            # Check for missing or zero request start
            if "requestStart" not in timing_data or timing_data["requestStart"] == 0:
                results["anomalies"].append("missing_or_zero_request_start")
                results["score"] += 15
            
            # Check for missing or zero response start
            if "responseStart" not in timing_data or timing_data["responseStart"] == 0:
                results["anomalies"].append("missing_or_zero_response_start")
                results["score"] += 15
            
            # Check for missing or zero response end
            if "responseEnd" not in timing_data or timing_data["responseEnd"] == 0:
                results["anomalies"].append("missing_or_zero_response_end")
                results["score"] += 15
            
            return results
        except Exception as e:
            logger.error(f"Error in detect_timing_inconsistency: {e}", exc_info=True)
            return {"anomalies": ["error_processing_timing_data"], "score": 0, "flags": ["error"]}
    
    # NEW: Detect canvas tampering
    @staticmethod
    def detect_canvas_tampering(canvas_fingerprint, webgl_fingerprint, canvas_supported=True, webgl_supported=True):
        """
        Detect canvas/WebGL tampering techniques
        
        Args:
            canvas_fingerprint: Canvas fingerprint hash
            webgl_fingerprint: WebGL fingerprint hash
            canvas_supported: Whether canvas is reported as supported
            webgl_supported: Whether WebGL is reported as supported
            
        Returns:
            dict: Canvas tampering detection results
        """
        results = {"tampered": False, "methods": [], "score": 0}
        
        try:
            # Check for inconsistency between support and fingerprint
            if canvas_supported and (not canvas_fingerprint or canvas_fingerprint == "canvas_not_supported"):
                results["tampered"] = True
                results["methods"].append("canvas_inconsistent_support")
                results["score"] += 25
                
            if webgl_supported and (not webgl_fingerprint or webgl_fingerprint == "webgl_not_supported"):
                results["tampered"] = True
                results["methods"].append("webgl_inconsistent_support")
                results["score"] += 25
            
            # Check for known tampered fingerprints
            if canvas_fingerprint in ["", "undefined", "blocked", "canvas_not_supported", "canvas_blocked"]:
                results["tampered"] = True
                results["methods"].append("canvas_blocked")
                results["score"] += 30
                
            if webgl_fingerprint in ["", "undefined", "blocked", "webgl_not_supported", "webgl_blocked"]:
                results["tampered"] = True
                results["methods"].append("webgl_blocked")
                results["score"] += 30
            
            # Check for known fingerprinting extensions
            common_fake_hashes = [
                # Common hash patterns produced by canvas blockers
                "0000000000000000", 
                "ffffffffffffffff",
                "canvas_defender",
                "canvas_defender_not_available",
                "00000000000000000000000000000000",
                "12345678901234567890123456789012"
            ]
            
            for fake_hash in common_fake_hashes:
                if canvas_fingerprint and fake_hash in canvas_fingerprint.lower():
                    results["tampered"] = True
                    results["methods"].append(f"known_fake_canvas_{fake_hash}")
                    results["score"] += 40
                    break
                    
                if webgl_fingerprint and fake_hash in webgl_fingerprint.lower():
                    results["tampered"] = True
                    results["methods"].append(f"known_fake_webgl_{fake_hash}")
                    results["score"] += 40
                    break
            
            return results
        except Exception as e:
            logger.error(f"Error in detect_canvas_tampering: {e}")
            return {"tampered": False, "methods": ["error"], "score": 0}

    @staticmethod
    def detect_browser_os_inconsistency(user_agent):
        """
        Detect browser-OS inconsistencies in user agent
        
        Args:
            user_agent: User agent string
            
        Returns:
            dict: Inconsistency detection results
        """
        results = {"inconsistent": False, "details": [], "score": 0}
        
        try:
            user_agent_lower = user_agent.lower()
            
            for check in SpoofingDetector.BROWSER_OS_INCONSISTENCIES:
                browser = check["browser"]
                disallowed_os = check["disallowed_os"]
                
                if browser.lower() in user_agent_lower:
                    for os_name in disallowed_os:
                        if os_name.lower() in user_agent_lower:
                            results["inconsistent"] = True
                            results["details"].append(f"{browser} reported with incompatible OS {os_name}")
                            results["score"] += 30
            
            # Check for multiple browser engines (highly suspicious)
            browser_engines = []
            if "webkit" in user_agent_lower:
                browser_engines.append("webkit")
            if "gecko" in user_agent_lower and "like gecko" not in user_agent_lower:
                browser_engines.append("gecko")
            if "trident" in user_agent_lower:
                browser_engines.append("trident")
            if "presto" in user_agent_lower:
                browser_engines.append("presto")
            if "edgehtml" in user_agent_lower:
                browser_engines.append("edgehtml")
                
            # Multiple rendering engines is highly suspicious
            if len(browser_engines) > 1:
                results["inconsistent"] = True
                results["details"].append(f"Multiple browser engines detected: {', '.join(browser_engines)}")
                results["score"] += 50
            
            return results
        except Exception as e:
            logger.error(f"Error in detect_browser_os_inconsistency: {e}")
            return {"inconsistent": False, "details": ["error"], "score": 0}
    
    @staticmethod
    def detect_virtual_machine(hardware_info, canvas_fp=None, webgl_fp=None):
        """
        Enhanced VM/emulator detection
        
        Args:
            hardware_info: Dict with hardware information
            canvas_fp: Optional canvas fingerprint for analysis
            webgl_fp: Optional WebGL fingerprint for analysis
            
        Returns:
            dict: VM detection results
        """
        results = {"is_vm": False, "indicators": [], "score": 0}
        
        try:
            # Convert to string for easier searching
            hardware_str = json.dumps(hardware_info).lower() if hardware_info else ""
            
            # Check for common VM indicators in hardware
            vm_terms = [
                "vmware", "virtualbox", "qemu", "xen", "kvm", "hyperv", "hyper-v", 
                "parallels", "virtual", "vm ", "bhyve", "proxmox", "azure", "amazon", 
                "oracle vm", "virtual machine", "bochs", "uml", "container", "docker",
                "sandbox", "cuckoo", "vps", "emulated", "emulator"
            ]
            
            for term in vm_terms:
                if term in hardware_str:
                    results["is_vm"] = True
                    results["indicators"].append(f"vm_term_{term}")
                    results["score"] += 25
                    break
            
            # Check for VM patterns in canvas/WebGL fingerprints
            if canvas_fp and any(term in canvas_fp.lower() for term in vm_terms):
                results["is_vm"] = True
                results["indicators"].append("vm_canvas_fp")
                results["score"] += 30
                
            if webgl_fp and any(term in webgl_fp.lower() for term in vm_terms):
                results["is_vm"] = True
                results["indicators"].append("vm_webgl_fp")
                results["score"] += 35
            
            # Hardware-based detection
            if isinstance(hardware_info, dict):
                # Check GPU info
                gpu_info = str(hardware_info.get("gpu", "")).lower()
                if gpu_info and any(x in gpu_info for x in ["llvmpipe", "swiftshader", "mesa", "software", "virtual", "microsoft basic"]):
                    results["is_vm"] = True
                    results["indicators"].append("software_rendering")
                    results["score"] += 40
                
                # Check processor info
                processor = str(hardware_info.get("processor", "")).lower()
                if processor and ("virtual" in processor or "hypervisor" in processor):
                    results["is_vm"] = True
                    results["indicators"].append("virtual_cpu")
                    results["score"] += 35
                
                # Check for unusually low memory
                memory = hardware_info.get("memory", "")
                try:
                    memory_val = float(memory)
                    if 0 < memory_val < 2:  # Less than 2GB is suspicious for modern browsing
                        results["indicators"].append("low_memory")
                        results["score"] += 10
                except (ValueError, TypeError):
                    pass
                
                # Check for suspicious hardware configurations
                if "cores" in hardware_info:
                    cores = hardware_info.get("cores", 0)
                    try:
                        cores_val = int(cores)
                        if cores_val == 1:  # Single core is suspicious for modern systems
                            results["indicators"].append("single_core")
                            results["score"] += 15
                    except (ValueError, TypeError):
                        pass
            
            return results
        except Exception as e:
            logger.error(f"Error in detect_virtual_machine: {e}")
            return {"is_vm": False, "indicators": ["error"], "score": 0}
    
    @staticmethod
    def detect_automation_tools(browser_features, user_agent=None):
        """
        Detect browser automation tools, fingerprint blockers, and privacy extensions
        
        Args:
            browser_features: Dict with browser feature information
            user_agent: Optional user agent string
            
        Returns:
            dict: Detection results including automation and privacy tools
        """
        results = {
            "automated": False,
            "tools": [],
            "score": 0,
            "privacy_tools": [],
            "fingerprint_blocked": False
        }
        
        try:
            if not browser_features or not isinstance(browser_features, dict):
                return results
            
            # Check for webdriver attribute (strong indicator of automation)
            if browser_features.get("webdriver") is True:
                results["automated"] = True
                results["tools"].append("webdriver")
                results["score"] += 80
            
            # Extended list of automation properties to check
            automation_props = [
                # Selenium/webdriver properties
                "domAutomation", 
                "domAutomationController", 
                "_selenium", 
                "callSelenium", 
                "_Selenium_IDE_Recorder", 
                "__webdriver_script_fn",
                "__driver_evaluate",
                "__webdriver_evaluate",
                "__selenium_evaluate",
                "__webdriver_unwrapped",
                "selenium",
                "webdriver",
                
                # Puppeteer/Playwright
                "puppeteer",
                "playwright",
                "__playwright_",
                "__pw_",
                "__pw_metadata__",
                
                # Other automation tools
                "__nightmare",
                "_phantom",
                "phantom",
                "nightmare",
                "testcafe",
                "cypress",
                "protractor",
                "webdriverio",
                "taiko",
                "testcafe-testing-library"
            ]
            
            # Check for automation properties
            for prop in automation_props:
                if any(prop in key.lower() for key in browser_features.keys()):
                    results["automated"] = True
                    results["tools"].append(f"prop_{prop}")
                    results["score"] += 60
            
            # Check user agent for automation/fingerprint blocking signals
            if user_agent:
                user_agent_lower = user_agent.lower()
                
                # Detect privacy/fingerprint blocking extensions
                privacy_indicators = [
                    # Common privacy extensions
                    ("canvasblocker", 50, "CanvasBlocker"),
                    ("privacy badger", 40, "PrivacyBadger"),
                    ("privacy possum", 40, "PrivacyPossum"),
                    ("noscript", 60, "NoScript"),
                    ("scriptsafe", 60, "ScriptSafe"),
                    ("ublock", 30, "uBlock"),
                    ("umatrix", 40, "uMatrix"),
                    ("decentraleyes", 30, "Decentraleyes"),
                    ("disconnect", 30, "Disconnect"),
                    ("ghostery", 30, "Ghostery"),
                    ("adguard", 30, "AdGuard"),
                    ("adblock", 30, "AdBlock"),
                    ("adblockplus", 30, "AdBlockPlus"),
                    ("privacy settings", 40, "PrivacySettings"),
                    ("canvas fingerprint", 70, "CanvasFingerprintBlock"),
                    ("fingerprint spoof", 80, "FingerprintSpoof"),
                    ("chameleon", 70, "ChameleonExtension"),
                    ("random user agent", 60, "RandomUserAgent"),
                    ("user agent switcher", 60, "UserAgentSwitcher"),
                    ("trace", 50, "TraceExtension"),
                    ("webrtc leak prevent", 50, "WebRTCLeakPrevent")
                ]
                
                # Check for privacy/blocking extensions in user agent
                for indicator, score, tool_name in privacy_indicators:
                    if indicator in user_agent_lower:
                        results["privacy_tools"].append(tool_name)
                        results["score"] += score
                        results["fingerprint_blocked"] = True
                
                # Check for known automation tools in user agent
                for tool in SpoofingDetector.HEADLESS_INDICATORS:
                    if tool.lower() in user_agent_lower:
                        results["automated"] = True
                        results["tools"].append(f"ua_{tool}")
                        results["score"] += 70
            
            # Detect fingerprint blocking through feature detection
            if isinstance(browser_features, dict):
                # Check for blocked or modified WebGL
                if browser_features.get("webgl_vendor") in ["Google Inc.", "Mesa OffScreen"] or \
                   "webgl" in browser_features and not browser_features.get("webgl"):
                    results["fingerprint_blocked"] = True
                    results["privacy_tools"].append("WebGL_Blocked")
                    results["score"] += 50
                
                # Check for blocked canvas
                if "canvas" in browser_features and not browser_features.get("canvas"):
                    results["fingerprint_blocked"] = True
                    results["privacy_tools"].append("Canvas_Blocked")
                    results["score"] += 60
                
                # Check for blocked audio context
                if "audio" in browser_features and not browser_features.get("audio"):
                    results["fingerprint_blocked"] = True
                    results["privacy_tools"].append("AudioContext_Blocked")
                    results["score"] += 40
                
                # Check for blocked fonts
                if "fonts" in browser_features and not browser_features.get("fonts"):
                    results["fingerprint_blocked"] = True
                    results["privacy_tools"].append("Fonts_Blocked")
                    results["score"] += 40
                
                # Check for missing or modified WebRTC
                if "rtc_peer_connection" in browser_features and not browser_features.get("rtc_peer_connection"):
                    results["fingerprint_blocked"] = True
                    results["privacy_tools"].append("WebRTC_Blocked")
                    results["score"] += 50
                
                # Check for missing features that should be present in real browsers
                required_features = ["localStorage", "sessionStorage", "indexedDB", "cookies"]
                for feature in required_features:
                    if feature in browser_features and not browser_features.get(feature):
                        results["privacy_tools"].append(f"{feature}_Blocked")
                        results["score"] += 30
            
            # Check for plugins count (headless browsers typically have 0, privacy browsers may have few)
            if "plugins" in browser_features:
                plugins_count = browser_features.get("plugins", 0)
                if plugins_count == 0:
                    results["tools"].append("no_plugins")
                    results["score"] += 25
                    
                    # If no plugins but browser claims to be a normal browser, it's suspicious
                    if "chrome" in (user_agent or "").lower() and plugins_count == 0:
                        results["score"] += 30
                        results["fingerprint_blocked"] = True
                        results["privacy_tools"].append("Plugins_Blocked")
            
            # If multiple privacy tools detected, increase score
            if len(results["privacy_tools"]) > 1:
                results["score"] += 20 * len(results["privacy_tools"])
            
            # If fingerprint blocking is detected but no privacy tools were identified
            if results["fingerprint_blocked"] and not results["privacy_tools"]:
                results["privacy_tools"].append("Unknown_Fingerprint_Blocker")
                results["score"] += 60
            
            return results
        except Exception as e:
            logger.error(f"Error in detect_automation_tools: {e}")
            return {
                "automated": False,
                "tools": ["error"],
                "privacy_tools": ["error"],
                "fingerprint_blocked": False,
                "score": 0
            }

# Enhanced entry point that combines all detection methods
@memcached_cached("spoofing", 300)  # Cache results for 5 minutes
def detect_spoofing(fingerprint_data, ip_address=None):
    """
    Enhanced spoofing detection that combines multiple methods including
    detection of fingerprint blocking and privacy extensions.
    
    Args:
        fingerprint_data: Dict containing fingerprint data including:
            - user_agent: Browser user agent string
            - browser_features: Dict of browser capabilities and features
            - hardware_info: Information about client hardware
            - canvas_fingerprint: Canvas fingerprint hash
            - webgl_fingerprint: WebGL fingerprint hash
            - audio_fingerprint: Audio fingerprint hash
            - timing_info: Browser timing information
            - headers: HTTP headers from the request
        ip_address: Optional IP address for additional context and rate limiting
        
    Returns:
        dict: Comprehensive spoofing detection results with the following structure:
            {
                "spoofing_detected": bool,  # True if spoofing is detected
                "methods": list[str],      # List of detected spoofing methods
                "details": dict,           # Detailed information about detections
                "score": int,              # 0-100 risk score
                "fingerprint_blocked": bool,  # True if fingerprint blocking detected
                "privacy_tools": list[str]  # List of detected privacy tools/extensions
            }
    """
    results = {
        "spoofing_detected": False,
        "methods": [],
        "details": {},
        "score": 0,  # 0-100 score where higher means more likely spoofing
        "fingerprint_blocked": False,
        "privacy_tools": []
    }
    
    try:
        detector = SpoofingDetector()
        total_score = 0
        
        # Extract components for analysis
        user_agent = fingerprint_data.get("user_agent", "")
        browser_features = fingerprint_data.get("browser_features", {})
        hardware_info = fingerprint_data.get("hardware_info", {})
        canvas_fp = fingerprint_data.get("canvas_fingerprint", "")
        webgl_fp = fingerprint_data.get("webgl_fingerprint", "")
        audio_fp = fingerprint_data.get("audio_fingerprint", "")
        timing_fingerprint = fingerprint_data.get("timing_fingerprint", "")
        
        # 1. Check browser-OS inconsistency
        browser_os_result = detector.detect_browser_os_inconsistency(user_agent)
        if browser_os_result["inconsistent"]:
            results["methods"].append("browser_os_inconsistency")
            results["details"]["browser_os"] = browser_os_result
            total_score += browser_os_result["score"]
        
        # 2. Check for canvas/WebGL tampering
        canvas_tampering = detector.detect_canvas_tampering(
            canvas_fp, 
            webgl_fp,
            browser_features.get("canvas", True),
            browser_features.get("webGL", True)
        )
        if canvas_tampering["tampered"]:
            results["methods"].append("canvas_tampering")
            results["details"]["canvas_tampering"] = canvas_tampering
            total_score += canvas_tampering["score"]
        
        # 3. Check for automation tools and fingerprint blocking
        automation_result = detector.detect_automation_tools(browser_features, user_agent)
        if automation_result["automated"] or automation_result["fingerprint_blocked"]:
            if automation_result["automated"]:
                results["methods"].append("automation_tools")
            if automation_result["fingerprint_blocked"]:
                results["methods"].append("fingerprint_blocking_detected")
                results["fingerprint_blocked"] = True
                results["privacy_tools"] = automation_result.get("privacy_tools", [])
            
            results["details"]["automation"] = automation_result
            total_score += automation_result["score"]
            
            # If fingerprint blocking is detected, increase the score
            if automation_result["fingerprint_blocked"]:
                total_score += 30  # Additional penalty for fingerprint blocking
        
        # 4. Check for VM/emulator
        vm_result = detector.detect_virtual_machine(hardware_info, canvas_fp, webgl_fp)
        if vm_result["is_vm"]:
            results["methods"].append("virtual_machine")
            results["details"]["vm"] = vm_result
            total_score += vm_result["score"]
        
        # 5. Check for timing inconsistency
        timing_result = detector.detect_timing_inconsistency(
            fingerprint_data.get("timing_info", {}),
            fingerprint_data.get("headers", {})
        )
        if timing_result["anomalies"]:
            results["methods"].append("timing_inconsistency")
            results["details"]["timing"] = timing_result
            total_score += timing_result["score"]
        
        # Calculate final score (cap at 100)
        final_score = min(100, total_score)
        results["score"] = final_score
        
        # Determine if spoofing is detected based on score threshold
        # Lower threshold if fingerprint blocking is detected
        threshold = 30 if results.get("fingerprint_blocked", False) else 40
        results["spoofing_detected"] = final_score >= threshold
        
        # If fingerprint blocking is detected, always flag as spoofing
        if results.get("fingerprint_blocked", False) and final_score >= 20:
            results["spoofing_detected"] = True
        
        # Log spoofing attempts for analysis
        if results["spoofing_detected"]:
            log_message = f"Spoofing detected with score {final_score}: {results['methods']}"
            if results.get("fingerprint_blocked", False):
                log_message += f" | Fingerprint blocking detected with tools: {results.get('privacy_tools', [])}"
            
            logger.warning(log_message)
            
            # Log more details if score is high or fingerprint blocking is detected
            if final_score >= 60 or results.get("fingerprint_blocked", False):
                logger.warning(f"Suspicious activity details: {json.dumps(results['details'], indent=2)}")
        
        return results
    except Exception as e:
        logger.error(f"Error in detect_spoofing: {e}")
        return {"spoofing_detected": False, "methods": ["error"], "details": {"error": str(e)}, "score": 0}