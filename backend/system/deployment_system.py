"""
Deployment System - Zero Downtime Deployment support

This module provides utilities for implementing zero-downtime deployments
using blue-green deployment strategy and graceful shutdowns.
"""

import os
import sys
import time
import signal
import socket
import logging
import threading
import subprocess
from typing import Dict, List, Optional, Callable, Union

# Configure logging
logger = logging.getLogger('cryptonel.deployment')

# Signal handler for graceful shutdown
_is_shutting_down = False
_original_handlers = {}
_shutdown_handlers = []
_lock = threading.RLock()
_readiness_file = None


def configure_zero_downtime(app, readiness_file: Optional[str] = None) -> None:
    """
    Configure application for zero downtime deployments
    
    Args:
        app: Flask application
        readiness_file: Optional path to readiness probe file
    """
    global _readiness_file
    
    # Set up readiness probe file
    if readiness_file:
        _readiness_file = readiness_file
        # Create readiness file to indicate app is ready
        with open(_readiness_file, 'w') as f:
            f.write('ready')
        logger.info(f"Created readiness probe file: {_readiness_file}")
    
    # Register health check endpoint for liveness probes
    @app.route('/system/ready')
    def readiness_probe():
        """Simple endpoint for readiness probes"""
        if _is_shutting_down:
            return "Service is shutting down", 503
        return "ready", 200
    
    @app.route('/system/live')
    def liveness_probe():
        """Simple endpoint for liveness probes"""
        return "alive", 200
    
    # Register signal handlers for graceful shutdown
    register_signal_handlers()
    
    logger.info("Zero-downtime deployment support configured")


def register_signal_handlers() -> None:
    """Register signal handlers for graceful shutdown"""
    signals = [signal.SIGTERM, signal.SIGINT, signal.SIGQUIT]
    
    def handle_signal(sig, frame):
        """Handle termination signals with graceful shutdown"""
        global _is_shutting_down
        
        if _is_shutting_down:
            # If already shutting down and we get another signal,
            # call the original handler
            logger.warning(f"Received signal {sig} again during shutdown")
            if sig in _original_handlers and _original_handlers[sig]:
                _original_handlers[sig](sig, frame)
            return
        
        logger.info(f"Received signal {sig}, starting graceful shutdown")
        _is_shutting_down = True
        
        # Remove readiness file to stop receiving new traffic
        if _readiness_file and os.path.exists(_readiness_file):
            try:
                os.unlink(_readiness_file)
                logger.info(f"Removed readiness file: {_readiness_file}")
            except Exception as e:
                logger.error(f"Failed to remove readiness file: {e}")
        
        # Execute shutdown handlers
        for handler in _shutdown_handlers:
            try:
                handler()
            except Exception as e:
                logger.error(f"Error in shutdown handler: {e}")
        
        # If no handlers were registered, just exit
        if not _shutdown_handlers:
            logger.info("No shutdown handlers registered, exiting")
            sys.exit(0)
    
    # Save original handlers and register new ones
    for sig in signals:
        _original_handlers[sig] = signal.getsignal(sig)
        signal.signal(sig, handle_signal)
    
    logger.info("Registered signal handlers for graceful shutdown")


def register_shutdown_handler(handler: Callable[[], None]) -> None:
    """
    Register a function to be called during shutdown
    
    Args:
        handler: Function to call during shutdown
    """
    with _lock:
        if handler not in _shutdown_handlers:
            _shutdown_handlers.append(handler)
            logger.debug(f"Registered shutdown handler: {handler.__name__}")


def is_shutting_down() -> bool:
    """
    Check if application is currently shutting down
    
    Returns:
        bool: Whether shutdown is in progress
    """
    return _is_shutting_down


def graceful_gunicorn_shutdown(timeout: int = 30) -> None:
    """
    Configure Gunicorn for graceful shutdown
    
    Args:
        timeout: Shutdown timeout in seconds
    """
    def post_fork(server, worker):
        """Gunicorn post-fork hook"""
        logger.info(f"Worker {worker.pid} started")
    
    def worker_exit(server, worker):
        """Handle worker exit"""
        logger.info(f"Worker {worker.pid} exiting gracefully")
    
    def worker_abort(worker):
        """Gunicorn worker abort hook"""
        logger.warning(f"Worker {worker.pid} aborting")
    
    def on_starting(server):
        """Gunicorn starting hook"""
        logger.info("Gunicorn server starting")
    
    def on_exit(server):
        """Gunicorn exit hook"""
        logger.info("Gunicorn server exiting")
    
    # Configure Gunicorn settings for graceful shutdown
    return {
        'worker_exit': worker_exit,
        'worker_abort': worker_abort,
        'on_starting': on_starting,
        'on_exit': on_exit,
        'graceful_timeout': timeout,
        'timeout': timeout + 5,  # Slightly longer than graceful_timeout
    }


