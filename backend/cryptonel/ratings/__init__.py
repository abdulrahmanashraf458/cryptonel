from backend.cryptonel.ratings.ratings_api import init_app as ratings_init
from backend.cryptonel.ratings.profile_api import init_app as profile_init
from backend.cryptonel.ratings.premium.settings_api import init_app as settings_init
from backend.cryptonel.ratings.premium.appearance_api import init_app as appearance_init
from backend.cryptonel.ratings.public_profile_api import init_app as public_profile_init

def init_app(app):
    """Initialize all rating modules"""
    # Initialize the ratings API
    ratings_init(app)
    
    # Initialize profile API
    profile_init(app)
    
    # Initialize settings API
    settings_init(app)
    
    # Initialize appearance API
    appearance_init(app)
    
    # Initialize public profile API
    public_profile_init(app)
    
    return app 