import os
import sys
from dotenv import load_dotenv

# Print the current working directory
print(f"Current working directory: {os.getcwd()}")

# Try to load from secure_config directory
secure_dotenv_path = os.path.join(os.path.dirname(__file__), 'secure_config', 'clyne.env')
print(f"Looking for env file at: {secure_dotenv_path}")
print(f"File exists: {os.path.exists(secure_dotenv_path)}")

if os.path.exists(secure_dotenv_path):
    print(f"Loading from {secure_dotenv_path}")
    load_dotenv(secure_dotenv_path, override=True)
    print("Environment loaded!")
else:
    print(f"Error: {secure_dotenv_path} not found")

# Get the database URL
database_url = os.environ.get('DATABASE_URL')
print(f"DATABASE_URL: {database_url}")

# Print all environment variables
print("\nAll environment variables:")
for key, value in os.environ.items():
    if 'DATABASE' in key or 'MONGO' in key:
        print(f"{key}: {value}")

# Additional check - see if the old MongoDB connection string is being used directly
import pymongo
try:
    # Try connecting with the environment variable
    if database_url:
        print("\nTesting connection with DATABASE_URL...")
        client = pymongo.MongoClient(database_url)
        db = client.admin
        # Issue the ping command to verify connectivity
        db.command('ping')
        print("Connection successful with DATABASE_URL!")
except Exception as e:
    print(f"Connection error with DATABASE_URL: {e}")

# Try the old connection string directly to see if it's hard-coded somewhere
try:
    old_url = "mongodb://clyne:clyneisbetterthanprobot@data.clyne.cc:27017"
    print("\nTesting connection with old URL...")
    client = pymongo.MongoClient(old_url)
    db = client.admin
    # Issue the ping command to verify connectivity
    db.command('ping')
    print("Warning: Connection with old URL still works. It may be hard-coded somewhere.")
except Exception as e:
    print(f"Connection error with old URL (expected): {e}") 