class BlueGreenDeployment:
    """
    Helper for implementing blue-green deployments
    """
    
    def __init__(self, port_blue: int = 8000, port_green: int = 8001, nginx_config: str = '/etc/nginx/conf.d/cryptonel.conf'):
        """
        Initialize blue-green deployment handler
        
        Args:
            port_blue: Port for the blue deployment
            port_green: Port for the green deployment
            nginx_config: Path to Nginx config file
        """
        self.port_blue = port_blue
        self.port_green = port_green
        self.nginx_config = nginx_config
        self.current_color = self._detect_current_color()
    
    def _detect_current_color(self) -> str:
        """
        Detect the current deployment color
        
        Returns:
            str: 'blue' or 'green'
        """
        # Get the port this process is listening on
        try:
            # Get all listening sockets
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('', 0))
            port = sock.getsockname()[1]
            sock.close()
            
            if port == self.port_blue:
                return 'blue'
            elif port == self.port_green:
                return 'green'
        except:
            pass
        
        # Fallback: try to parse Nginx config
        try:
            with open(self.nginx_config, 'r') as f:
                content = f.read()
                if f'127.0.0.1:{self.port_blue}' in content and 'active' in content:
                    return 'blue'
                elif f'127.0.0.1:{self.port_green}' in content and 'active' in content:
                    return 'green'
        except:
            pass
        
        # Default to blue
        return 'blue'
    
    def get_inactive_color(self) -> str:
        """
        Get the inactive deployment color
        
        Returns:
            str: 'blue' or 'green'
        """
        return 'green' if self.current_color == 'blue' else 'blue'
    
    def get_inactive_port(self) -> int:
        """
        Get the inactive deployment port
        
        Returns:
            int: Port number
        """
        return self.port_green if self.current_color == 'blue' else self.port_blue
    
    def switch_to_new_deployment(self) -> bool:
        """
        Switch Nginx to point to the new deployment
        
        Returns:
            bool: Whether switch was successful
        """
        try:
            inactive_color = self.get_inactive_color()
            inactive_port = self.get_inactive_port()
            
            # Generate new Nginx config
            nginx_cmd = [
                'sudo', 'bash', '-c',
                f"sed -i 's/server 127.0.0.1:{self.port_blue if inactive_color == 'green' else self.port_green}/server 127.0.0.1:{inactive_port}/' {self.nginx_config}"
            ]
            subprocess.run(nginx_cmd, check=True)
            
            # Reload Nginx
            reload_cmd = ['sudo', 'systemctl', 'reload', 'nginx']
            subprocess.run(reload_cmd, check=True)
            
            logger.info(f"Switched to {inactive_color} deployment on port {inactive_port}")
            return True
        except Exception as e:
            logger.error(f"Failed to switch to new deployment: {e}")
            return False
    
    @staticmethod
    def create_deployment_script(script_path: str) -> None:
        """
        Create a deployment script for blue-green deployments
        
        Args:
            script_path: Path to write the script
        """
        script_content = """#!/bin/bash
# Cryptonel Wallet - Blue-Green Deployment Script

set -e

# Configuration
APP_DIR="/path/to/cryptonel"
VENV_DIR="$APP_DIR/venv"
BLUE_PORT=8000
GREEN_PORT=8001
NGINX_CONF="/etc/nginx/conf.d/cryptonel.conf"
TIMEOUT=60

# Determine current active color
if grep -q "server 127.0.0.1:$BLUE_PORT" "$NGINX_CONF" && ! grep -q "#.*server 127.0.0.1:$BLUE_PORT" "$NGINX_CONF"; then
    ACTIVE_COLOR="blue"
    INACTIVE_COLOR="green"
    INACTIVE_PORT=$GREEN_PORT
else
    ACTIVE_COLOR="green"
    INACTIVE_COLOR="blue"
    INACTIVE_PORT=$BLUE_PORT
fi

echo "Current active deployment: $ACTIVE_COLOR on port ${ACTIVE_COLOR^^}_PORT"
echo "Deploying to $INACTIVE_COLOR on port $INACTIVE_PORT"

# Pull latest code
cd "$APP_DIR"
git pull

# Install dependencies in virtualenv
source "$VENV_DIR/bin/activate"
pip install -r requirements.txt

# Start the inactive deployment
PRODUCTION=true \
PORT=$INACTIVE_PORT \
BLUE_GREEN=true \
nohup "$VENV_DIR/bin/gunicorn" -w 4 -b "127.0.0.1:$INACTIVE_PORT" --timeout 90 server:app > "$APP_DIR/logs/gunicorn-$INACTIVE_COLOR.log" 2>&1 &

INACTIVE_PID=$!
echo "Started $INACTIVE_COLOR deployment with PID $INACTIVE_PID"

# Wait for it to be ready
echo "Waiting for $INACTIVE_COLOR deployment to be ready..."
ATTEMPTS=0
MAX_ATTEMPTS=$((TIMEOUT / 2))
until $(curl --output /dev/null --silent --head --fail http://127.0.0.1:$INACTIVE_PORT/system/ready); do
    ATTEMPTS=$((ATTEMPTS + 1))
    if [ $ATTEMPTS -ge $MAX_ATTEMPTS ]; then
        echo "Error: $INACTIVE_COLOR deployment failed to start within $TIMEOUT seconds"
        kill $INACTIVE_PID
        exit 1
    fi
    sleep 2
done

echo "$INACTIVE_COLOR deployment is ready."

# Switch Nginx to the new deployment
echo "Switching Nginx to $INACTIVE_COLOR deployment..."
sed -i "s/server 127.0.0.1:${ACTIVE_COLOR^^}_PORT/server 127.0.0.1:$INACTIVE_PORT/" "$NGINX_CONF"
nginx -t && systemctl reload nginx

echo "Switched to $INACTIVE_COLOR deployment. Waiting for connections to drain from $ACTIVE_COLOR..."
sleep 30

# Find and stop the old deployment
OLD_PID=$(ps aux | grep "gunicorn.*$ACTIVE_COLOR" | grep -v grep | awk '{print $2}')
if [ ! -z "$OLD_PID" ]; then
    echo "Stopping $ACTIVE_COLOR deployment (PID $OLD_PID)..."
    kill -TERM $OLD_PID
    
    # Wait for it to exit gracefully
    ATTEMPTS=0
    while kill -0 $OLD_PID >/dev/null 2>&1; do
        ATTEMPTS=$((ATTEMPTS + 1))
        if [ $ATTEMPTS -ge $((TIMEOUT / 5)) ]; then
            echo "Warning: $ACTIVE_COLOR deployment did not exit gracefully, forcing stop..."
            kill -9 $OLD_PID
            break
        fi
        sleep 5
    done
else
    echo "No running $ACTIVE_COLOR deployment found."
fi

echo "Deployment complete! $INACTIVE_COLOR is now active on port $INACTIVE_PORT"
"""
        
        try:
            with open(script_path, 'w') as f:
                f.write(script_content)
            os.chmod(script_path, 0o755)  # Make executable
            logger.info(f"Created blue-green deployment script: {script_path}")
        except Exception as e:
            logger.error(f"Failed to create deployment script: {e}")


