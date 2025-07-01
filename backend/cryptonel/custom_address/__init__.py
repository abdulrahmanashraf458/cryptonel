from flask import Flask
import pymongo
import logging
from .routes import users_collection

logger = logging.getLogger(__name__)

def init_app(app: Flask):
    """
    Initialize Custom Address module for Cryptonel Wallet
    
    This module allows premium users to customize their private address
    """
    # Ensure unique, sparse index on private_address to prevent race conditions
    # A sparse index only includes entries for documents that have the indexed field.
    if users_collection is not None:
        try:
            index_name = "private_address_unique_idx"
            existing_indexes = users_collection.index_information()
            
            if index_name not in existing_indexes:
                users_collection.create_index(
                    [("private_address", pymongo.ASCENDING)],
                    name=index_name,
                    unique=True,
                    sparse=True
                )
                logger.info("Successfully created unique, sparse index on 'private_address'")
        except pymongo.errors.OperationFailure as e:
            logger.warning(f"Could not create unique index on 'private_address' (may already exist with different options): {e}")
        except Exception as e:
            logger.error(f"Error creating unique index on 'private_address': {e}")

    from .routes import register_routes
    
    # Register routes
    register_routes(app)
    
    return app 