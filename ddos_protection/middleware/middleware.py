#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DDoS Protection System - Flask Middleware
----------------------------------------
Middleware for integrating DDoS protection with Flask applications
"""

import logging
import json
import time
import traceback
import asyncio
from typing import Dict, Any, Optional, Callable, Tuple
from functools import wraps
import os
import hashlib
from flask import abort, request

# Configure logging
logger = logging.getLogger('ddos_protection.middleware')

# Define a local sync_wrapper function to avoid circular imports
def local_sync_wrapper(async_function):
    """Convert an async function to sync function"""
    def sync_function(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(async_function(*args, **kwargs))
        finally:
            loop.close()
    return sync_function

def get_client_ip_from_request(request):
    """
    Get the real client IP from request, handling proxies correctly.
    
    Args:
        request: Flask request object
        
    Returns:
        str: The client IP address
    """
    # First try the X-Real-IP header (set by nginx)
    if request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    
    # Then try X-Forwarded-For header (set by many proxies)
    elif request.headers.get('X-Forwarded-For'):
        # X-Forwarded-For can be a comma-separated list if multiple proxies are used
        # The client IP is the first one in the list
        x_forwarded_for = request.headers.get('X-Forwarded-For')
        return x_forwarded_for.split(',')[0].strip()
    
    # Otherwise use the remote address
    else:
        return request.remote_addr

class DDoSMiddleware:
    """
    Middleware for integrating DDoS protection with Flask
    """
    
    def __init__(self, app=None, ddos_system=None):
        """
        Initialize middleware with Flask app and DDoS protection system
        
        Args:
            app: Flask application
            ddos_system: DDoS protection system instance
        """
        self.app = app
        self.ddos_system = ddos_system
        
        if app and ddos_system:
            self.init_app(app, ddos_system)
    
    def init_app(self, app, ddos_system):
        """
        Initialize the middleware with a Flask app and DDoS system
        
        Args:
            app: Flask application
            ddos_system: DDoS protection system instance
        """
        self.app = app
        self.ddos_system = ddos_system
        
        # Register challenge routes
        self._register_challenge_routes(app)
        
        # Register middleware
        @app.before_request
        def ddos_protection_middleware():
            """
            Main middleware function for DDoS protection.
            This runs before each request to check if it should be allowed.
            """
            try:
                # Skip protection for challenge verification endpoints
                if request.path in ['/ddos-challenge', '/verify-challenge']:
                    return None
                
                # Get real IP address
                real_ip = get_client_ip_from_request(request)
                
                # Get device fingerprint
                device_fingerprint = request.headers.get('X-Device-Fingerprint')
                
                # Process request through DDoS protection system
                if self.ddos_system:
                    # Use monitor system for direct synchronous processing
                    if hasattr(self.ddos_system, 'monitor') and self.ddos_system.monitor:
                        allowed = self.ddos_system.monitor.process_request_sync(
                            ip=real_ip,
                            path=request.path,
                            device_fingerprint=device_fingerprint,
                            user_agent=request.headers.get('User-Agent'),
                            request_size=len(request.get_data() if request.is_json else b''),
                            method=request.method
                        )
                        
                        if not allowed:
                            # Log the blocked request
                            logging.warning(f"Blocked request from {real_ip} to {request.path} ({request.method})")
                            
                            # Return challenge or block
                            if device_fingerprint:
                                # User has JS enabled, show challenge
                                challenge_data = self._generate_challenge_data(real_ip, request.headers.get('User-Agent'))
                                return self._show_challenge(challenge_data, request.path)
                            else:
                                # No fingerprint, hard block
                                return abort(403, description="Access denied by DDoS protection")
                    else:
                        # Fallback to basic check
                        if self.ddos_system.ban_manager.is_banned(real_ip):
                            logging.warning(f"Blocked banned IP {real_ip} at middleware")
                            return abort(403, description="Forbidden: IP is banned")
            except Exception as e:
                # Log the error but allow the request to proceed
                logging.error(f"Error in DDoS protection middleware: {e}")
                logging.debug(traceback.format_exc())
            
            return None
    
    def _register_challenge_routes(self, app):
        """
        Register routes for the challenge page and verification
        
        Args:
            app: Flask application
        """
        # Import Flask dependencies
        from flask import request, jsonify, make_response, redirect, render_template_string, session
        
        @app.route('/ddos-challenge', methods=['GET'])
        def ddos_challenge_page():
            """Challenge page for suspected DDoS clients"""
            client_ip = getattr(request, 'real_ip', request.remote_addr)
            
            # Get challenge data from session
            challenge_data = session.get('challenge_data')
            redirect_path = session.get('challenge_redirect', '/')
            
            if not challenge_data:
                # No challenge data, create a new one
                try:
                    from ddos_protection.core.mitigator import ChallengeManager
                    
                    challenge_manager = self.ddos_system.mitigator.challenge_manager
                    challenge_data = challenge_manager.create_challenge(
                        client_ip, 
                        request.headers.get("User-Agent", "")
                    )
                    
                    if not challenge_data:
                        # Failed to create challenge, just block
                        return jsonify({"error": "Access denied"}), 403
                        
                    # Store in session
                    session['challenge_data'] = challenge_data
                except Exception as e:
                    logger.error(f"Error creating challenge: {e}")
                    return jsonify({"error": "Internal server error"}), 500
            
            # Create a page with JavaScript challenge
            html = self._generate_challenge_html(challenge_data, redirect_path)
            
            return render_template_string(html)
        
        @app.route('/verify-challenge', methods=['POST'])
        def verify_challenge():
            """Verify challenge answer from client"""
            if not request.is_json:
                return jsonify({"success": False, "message": "Invalid request format"}), 400
            
            client_ip = getattr(request, 'real_ip', request.remote_addr)
            data = request.json
            
            token = data.get('token')
            answer = data.get('answer')
            
            if not token or not answer:
                return jsonify({"success": False, "message": "Missing token or answer"}), 400
            
            try:
                # Verify the challenge
                challenge_manager = self.ddos_system.mitigator.challenge_manager
                is_valid = challenge_manager.verify_challenge(token, answer)
                
                if is_valid:
                    # Challenge solved - whitelist the IP temporarily
                    try:
                        # Mark this IP as trusted
                        from ddos_protection.storage import ban_manager
                        from ddos_protection.storage import device_manager
                        
                        # Add to trusted list temporarily
                        # Use local_sync_wrapper since add_trusted_ip is an async method
                        local_sync_wrapper(self.ddos_system.mitigator.add_trusted_ip)(client_ip, "Passed CAPTCHA challenge")
                        
                        # Update device fingerprint if available
                        device_fingerprint = request.headers.get('X-Device-Fingerprint') or session.get('device_fingerprint')
                        
                        if device_fingerprint:
                            # If we have device fingerprint, mark this device as verified
                            device_manager.update_device_record(
                                device_fingerprint,
                                client_ip,
                                request.headers.get('X-Browser-Fingerprint'),
                                request.user_agent.string if request.user_agent else None
                            )
                            
                            if hasattr(device_manager, 'mark_device_as_verified'):
                                device_manager.mark_device_as_verified(device_fingerprint)
                        
                        # Clear challenge from session
                        if 'challenge_data' in session:
                            del session['challenge_data']
                        
                        # Redirect to original page
                        redirect_path = session.pop('challenge_redirect', '/')
                        
                        return jsonify({
                            "success": True, 
                            "message": "Challenge verified", 
                            "redirect": redirect_path
                        })
                    except Exception as e:
                        logger.error(f"Error whitelisting client after challenge: {e}")
                
                return jsonify({"success": is_valid, "message": "Challenge verification failed"}), 200
            except Exception as e:
                logger.error(f"Error verifying challenge: {e}")
                logger.error(traceback.format_exc())
                return jsonify({"success": False, "message": "Server error"}), 500
    
    def _generate_challenge_html(self, challenge_data, redirect_path):
        """
        Generate the HTML for the challenge page
        
        Args:
            challenge_data: Challenge data
            redirect_path: Path to redirect after challenge
            
        Returns:
            str: HTML for the challenge page
        """
        html = f"""<!DOCTYPE html>
        <html>
        <head>
            <title>Security Check</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: #f5f5f5;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    direction: rtl;
                }}
                .challenge-box {{
                    background-color: #fff;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
                    padding: 30px;
                    max-width: 500px;
                    text-align: center;
                }}
                h1 {{
                    color: #333;
                    font-size: 24px;
                    margin-bottom: 20px;
                }}
                p {{
                    color: #666;
                    margin-bottom: 20px;
                    line-height: 1.5;
                }}
                .spinner {{
                    border: 4px solid #f3f3f3;
                    border-top: 4px solid #3498db;
                    border-radius: 50%;
                    width: 40px;
                    height: 40px;
                    animation: spin 2s linear infinite;
                    margin: 0 auto 20px;
                }}
                @keyframes spin {{
                    0% {{ transform: rotate(0deg); }}
                    100% {{ transform: rotate(360deg); }}
                }}
                .progress {{
                    height: 4px;
                    background: #f3f3f3;
                    border-radius: 2px;
                    margin-bottom: 20px;
                    overflow: hidden;
                }}
                .progress-bar {{
                    height: 100%;
                    width: 0%;
                    background: #3498db;
                    border-radius: 2px;
                    transition: width 0.5s;
                }}
                .hidden {{
                    display: none;
                }}
            </style>
        </head>
        <body>
            <div class="challenge-box">
                <h1>التحقق الأمني</h1>
                <div class="spinner" id="spinner"></div>
                <div class="progress">
                    <div class="progress-bar" id="progress"></div>
                </div>
                <p>الرجاء الانتظار بينما نتحقق من متصفحك...</p>
                <p id="countdown" class="hidden">سيتم إعادة توجيهك في غضون <span id="seconds">5</span> ثوان...</p>
                <p id="error" class="hidden" style="color: red;">فشل التحقق من المتصفح. يرجى تحديث الصفحة للمحاولة مرة أخرى.</p>
                
                <script>
                    // Challenge data
                    const token = "{challenge_data.get('token')}";
                    const challenge = `{challenge_data.get('challenge')}`;
                    
                    // Execute the challenge
                    function solveChallenge() {{
                        try {{
                            // The challenge is executed in a new Function to isolate its scope
                            const challengeFunc = new Function(challenge);
                            const answer = challengeFunc();
                            return answer;
                        }} catch (e) {{
                            console.error("Challenge execution error:", e);
                            return null;
                        }}
                    }}
                    
                    // Progress bar animation
                    function updateProgress(percent) {{
                        document.getElementById('progress').style.width = percent + '%';
                    }}
                    
                    // Submit the challenge answer
                    function submitAnswer(answer) {{
                        fetch('/verify-challenge', {{
                            method: 'POST',
                            headers: {{
                                'Content-Type': 'application/json',
                            }},
                            body: JSON.stringify({{
                                token: token,
                                answer: answer
                            }})
                        }})
                        .then(response => response.json())
                        .then(data => {{
                            if (data.success) {{
                                // Success - show countdown and redirect
                                document.getElementById('spinner').classList.add('hidden');
                                document.getElementById('countdown').classList.remove('hidden');
                                
                                // Start countdown
                                let seconds = 5;
                                document.getElementById('seconds').textContent = seconds;
                                
                                const interval = setInterval(() => {{
                                    seconds--;
                                    document.getElementById('seconds').textContent = seconds;
                                    
                                    if (seconds <= 0) {{
                                        clearInterval(interval);
                                        // Redirect back to original page
                                        window.location.href = data.redirect || '{redirect_path}';
                                    }}
                                }}, 1000);
                            }} else {{
                                // Failed verification
                                document.getElementById('spinner').classList.add('hidden');
                                document.getElementById('error').classList.remove('hidden');
                            }}
                        }})
                        .catch(error => {{
                            console.error('Error:', error);
                            document.getElementById('spinner').classList.add('hidden');
                            document.getElementById('error').classList.remove('hidden');
                        }});
                    }}
                    
                    // Main function
                    function main() {{
                        // Update progress animation
                        let progress = 0;
                        const progressInterval = setInterval(() => {{
                            progress += 5;
                            updateProgress(Math.min(progress, 100));
                            
                            if (progress >= 100) {{
                                clearInterval(progressInterval);
                            }}
                        }}, 200);
                        
                        // Execute the challenge
                        setTimeout(() => {{
                            const answer = solveChallenge();
                            if (answer !== null) {{
                                submitAnswer(answer);
                            }} else {{
                                // Challenge execution failed
                                document.getElementById('spinner').classList.add('hidden');
                                document.getElementById('error').classList.remove('hidden');
                            }}
                        }}, 1500);
                    }}
                    
                    // Start the process when page loads
                    window.onload = main;
                </script>
            </div>
        </body>
        </html>
        """
        
        return html

    def _generate_challenge_data(self, ip, user_agent):
        """Generate challenge data for client verification"""
        try:
            if hasattr(self.ddos_system, 'mitigator') and hasattr(self.ddos_system.mitigator, 'challenge_manager'):
                challenge_manager = self.ddos_system.mitigator.challenge_manager
                return challenge_manager.create_challenge(ip, user_agent)
            else:
                # Simple fallback challenge if challenge manager not available
                token = hashlib.sha256(f"{ip}-{time.time()}".encode()).hexdigest()
                challenge = "return 'verified';"  # Simple JS challenge
                return {'token': token, 'challenge': challenge}
        except Exception as e:
            logging.error(f"Error generating challenge data: {e}")
            return None
            
    def _show_challenge(self, challenge_data, redirect_path):
        """Show the challenge page to the client"""
        from flask import render_template_string, session
        
        if not challenge_data:
            # No challenge data available, just block
            return abort(403, description="Access denied by DDoS protection")
            
        # Store challenge data and redirect path in session
        session['challenge_data'] = challenge_data
        session['challenge_redirect'] = redirect_path
        
        # Generate HTML
        html = self._generate_challenge_html(challenge_data, redirect_path)
        
        return render_template_string(html)

# Create a helper function to initialize the middleware
def init_app(app, ddos_system):
    """
    Initialize DDoS middleware with Flask app
    
    Args:
        app: Flask application
        ddos_system: DDoS protection system
    """
    middleware = DDoSMiddleware(app, ddos_system)
    
    # Store middleware in app for reference
    app.ddos_middleware = middleware
    
    return middleware 