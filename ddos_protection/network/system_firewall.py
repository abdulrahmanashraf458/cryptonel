#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DDoS Protection System - System Firewall Stub
-------------------------------------------
Este es un archivo stub para evitar errores de importación cuando
el sistema está configurado para usar exclusivamente Cloudflare.
"""

import logging

# Configure logger
logger = logging.getLogger('ddos_protection.network.system_firewall')

class SystemFirewall:
    """Stub class for system firewall to avoid import errors."""
    
    def __init__(self):
        """Initialize system firewall stub."""
        logger.info("SystemFirewall stub initialized (Cloudflare-only mode)")
        
    def block_ip(self, ip, reason="Unknown", duration=None):
        """Stub method for blocking IP."""
        logger.debug(f"SystemFirewall stub: block_ip called for {ip} (ignored in Cloudflare-only mode)")
        return True
        
    def unblock_ip(self, ip):
        """Stub method for unblocking IP."""
        logger.debug(f"SystemFirewall stub: unblock_ip called for {ip} (ignored in Cloudflare-only mode)")
        return True
        
    def is_blocked(self, ip):
        """Stub method for checking if IP is blocked."""
        return False
        
    def list_blocked(self):
        """Stub method for listing blocked IPs."""
        return [] 