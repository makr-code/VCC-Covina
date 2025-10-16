"""Test import guard used to monkeypatch environment issues before adapter imports.

This module is intended for test environments only. It ensures common socket
constants exist so optional drivers that expect them don't crash at import-time.
"""
import socket
import logging

logger = logging.getLogger(__name__)

patched = False
try:
    if not hasattr(socket, 'EAI_ADDRFAMILY'):
        # Use a sentinel numeric value that's unlikely to conflict
        socket.EAI_ADDRFAMILY = -1
        patched = True
        logger.info('Patched socket.EAI_ADDRFAMILY for test environment')
except Exception as e:
    logger.warning(f'Failed to monkeypatch socket constants: {e}')

__all__ = ['patched']
