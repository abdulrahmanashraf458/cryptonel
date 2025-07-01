#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Redis Manager
----------------------------
This file sets up and runs Redis automatically before starting the website.
It is called from the server.py file
"""

import os
import sys
import time
import socket
import subprocess
import logging
import redis
import json
import random
import string
import atexit

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("redis_manager.log")
    ]
)
logger = logging.getLogger("redis_manager")

# Configuration variables
DEFAULT_REDIS_HOST = "localhost"
DEFAULT_REDIS_PORT = 6379
DEFAULT_REDIS_DB = 0
ENV_FILE_PATH = os.path.join(os.path.dirname(__file__), 'clyne.env')

# Default password - will be generated randomly if not set
DEFAULT_REDIS_PASSWORD = None

def generate_secure_password(length=16):
    """Generate a strong random password"""
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(random.choice(characters) for _ in range(length))
    logger.info(f"Generated secure random password (not shown here)")
    return password

def read_env_file():
    """Read settings from environment file"""
    if os.path.exists(ENV_FILE_PATH):
        env_vars = {}
        try:
            with open(ENV_FILE_PATH, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip().strip("'").strip('"')
            return env_vars
        except UnicodeDecodeError:
            # محاولة قراءة الملف باستخدام ترميزات أخرى إذا فشل UTF-8
            try:
                with open(ENV_FILE_PATH, 'r', encoding='cp1256') as f:  # ترميز عربي شائع
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            key, value = line.split('=', 1)
                            env_vars[key.strip()] = value.strip().strip("'").strip('"')
                return env_vars
            except Exception as e2:
                logger.error(f"Error reading environment file with alternative encoding: {e2}")
        except Exception as e:
            logger.error(f"Error reading environment file: {e}")
    return {}

def update_env_file(env_vars):
    """Update environment file with new settings"""
    try:
        # Read existing file
        existing_lines = []
        if os.path.exists(ENV_FILE_PATH):
            try:
                with open(ENV_FILE_PATH, 'r', encoding='utf-8') as f:
                    existing_lines = f.readlines()
            except UnicodeDecodeError:
                # محاولة قراءة الملف باستخدام ترميزات أخرى إذا فشل UTF-8
                with open(ENV_FILE_PATH, 'r', encoding='cp1256') as f:  # ترميز عربي شائع
                    existing_lines = f.readlines()

        # Update existing values or add new ones
        updated_keys = set()
        for i in range(len(existing_lines)):
            line = existing_lines[i].strip()
            if line and not line.startswith('#'):
                key = line.split('=', 1)[0].strip()
                if key in env_vars:
                    existing_lines[i] = f"{key}='{env_vars[key]}'\n"
                    updated_keys.add(key)

        # Add new variables
        for key, value in env_vars.items():
            if key not in updated_keys:
                existing_lines.append(f"{key}='{value}'\n")

        # Write the file using UTF-8 encoding
        with open(ENV_FILE_PATH, 'w', encoding='utf-8') as f:
            f.writelines(existing_lines)
        
        logger.info(f"Environment file updated successfully")
    except Exception as e:
        logger.error(f"Error updating environment file: {e}")

def update_os_env(env_vars):
    """Update environment variables in the system"""
    for key, value in env_vars.items():
        os.environ[key] = value
    logger.info("System environment variables updated")

def is_redis_running(host=DEFAULT_REDIS_HOST, port=DEFAULT_REDIS_PORT):
    """Check if Redis is running"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        logger.error(f"Error checking if Redis is running: {e}")
        return False

