#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DDoS Protection System - Early IP Rejection Module
--------------------------------------------------
وحدة رفض عناوين IP المشبوهة في مرحلة مبكرة
"""

import logging
import time
import re
from typing import Dict, List, Set, Any, Optional, Callable

logger = logging.getLogger("ddos_protection.middleware.early_ip_rejection")

class EarlyIPRejection:
    """
    Proporciona rechazo temprano de IPs maliciosas antes del procesamiento completo de la solicitud.
    Esta clase actúa como una primera línea de defensa rápida.
    """
    
    def __init__(self):
        """Inicializar el sistema de rechazo temprano de IP."""
        # Cache de IPs para verificación rápida
        self._banned_ips_cache = set()
        self._trusted_ips_cache = set()
        
        # Patrones para identificar bots maliciosos conocidos
        self.malicious_bot_patterns = [
            'zgrab',
            'masscan',
            'nmap',
            'nikto',
            'sqlmap',
            'semrush',
            'netsystemsresearch',
            'python-requests',
            'go-http-client',
            'whatweb',
            'ahrefs',
            'censys',
            'curl/',
            'wget/',
            'bot',
            'spider',
            'crawler',
            'scrapinghub',
            'scrapy',
            'check_http',
            'http-client',
            'linkchecker',
            'facebookexternalhit',
            'java/',
            'dirbuster',
            'metasploit',
            'nuclei',
            'gobuster',
            'ffuf',
            'wfuzz',
            'wpscan',
            'shodan',
            'zabbix'
        ]
        
        # Expresión regular compilada para rendimiento
        self.bot_pattern = re.compile('|'.join(self.malicious_bot_patterns), re.IGNORECASE)
        
        # Contadores para métricas
        self.metrics = {
            'total_rejections': 0,
            'ip_rejections': 0,
            'bot_rejections': 0,
            'rate_rejections': 0
        }
        
        # Cache para rate limiting ligero (IP -> lista de timestamps)
        self._rate_cache = {}
        self._rate_limit_window = 5  # Segundos
        self._rate_limit_max = 15    # Solicitudes por ventana
        
        # Tiempo de la última limpieza
        self._last_cleanup = time.time()
        self._cleanup_interval = 30   # Segundos
        
    def update_banned_ips(self, banned_ips: Set[str]) -> None:
        """Actualiza el caché de IPs prohibidas."""
        self._banned_ips_cache = set(banned_ips)
        
    def update_trusted_ips(self, trusted_ips: Set[str]) -> None:
        """Actualiza el caché de IPs confiables."""
        self._trusted_ips_cache = set(trusted_ips)
        
    def should_reject(self, ip: str, user_agent: str) -> bool:
        """
        Verifica rápidamente si una solicitud debe rechazarse de inmediato.
        
        Args:
            ip: Dirección IP del cliente
            user_agent: Agente de usuario del cliente
            
        Returns:
            bool: True si la solicitud debe rechazarse, False en caso contrario
        """
        # Verificar limpieza periódica 
        current_time = time.time()
        if current_time - self._last_cleanup > self._cleanup_interval:
            self._cleanup_rate_cache(current_time)
            self._last_cleanup = current_time
        
        # 1. Verificar si la IP está en la lista blanca
        if ip in self._trusted_ips_cache:
            return False
            
        # 2. Verificar si la IP está prohibida
        if ip in self._banned_ips_cache:
            self.metrics['ip_rejections'] += 1
            self.metrics['total_rejections'] += 1
            return True
            
        # 3. Verificar si es un bot malicioso conocido
        if user_agent and self.bot_pattern.search(user_agent):
            self.metrics['bot_rejections'] += 1
            self.metrics['total_rejections'] += 1
            return True
            
        # 4. Verificar rate limiting básico
        if self._check_rate_limit(ip, current_time):
            self.metrics['rate_rejections'] += 1
            self.metrics['total_rejections'] += 1
            return True
            
        return False
        
    def _check_rate_limit(self, ip: str, current_time: float) -> bool:
        """
        Verifica si una IP ha excedido el límite de tasa.
        
        Args:
            ip: Dirección IP del cliente
            current_time: Tiempo actual
            
        Returns:
            bool: True si se excede el límite de tasa, False en caso contrario
        """
        # Inicializar si es nueva IP
        if ip not in self._rate_cache:
            self._rate_cache[ip] = []
            
        # Añadir registro de tiempo
        self._rate_cache[ip].append(current_time)
        
        # Limpiar solicitudes antiguas fuera de la ventana
        window_start = current_time - self._rate_limit_window
        self._rate_cache[ip] = [t for t in self._rate_cache[ip] if t > window_start]
        
        # Verificar si excede el límite
        return len(self._rate_cache[ip]) > self._rate_limit_max
        
    def _cleanup_rate_cache(self, current_time: float) -> None:
        """
        Limpia el caché de tasa para evitar el crecimiento de memoria.
        
        Args:
            current_time: Tiempo actual
        """
        window_start = current_time - self._rate_limit_window
        for ip in list(self._rate_cache.keys()):
            # Limpiar solicitudes antiguas
            self._rate_cache[ip] = [t for t in self._rate_cache[ip] if t > window_start]
            # Eliminar entradas vacías
            if not self._rate_cache[ip]:
                del self._rate_cache[ip]
                
    def get_metrics(self) -> Dict[str, int]:
        """Devuelve métricas sobre rechazos."""
        return self.metrics.copy()
        
    def reset_metrics(self) -> None:
        """Restablece los contadores de métricas a cero."""
        for key in self.metrics:
            self.metrics[key] = 0
            
# Instancia global
early_rejection = EarlyIPRejection()

def create_flask_middleware(app, ban_manager=None, storage_manager=None):
    """
    Crea un middleware Flask para el rechazo temprano.
    
    Args:
        app: Aplicación Flask
        ban_manager: Gestor de prohibiciones opcional
        storage_manager: Gestor de almacenamiento opcional
        
    Returns:
        Function: Función middleware para Flask
    """
    from flask import request, jsonify
    
    # Actualizar caché de IPs prohibidas si el gestor está disponible
    if ban_manager and hasattr(ban_manager, 'get_banned_ips'):
        banned_ips = ban_manager.get_banned_ips()
        early_rejection.update_banned_ips(set(banned_ips.keys()))
    
    # Actualizar caché de IPs confiables si el almacenamiento está disponible
    if storage_manager and hasattr(storage_manager, 'trusted_ips'):
        trusted_ips = storage_manager.trusted_ips.keys()
        early_rejection.update_trusted_ips(set(trusted_ips))
    
    @app.before_request
    def reject_malicious_ips():
        """Middleware para rechazar IPs maliciosas temprano."""
        # Obtener IP del cliente y agente de usuario
        client_ip = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')
        
        # Verificar si debe rechazarse
        if early_rejection.should_reject(client_ip, user_agent):
            return jsonify({'error': 'Acceso denegado'}), 403
        
        # Permitir que continúe la solicitud
        return None

def create_fastapi_middleware(ban_manager=None, storage_manager=None):
    """
    Crea un middleware FastAPI para el rechazo temprano.
    
    Args:
        ban_manager: Gestor de prohibiciones opcional
        storage_manager: Gestor de almacenamiento opcional
        
    Returns:
        Function: Función middleware para FastAPI
    """
    # Actualizar caché de IPs prohibidas si el gestor está disponible
    if ban_manager and hasattr(ban_manager, 'get_banned_ips'):
        banned_ips = ban_manager.get_banned_ips()
        early_rejection.update_banned_ips(set(banned_ips.keys()))
    
    # Actualizar caché de IPs confiables si el almacenamiento está disponible
    if storage_manager and hasattr(storage_manager, 'trusted_ips'):
        trusted_ips = storage_manager.trusted_ips.keys()
        early_rejection.update_trusted_ips(set(trusted_ips))
    
    async def middleware(request, call_next):
        """Middleware para rechazar IPs maliciosas temprano."""
        from fastapi.responses import JSONResponse
        
        # Obtener IP del cliente y agente de usuario
        client_ip = request.client.host
        user_agent = request.headers.get('user-agent', '')
        
        # Verificar si debe rechazarse
        if early_rejection.should_reject(client_ip, user_agent):
            return JSONResponse(
                content={'error': 'Acceso denegado'},
                status_code=403
            )
        
        # Permitir que continúe la solicitud
        return await call_next(request)
    
    return middleware 