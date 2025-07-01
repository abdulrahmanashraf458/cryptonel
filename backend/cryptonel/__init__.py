# استيراد الوحدات اللازمة
from .quick_transfer import init_app as init_quicktransfer
from flask import Flask

def init_app(app: Flask):
    """
    Initialize all Cryptonel modules and register routes
    """
    # Initialize quicktransfer
    init_quicktransfer(app)
    
    # Add any additional initialization as needed
    
    return app 