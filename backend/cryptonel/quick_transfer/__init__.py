from flask import Flask

def init_app(app: Flask):
    """
    Initialize Quick Transfer module
    """
    # Use only routes.py for all API endpoints
    from .routes import init_routes
    
    # Register routes
    init_routes(app)
    
    return app 