class RollingDeployment:
    """
    Helper for implementing rolling deployments with Kubernetes
    """
    
    @staticmethod
    def create_k8s_deployment_files(output_dir: str) -> None:
        """
        Create Kubernetes deployment files for rolling updates
        
        Args:
            output_dir: Directory to write the files
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Create deployment.yaml
        deployment_yaml = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: cryptonel-wallet
  labels:
    app: cryptonel-wallet
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: cryptonel-wallet
  template:
    metadata:
      labels:
        app: cryptonel-wallet
    spec:
      containers:
      - name: cryptonel-wallet
        image: ${DOCKER_REGISTRY}/cryptonel-wallet:${VERSION}
        imagePullPolicy: Always
        ports:
        - containerPort: 5000
        env:
        - name: PRODUCTION
          value: "true"
        - name: MONGO_URI
          valueFrom:
            secretKeyRef:
              name: cryptonel-secrets
              key: mongo_uri
        - name: REDIS_URI
          valueFrom:
            secretKeyRef:
              name: cryptonel-secrets
              key: redis_uri
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: cryptonel-secrets
              key: secret_key
        readinessProbe:
          httpGet:
            path: /system/ready
            port: 5000
          initialDelaySeconds: 10
          periodSeconds: 5
        livenessProbe:
          httpGet:
            path: /system/live
            port: 5000
          initialDelaySeconds: 30
          periodSeconds: 15
        resources:
          limits:
            cpu: "1"
            memory: "512Mi"
          requests:
            cpu: "0.1"
            memory: "128Mi"
        lifecycle:
          preStop:
            exec:
              command: ["sh", "-c", "sleep 10"]
"""
        
        # Create service.yaml
        service_yaml = """apiVersion: v1
kind: Service
metadata:
  name: cryptonel-wallet
  labels:
    app: cryptonel-wallet
spec:
  selector:
    app: cryptonel-wallet
  ports:
  - port: 80
    targetPort: 5000
  type: ClusterIP
"""
        
        # Create ingress.yaml
        ingress_yaml = """apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: cryptonel-wallet
  annotations:
    kubernetes.io/ingress.class: "nginx"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - wallet.example.com
    secretName: cryptonel-tls
  rules:
  - host: wallet.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: cryptonel-wallet
            port:
              number: 80
"""
        
        # Create secrets.yaml template
        secrets_yaml = """apiVersion: v1
kind: Secret
metadata:
  name: cryptonel-secrets
type: Opaque
data:
  mongo_uri: # base64 encoded MongoDB URI
  redis_uri: # base64 encoded Redis URI
  secret_key: # base64 encoded secret key
"""
        
        # Write files
        with open(os.path.join(output_dir, 'deployment.yaml'), 'w') as f:
            f.write(deployment_yaml)
        
        with open(os.path.join(output_dir, 'service.yaml'), 'w') as f:
            f.write(service_yaml)
        
        with open(os.path.join(output_dir, 'ingress.yaml'), 'w') as f:
            f.write(ingress_yaml)
        
        with open(os.path.join(output_dir, 'secrets.yaml'), 'w') as f:
            f.write(secrets_yaml)
        
        # Create deployment script
        deploy_script = """#!/bin/bash
# Cryptonel Wallet - Kubernetes Deployment Script

set -e

# Configuration
VERSION=${1:-latest}
NAMESPACE=${2:-default}
DOCKER_REGISTRY="your-registry.example.com"

echo "Deploying Cryptonel Wallet version $VERSION to namespace $NAMESPACE"

# Build and push Docker image
docker build -t $DOCKER_REGISTRY/cryptonel-wallet:$VERSION .
docker push $DOCKER_REGISTRY/cryptonel-wallet:$VERSION

# Apply Kubernetes configs
export VERSION=$VERSION
export DOCKER_REGISTRY=$DOCKER_REGISTRY

# Apply secrets first (if not already created)
kubectl get secret cryptonel-secrets -n $NAMESPACE || kubectl apply -f k8s/secrets.yaml -n $NAMESPACE

# Apply service and ingress
kubectl apply -f k8s/service.yaml -n $NAMESPACE
kubectl apply -f k8s/ingress.yaml -n $NAMESPACE

# Apply deployment with environment variables expanded
envsubst < k8s/deployment.yaml | kubectl apply -f - -n $NAMESPACE

# Watch the rollout
kubectl rollout status deployment/cryptonel-wallet -n $NAMESPACE

echo "Deployment complete!"
"""
        
        with open(os.path.join(output_dir, 'deploy.sh'), 'w') as f:
            f.write(deploy_script)
        os.chmod(os.path.join(output_dir, 'deploy.sh'), 0o755)  # Make executable
        
        logger.info(f"Created Kubernetes deployment files in {output_dir}")


