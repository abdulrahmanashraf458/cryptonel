"""
Error Handlers System - Manages application error handlers
Provides consistent error responses for API and HTML requests
"""

import logging
from flask import Flask, jsonify, request, send_from_directory, current_app


def configure_error_handlers(app: Flask) -> None:
    """
    Configure all error handlers for the application
    
    Args:
        app: Flask application instance
    """
    security_logger = logging.getLogger('security')
    error_logger = logging.getLogger('error')
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 Not Found errors"""
        if request.path.startswith('/api/'):
            return jsonify({"error": "Resource not found"}), 404
        return send_from_directory(app.static_folder, 'index.html')
    
    @app.errorhandler(403)
    def forbidden(error):
        """Handle 403 Forbidden errors"""
        security_logger.warning(f"Forbidden access attempt: {request.remote_addr} - {request.path}")
        if request.path.startswith('/api/'):
            return jsonify({"error": "Access forbidden"}), 403
        return send_from_directory(app.static_folder, 'index.html')
    
    @app.errorhandler(500)
    def server_error(error):
        """Handle 500 Internal Server Error errors"""
        error_logger.error(f"Internal server error: {error}", exc_info=True)
        if request.path.startswith('/api/'):
            return jsonify({"error": "Internal server error"}), 500
        return send_from_directory(app.static_folder, 'index.html')
    
    @app.errorhandler(429)
    def too_many_requests(error):
        """Handle 429 Too Many Requests errors (rate limiting)"""
        security_logger.warning(f"Rate limit exceeded: {request.remote_addr} - {request.path}")
        if request.path.startswith('/api/'):
            return jsonify({
                "error": "Too many requests",
                "message": "Rate limit exceeded. Please try again later."
            }), 429
        return send_from_directory(app.static_folder, 'index.html')
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        """Handle 405 Method Not Allowed errors"""
        security_logger.warning(f"Method not allowed: {request.method} - {request.remote_addr} - {request.path}")
        if request.path.startswith('/api/'):
            return jsonify({
                "error": "Method not allowed",
                "message": f"The method {request.method} is not allowed for this resource."
            }), 405
        return send_from_directory(app.static_folder, 'index.html')
    
    @app.errorhandler(413)
    def request_entity_too_large(error):
        """Handle 413 Request Entity Too Large errors"""
        security_logger.warning(f"Request too large: {request.remote_addr} - {request.path}")
        if request.path.startswith('/api/'):
            return jsonify({
                "error": "Request too large",
                "message": "The request data exceeds the maximum allowed size."
            }), 413
        return send_from_directory(app.static_folder, 'index.html')
    
    # Custom error handler for CSRF errors
    @app.errorhandler(400)
    def bad_request(error):
        """Handle 400 Bad Request errors, including CSRF errors"""
        if 'CSRF' in str(error):
            security_logger.warning(f"CSRF validation failed: {request.remote_addr} - {request.path}")
            if request.path.startswith('/api/'):
                return jsonify({
                    "error": "CSRF validation failed",
                    "message": "Invalid or missing CSRF token."
                }), 400
        else:
            error_logger.warning(f"Bad request: {request.remote_addr} - {request.path} - {error}")
            if request.path.startswith('/api/'):
                return jsonify({
                    "error": "Bad request",
                    "message": "The request could not be understood by the server."
                }), 400
        return send_from_directory(app.static_folder, 'index.html') 