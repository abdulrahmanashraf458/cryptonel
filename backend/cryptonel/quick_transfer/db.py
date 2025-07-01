from flask import current_app, g
import pymongo
import os
import logging
import datetime

# Setup logging
logger = logging.getLogger(__name__)

def get_db():
    """
    Get database connection from current application context
    """
    if 'db' not in g:
        # Get MongoDB connection details directly from environment variables
        mongo_uri = os.environ.get('DATABASE_URL')
        
        # Use the correct database name
        mongo_db_name = 'cryptonel_wallet'
        
        # Create MongoDB client and get database
        client = pymongo.MongoClient(mongo_uri)
        g.db = client[mongo_db_name]
        
        # Ensure quick_transfer_contacts collection exists with proper validation
        if 'quick_transfer_contacts' not in g.db.list_collection_names():
            try:
                # Create collection with validation schema
                g.db.create_collection('quick_transfer_contacts')
                logger.info("Created quick_transfer_contacts collection in cryptonel_wallet database")
                
                # Create index on user_id for faster lookups
                try:
                    # Check if any user_id index already exists
                    existing_indexes = [idx.get('name') for idx in g.db.quick_transfer_contacts.list_indexes()]
                    if not any('user_id' in idx_name for idx_name in existing_indexes):
                        g.db.quick_transfer_contacts.create_index("user_id", unique=True, name="quick_transfer_user_id_idx")
                        logger.info("Created index on user_id in quick_transfer_contacts collection")
                    else:
                        logger.info("User ID index already exists in quick_transfer_contacts collection, skipping creation")
                except Exception as e:
                    logger.warning(f"Error creating index for quick_transfer_contacts: {e}")
                    # Continue even if index creation fails
                
                # Add validation schema
                validation = {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["user_id", "contacts"],
                        "properties": {
                            "user_id": {
                                "bsonType": "string",
                                "description": "User ID must be a string and is required"
                            },
                            "contacts": {
                                "bsonType": "array",
                                "description": "Contacts must be an array and is required",
                                "items": {
                                    "bsonType": "object",
                                    "required": ["id", "user_id", "username", "private_address"],
                                    "properties": {
                                        "id": {
                                            "bsonType": "string",
                                            "description": "Contact ID must be a string and is required"
                                        },
                                        "user_id": {
                                            "bsonType": "string",
                                            "description": "Contact user ID must be a string and is required"
                                        },
                                        "username": {
                                            "bsonType": "string",
                                            "description": "Contact username must be a string and is required"
                                        },
                                        "private_address": {
                                            "bsonType": "string",
                                            "description": "Contact private address must be a string and is required"
                                        },
                                        "added_at": {
                                            "bsonType": ["date", "string", "null"],
                                            "description": "Date when contact was added (optional)"
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                
                # Apply validation schema to collection
                g.db.command({
                    "collMod": "quick_transfer_contacts",
                    "validator": validation
                })
                logger.info("Applied validation schema to quick_transfer_contacts collection")
                
            except Exception as e:
                logger.error(f"Error creating quick_transfer_contacts collection: {str(e)}")
                # Continue even if validation schema fails - we can still use the collection
        
        # Update existing contacts to add added_at field if missing
        try:
            contacts_docs = g.db.quick_transfer_contacts.find({})
            for doc in contacts_docs:
                updated = False
                for contact in doc.get("contacts", []):
                    if "added_at" not in contact:
                        contact["added_at"] = datetime.datetime.utcnow()
                        updated = True
                
                if updated:
                    g.db.quick_transfer_contacts.update_one(
                        {"_id": doc["_id"]},
                        {"$set": {"contacts": doc["contacts"]}}
                    )
                    logger.info(f"Updated contacts for user {doc.get('user_id')} to add added_at field")
        except Exception as e:
            logger.error(f"Error updating existing contacts with added_at field: {str(e)}")
            
    return g.db

def close_db(e=None):
    """
    Close database connection
    """
    db = g.pop('db', None)
    
    if db is not None:
        # If using PyMongo client, close the connection
        if hasattr(db, 'client'):
            db.client.close() 