def create_systemd_service_file(output_path: str, app_dir: str, venv_dir: Optional[str] = None) -> None:
    """
    Create a systemd service file for the application
    
    Args:
        output_path: Path to write the service file
        app_dir: Application directory
        venv_dir: Optional virtualenv directory
    """
    if venv_dir is None:
        venv_dir = os.path.join(app_dir, 'venv')
    
    service_content = f"""[Unit]
Description=Cryptonel Wallet Flask Application
After=network.target

[Service]
User=www-data
WorkingDirectory={app_dir}
Environment="PATH={venv_dir}/bin"
Environment="PRODUCTION=true"
ExecStart={venv_dir}/bin/gunicorn -w 4 -b 127.0.0.1:5000 --timeout 90 server:app
Restart=always
# Give a reasonable amount of time for connections to drain
TimeoutStopSec=30

# Graceful shutdown support
KillSignal=SIGTERM
KillMode=mixed

# Security hardening
PrivateTmp=true
ProtectSystem=full
NoNewPrivileges=true
ProtectHome=true

[Install]
WantedBy=multi-user.target
"""
    
    try:
        with open(output_path, 'w') as f:
            f.write(service_content)
        logger.info(f"Created systemd service file: {output_path}")
    except Exception as e:
        logger.error(f"Failed to create systemd service file: {e}")