def start_redis_server():
    """Start Redis server"""
    logger.info("Attempting to start Redis server...")
    
    # Check if Redis is installed
    try:
        # Check if Redis exists on the system
        if sys.platform.startswith('win'):
            # For Windows
            check_cmd = "where redis-server"
        else:
            # For Linux/Mac
            check_cmd = "which redis-server"
        
        result = subprocess.run(check_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        if result.returncode != 0:
            logger.error("Redis is not installed. Please install Redis first.")
            return False
    except Exception as e:
        logger.error(f"Failed to check if Redis is installed: {e}")
        return False

    try:
        # Try to start Redis using systemd (for Linux)
        if not sys.platform.startswith('win'):
            try:
                subprocess.run(["systemctl", "start", "redis"], check=True)
                time.sleep(1)
                if is_redis_running():
                    logger.info("Successfully started Redis using systemd")
                    return True
            except (subprocess.SubprocessError, FileNotFoundError):
                logger.warning("Failed to start Redis using systemd")

            # Try using service (alternative for Linux)
            try:
                subprocess.run(["service", "redis-server", "start"], check=True)
                time.sleep(1)
                if is_redis_running():
                    logger.info("Successfully started Redis using service")
                    return True
            except (subprocess.SubprocessError, FileNotFoundError):
                logger.warning("Failed to start Redis using service")

        # For Windows or as a last resort for Linux
        redis_cmd = "redis-server"
        logger.info(f"Starting Redis using: {redis_cmd}")
        
        # Run Redis as a separate process
        if sys.platform.startswith('win'):
            process = subprocess.Popen([redis_cmd], 
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE,
                                     creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            process = subprocess.Popen([redis_cmd], 
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
        
        # Wait for startup
        time.sleep(2)
        
        if is_redis_running():
            logger.info("Redis server started successfully")
            
            # Register function to stop Redis when the program closes
            atexit.register(lambda: process.terminate())
            
            return True
        else:
            logger.error("Failed to start Redis")
            return False
    except Exception as e:
        logger.error(f"Error starting Redis: {e}")
        return False

def try_docker_redis(redis_password=None):
    """Try to run Redis using Docker"""
    if redis_password is None:
        redis_password = generate_secure_password()
    
    logger.info("Attempting to run Redis using Docker...")
    try:
        # Check if Docker exists
        result = subprocess.run(["docker", "--version"], 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE)
        if result.returncode != 0:
            logger.error("Docker is not installed. Please install Docker first.")
            return False, None

        # Check if Docker is running
        result = subprocess.run(["docker", "info"], 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE)
        if result.returncode != 0:
            logger.error("Docker is not running. Please start Docker first.")
            return False, None

        # Check if container exists
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", "name=redis-server", "--format", "{{.ID}}"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        container_id = result.stdout.strip()

        if container_id:
            # If container exists, check if it's running
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=redis-server", "--format", "{{.ID}}"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            if result.stdout.strip():
                logger.info("Redis container already exists and is running")
            else:
                # Restart existing container
                subprocess.run(["docker", "start", container_id], check=True)
                logger.info("Restarted existing Redis container")
        else:
            # Create and run a new container
            cmd = [
                "docker", "run", "--name", "redis-server",
                "-p", f"{DEFAULT_REDIS_PORT}:{DEFAULT_REDIS_PORT}", 
                "-d", "redis", "redis-server", 
                "--requirepass", redis_password
            ]
            subprocess.run(cmd, check=True)
            logger.info("Created and started new Redis container")

        # Wait for startup
        time.sleep(2)
        
        if is_redis_running():
            logger.info("Redis started successfully using Docker")
            return True, redis_password
        else:
            logger.error("Failed to start Redis using Docker")
            return False, None
    except Exception as e:
        logger.error(f"Error starting Redis using Docker: {e}")
        return False, None

def test_redis_connection(host=DEFAULT_REDIS_HOST, port=DEFAULT_REDIS_PORT, 
                         db=DEFAULT_REDIS_DB, password=None, retries=3):
    """Test connection to Redis"""
    for attempt in range(retries):
        try:
            if password:
                # Connect using password
                r = redis.Redis(
                    host=host, 
                    port=port, 
                    db=db,
                    password=password,
                    socket_timeout=2
                )
            else:
                # Connect without password
                r = redis.Redis(
                    host=host, 
                    port=port, 
                    db=db,
                    socket_timeout=2
                )
            
            # Check connection
            r.ping()
            logger.info(f"Successfully connected to Redis at {host}:{port}")
            
            # Test read and write
            r.set("test_key", "Connected successfully")
            test_value = r.get("test_key")
            
            if test_value and test_value.decode('utf-8') == "Connected successfully":
                logger.info("Read/write operations successful")
                return True, r
            else:
                logger.error("Failed in Redis read/write operation")
        except redis.exceptions.AuthenticationError:
            # Don't log this as a warning since we expect this when we're trying to detect if we need to set a password
            logger.debug("Authentication failed: Incorrect password")
            return False, None
        except redis.exceptions.ConnectionError as e:
            logger.warning(f"Failed to connect to Redis ({attempt+1}/{retries}): {e}")
            time.sleep(1)  # Wait a bit before trying again
        except Exception as e:
            logger.error(f"Error testing Redis connection: {e}")
            return False, None
    
    return False, None

def configure_redis(connection, password=None):
    """Configure Redis with required settings"""
    if not connection:
        return False
    
    try:
        # Set password if provided
        if password:
            connection.config_set('requirepass', password)
            logger.info("Password set successfully")
        
        # Additional settings to optimize Redis performance
        config_settings = {
            'maxmemory': '256mb',  # Maximum memory limit
            'maxmemory-policy': 'allkeys-lru',  # Policy for removing items when memory is full
            'appendonly': 'yes',  # Enable AOF mode for durability
            'appendfsync': 'everysec',  # Sync appendix every second
        }
        
        # Apply settings
        for setting, value in config_settings.items():
            try:
                connection.config_set(setting, value)
                logger.info(f"Set {setting}={value}")
            except redis.exceptions.ResponseError as e:
                # Some settings may not be available in some Redis versions
                logger.warning(f"Could not set {setting}: {e}")
        
        return True
    except Exception as e:
        logger.error(f"Error configuring Redis: {e}")
        return False

def setup_redis():
    """Set up Redis and ensure it's running"""
    logger.info("Starting Redis setup...")
    
    # Read current settings
    env_vars = read_env_file()
    redis_host = env_vars.get('REDIS_HOST', DEFAULT_REDIS_HOST)
    redis_port = int(env_vars.get('REDIS_PORT', DEFAULT_REDIS_PORT))
    redis_db = int(env_vars.get('REDIS_DB', DEFAULT_REDIS_DB))
    redis_password = env_vars.get('REDIS_PASSWORD')
    
    # Check if Redis is running
    if is_redis_running(redis_host, redis_port):
        logger.info(f"Redis is already running at {redis_host}:{redis_port}")
        
        # First, try connecting without password to determine if auth is required
        success_no_auth, connection_no_auth = test_redis_connection(
            host=redis_host, 
            port=redis_port, 
            db=redis_db, 
            password=None
        )
        
        if success_no_auth:
            logger.info("Connected to Redis without authentication")
            
            # No password required - but we should set one for security
            if not redis_password:
                redis_password = generate_secure_password()
            
            if configure_redis(connection_no_auth, redis_password):
                logger.info("Successfully configured Redis with a new password")
                
                # Reconnect with the new password to confirm
                success, connection = test_redis_connection(
                    host=redis_host, 
                    port=redis_port, 
                    db=redis_db, 
                    password=redis_password
                )
                
                if success:
                    # Update environment file with the new password
                    env_vars['REDIS_PASSWORD'] = redis_password
                    update_env_file(env_vars)
                    update_os_env(env_vars)
                    return True, redis_password, connection
                else:
                    logger.error("Failed to connect after setting the new password")
        else:
            # Auth may be required - try with the password from env if available
            if redis_password:
                logger.info("Trying to connect with current password...")
                success, connection = test_redis_connection(
                    host=redis_host, 
                    port=redis_port, 
                    db=redis_db, 
                    password=redis_password
                )
                
                if success:
                    logger.info("Connected to Redis with current credentials")
                    return True, redis_password, connection
            
            logger.warning("Failed to connect to Redis with current settings")
    else:
        logger.warning("Redis is not running")
        
        # Try to start local Redis
        if start_redis_server():
            # Redis started successfully, now configure it
            # Create a new password if none exists
            if not redis_password:
                redis_password = generate_secure_password()
            
            # Test connection
            success, connection = test_redis_connection(
                host=redis_host, 
                port=redis_port, 
                db=redis_db, 
                password=None  # Initially without password
            )
            
            if success:
                # Configure Redis with password
                if configure_redis(connection, redis_password):
                    # Test connection again with password
                    success, connection = test_redis_connection(
                        host=redis_host, 
                        port=redis_port, 
                        db=redis_db, 
                        password=redis_password
                    )
                    
                    if success:
                        # Update environment file
                        env_vars['REDIS_HOST'] = redis_host
                        env_vars['REDIS_PORT'] = str(redis_port)
                        env_vars['REDIS_DB'] = str(redis_db)
                        env_vars['REDIS_PASSWORD'] = redis_password
                        update_env_file(env_vars)
                        update_os_env(env_vars)
                        return True, redis_password, connection
            
            logger.error("Failed to configure Redis after starting")
        else:
            # Try using Docker
            logger.info("Trying to run Redis using Docker...")
            docker_success, docker_password = try_docker_redis(redis_password)
            
            if docker_success:
                # Test connection
                success, connection = test_redis_connection(
                    host=redis_host, 
                    port=redis_port, 
                    db=redis_db, 
                    password=docker_password
                )
                
                if success:
                    # Update environment file
                    env_vars['REDIS_HOST'] = redis_host
                    env_vars['REDIS_PORT'] = str(redis_port)
                    env_vars['REDIS_DB'] = str(redis_db)
                    env_vars['REDIS_PASSWORD'] = docker_password
                    update_env_file(env_vars)
                    update_os_env(env_vars)
                    return True, docker_password, connection
                
                logger.error("Failed to connect to Redis via Docker")
            else:
                logger.error("All Redis startup attempts failed")
    
    logger.error("Redis setup failed")
    return False, None, None

def ensure_redis_ready():
    """Ensure Redis is ready for use - this function is used from server.py"""
    success, password, _ = setup_redis()
    return success, {
        'REDIS_HOST': os.environ.get('REDIS_HOST', DEFAULT_REDIS_HOST),
        'REDIS_PORT': int(os.environ.get('REDIS_PORT', DEFAULT_REDIS_PORT)),
        'REDIS_DB': int(os.environ.get('REDIS_DB', DEFAULT_REDIS_DB)),
        'REDIS_PASSWORD': password or os.environ.get('REDIS_PASSWORD', '')
    }

if __name__ == "__main__":
    # Run setup if file is called directly
    success, password, _ = setup_redis()
    
    if success:
        print("\n✅ Redis setup completed successfully")
        print(f"🔌 Host: {os.environ.get('REDIS_HOST', DEFAULT_REDIS_HOST)}")
        print(f"🔢 Port: {os.environ.get('REDIS_PORT', DEFAULT_REDIS_PORT)}")
        print(f"🔑 Password: {'*' * 10} (hidden for security)")
        print("\n🚀 You can now start the site using 'python server.py'\n")
    else:
        print("\n❌ Redis setup failed")
        print("\n⚠️ The site will use in-memory cache instead of Redis\n")
        
        # Show options to the user
        print("Options:")
        print("1. Install Redis and restart this program")
        print("2. Run Docker and restart this program")
        print("3. Continue without Redis (not recommended for production)\n")
        
        choice = input("Your choice (1/2/3): ")
        
        if choice == "1":
            if sys.platform.startswith('win'):
                print("\nTo install Redis on Windows:")
                print("1. Download Redis from https://github.com/tporadowski/redis/releases")
                print("2. Install it and follow the instructions")
            else:
                print("\nTo install Redis on Linux:")
                print("sudo apt update && sudo apt install redis-server")
                print("sudo systemctl enable redis-server")
        elif choice == "2":
            print("\nTo install and run Docker:")
            print("Download Docker from https://www.docker.com/products/docker-desktop")
            print("Install and run it")
        
        print("\n🔄 After completing the steps, run this program again.")
        sys.exit(1) 