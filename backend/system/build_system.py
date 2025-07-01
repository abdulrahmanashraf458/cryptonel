"""
Build System - Manages the building of the React application
Handles npm/node.js interaction and error handling
"""

import os
import sys
import subprocess
import shutil
import logging
from typing import Tuple, Optional

# Get logger
logger = logging.getLogger('cryptonel')


def build_react_app(app_dir: str = ".") -> Tuple[bool, Optional[str]]:
    """
    Build the React application using npm with improved error handling
    
    Args:
        app_dir: Directory containing the React application
        
    Returns:
        Tuple[bool, Optional[str]]: Success status and error message if any
    """
    logger.info("[PACKAGE] Building React application...")
    
    try:
        # Find npm executable path based on platform
        npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
        npm_path = shutil.which(npm_cmd)
        
        if not npm_path:
            error_msg = f"[X] Could not find {npm_cmd} in PATH. Make sure Node.js is installed and in your PATH."
            logger.error(error_msg)
            return False, error_msg
            
        logger.info(f"Using npm at: {npm_path}")
        
        # Check for package.json to verify it's a Node.js project
        if not os.path.exists(os.path.join(app_dir, 'package.json')):
            error_msg = "[X] No package.json found. Make sure you're in the correct directory."
            logger.error(error_msg)
            return False, error_msg
        
        # Install dependencies if node_modules doesn't exist
        if not os.path.exists(os.path.join(app_dir, 'node_modules')):
            logger.info("Installing dependencies...")
            
            # First check npm version
            version_result = subprocess.run(
                [npm_path, "--version"], 
                capture_output=True, 
                text=True,
                cwd=app_dir
            )
            
            if version_result.returncode != 0:
                error_msg = f"[X] Error checking npm version: {version_result.stderr}"
                logger.error(error_msg)
                return False, error_msg
                
            logger.info(f"Using npm version: {version_result.stdout.strip()}")
            
            # Then install dependencies with timeout
            install_result = subprocess.run(
                [npm_path, "install"], 
                capture_output=True, 
                text=True,
                cwd=app_dir,
                timeout=300  # 5 minute timeout
            )
            
            if install_result.returncode != 0:
                error_msg = f"[X] Error installing dependencies:\n{install_result.stderr}"
                logger.error(error_msg)
                return False, error_msg
        
        # Run npm run build with appropriate environment
        build_env = os.environ.copy()
        # Set production flag to ensure optimized build
        build_env["NODE_ENV"] = "production"
        # Disable browser opening during build
        build_env["BROWSER"] = "none"
        
        logger.info(f"Running build command with {npm_path}...")
        build_result = subprocess.run(
            [npm_path, "run", "build"], 
            capture_output=True, 
            text=True,
            cwd=app_dir,
            env=build_env,
            timeout=600  # 10 minute timeout
        )
        
        if build_result.returncode != 0:
            error_msg = f"[X] Error building React application:\n{build_result.stderr}"
            logger.error(error_msg)
            return False, error_msg
            
        logger.info("[CHECK] React application built successfully!")
        return True, None
        
    except subprocess.TimeoutExpired:
        error_msg = "[X] Build process timed out. This could indicate an issue with the build script."
        logger.error(error_msg)
        return False, error_msg
    except subprocess.CalledProcessError as e:
        error_msg = f"[X] Error building React application: {e}"
        logger.error(error_msg)
        return False, error_msg
    except FileNotFoundError as e:
        error_msg = f"[X] Command not found: {e}"
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"[X] Unexpected error: {e}"
        logger.error(error_msg, exc_info=True)
        return False, str(e)


def create_error_page(static_folder: str, error_message: str = None) -> None:
    """
    Create a basic error page when the build fails
    
    Args:
        static_folder: Folder to create the error page in
        error_message: Optional error message to display
    """
    if not os.path.exists(static_folder):
        os.makedirs(static_folder)
        
    error_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Build Error</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        h1 {{
            color: #e53e3e;
            border-bottom: 1px solid #ddd;
            padding-bottom: 10px;
        }}
        .error {{
            background-color: #fff5f5;
            border-left: 4px solid #e53e3e;
            padding: 15px;
            margin-bottom: 20px;
        }}
    </style>
</head>
<body>
    <h1>Build Error</h1>
    <p>There was an error building the React application. Please check the server logs.</p>
    {f'<div class="error"><pre>{error_message}</pre></div>' if error_message else ''}
    <p>If you are the administrator, please ensure:</p>
    <ul>
        <li>Node.js and npm are installed correctly</li>
        <li>All dependencies are installed (run npm install)</li>
        <li>The build script in package.json is configured correctly</li>
    </ul>
</body>
</html>
"""
    
    with open(os.path.join(static_folder, 'index.html'), 'w') as f:
        f.write(error_html) 