def create_dockerfile(output_path: str) -> None:
    """
    Create a Dockerfile for the application
    
    Args:
        output_path: Path to write the Dockerfile
    """
    dockerfile_content = """FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    build-essential \\
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PRODUCTION=true
ENV PYTHONUNBUFFERED=1

# Create non-root user
RUN useradd -m cryptonel
RUN chown -R cryptonel:cryptonel /app
USER cryptonel

# Create readiness file directory with correct permissions
RUN mkdir -p /tmp/cryptonel
RUN touch /tmp/cryptonel/ready

# Expose port
EXPOSE 5000

# Run the application
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--timeout", "90", "server:app"]
"""
    
    try:
        with open(output_path, 'w') as f:
            f.write(dockerfile_content)
        logger.info(f"Created Dockerfile: {output_path}")
    except Exception as e:
        logger.error(f"Failed to create Dockerfile: {e}")


def create_deployment_docs(output_path: str) -> None:
    """
    Create a documentation file for zero-downtime deployments
    
    Args:
        output_path: Path to write the documentation
    """
    docs_content = """# Zero-Downtime Deployment Guide

This guide explains how to implement zero-downtime deployments for the Cryptonel Wallet application.

## Deployment Strategies

Three deployment strategies are provided:

1. **Blue-Green Deployment**: Two identical environments run side by side, with traffic switched between them.
2. **Rolling Deployment with Kubernetes**: Gradually replaces instances with new versions.
3. **Systemd Service with Graceful Shutdown**: Single-server deployment with connection draining.

## Blue-Green Deployment

### How It Works

1. Two identical environments run on different ports (Blue: 8000, Green: 8001)
2. Nginx proxies traffic to the active environment
3. New code is deployed to the inactive environment
4. Once ready, Nginx is reconfigured to point to the new environment
5. Old environment is gracefully shut down after connections drain

### Implementation

1. Set up the deployment script:
   ```bash
   python -c "from backend.system.deployment_system import BlueGreenDeployment; BlueGreenDeployment.create_deployment_script('/path/to/deploy.sh')"
   ```

2. Run the deployment script:
   ```bash
   sudo ./deploy.sh
   ```

## Kubernetes Rolling Deployment

### How It Works

1. Kubernetes gradually replaces pods with new versions
2. Readiness probes ensure new pods are only added to service when ready
3. Lifecycle hooks ensure pods drain connections before terminating

### Implementation

1. Generate Kubernetes manifests:
   ```bash
   python -c "from backend.system.deployment_system import RollingDeployment; RollingDeployment.create_k8s_deployment_files('k8s')"
   ```

2. Edit the files in the `k8s` directory to match your environment

3. Run the deployment script:
   ```bash
   ./k8s/deploy.sh 1.0.0
   ```

## Systemd Service with Graceful Shutdown

### How It Works

1. Systemd manages the application as a service
2. SIGTERM signal triggers graceful shutdown
3. Application stops accepting new connections but finishes processing existing ones

### Implementation

1. Generate systemd service file:
   ```bash
   python -c "from backend.system.deployment_system import create_systemd_service_file; create_systemd_service_file('/etc/systemd/system/cryptonel.service', '/path/to/app')"
   ```

2. Enable and start the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable cryptonel
   sudo systemctl start cryptonel
   ```

3. For updates, deploy new code and restart the service:
   ```bash
   git pull
   pip install -r requirements.txt
   sudo systemctl restart cryptonel
   ```

## Implementing in Your Application

Add this to your application's startup code:

```python
from backend.system.deployment_system import configure_zero_downtime, register_shutdown_handler

# Configure zero-downtime support
configure_zero_downtime(app, readiness_file='/tmp/cryptonel/ready')

# Register shutdown handlers
def cleanup_connections():
    # Close database connections, etc.
    logger.info("Cleaning up connections...")
    time.sleep(5)  # Give time for connections to finish

register_shutdown_handler(cleanup_connections)
```

## Monitoring Deployments

Monitor the health of your deployments:

- Check application logs: `journalctl -u cryptonel`
- Verify readiness endpoint: `curl http://localhost:5000/system/ready`
- Test liveness endpoint: `curl http://localhost:5000/system/live`

## Rollback Procedure

If a deployment fails:

### Blue-Green
Modify Nginx config to point back to the previous version and reload.

### Kubernetes
```bash
kubectl rollout undo deployment/cryptonel-wallet
```

### Systemd
```bash
git checkout previous-version
pip install -r requirements.txt
sudo systemctl restart cryptonel
```
"""
    
    try:
        with open(output_path, 'w') as f:
            f.write(docs_content)
        logger.info(f"Created deployment documentation: {output_path}")
    except Exception as e:
        logger.error(f"Failed to create deployment documentation: {e}")


# When this module is imported, register it to handle shutdown signals
register_signal_handlers() 