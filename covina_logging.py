#!/usr/bin/env python3
"""
Globaler Logging-Filter für das gesamte Covina-System.
Filtert Unicode-Encoding-Fehler und andere störende Log-Meldungen.
"""

import logging
import sys


class CovinaLoggingFilter(logging.Filter):
    """Globaler Filter für Covina Logging-System."""
    
    def __init__(self):
        super().__init__()
        self.suppressed_patterns = [
            'character maps to <undefined>',
            'charmap codec can\'t encode',
            '--- Logging error ---',
            'Call stack:',
            'UnicodeEncodeError',
            'During handling of the above exception',
            'Traceback (most recent call last):',
            'File "C:\\Program Files\\Python',
            'stream.write(msg + self.terminator)',
            'codecs.charmap_encode',
        ]
        
        self.emoji_replacements = {
            '✅': '[OK]',
            '⚠️': '[WARN]',
            '❌': '[ERROR]',
            '🔧': '[SETUP]',
            '📊': '[STATS]',
            '🔍': '[SEARCH]',
            '📄': '[FILE]',
            '🤖': '[AI]',
            '🎬': '[MEDIA]',
            '📋': '[CLASS]',
            '🔒': '[PII]',
        }
    
    def filter(self, record):
        """Filtert Log-Records."""
        try:
            message = record.getMessage()
            
            # Unterdrücke bekannte Unicode-Encoding-Fehler
            for pattern in self.suppressed_patterns:
                if pattern.lower() in message.lower():
                    return False
            
            # Ersetze Emojis für bessere Windows-Kompatibilität
            for emoji, replacement in self.emoji_replacements.items():
                if emoji in message:
                    record.msg = str(record.msg).replace(emoji, replacement)
            
            # Kürze extrem lange Nachrichten
            if len(message) > 300:
                record.msg = str(record.msg)[:300] + "... [truncated]"
            
            return True
            
        except Exception:
            # Bei Fehlern im Filter: Log trotzdem anzeigen
            return True


def setup_global_logging_filter():
    """Richtet globalen Logging-Filter ein."""
    try:
        # UTF-8 Support für Console falls möglich
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass
    
    # Filter zu allen Loggern hinzufügen
    filter_instance = CovinaLoggingFilter()
    
    # Root Logger
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.addFilter(filter_instance)
    
    # Spezifische Logger für Covina-Module
    covina_loggers = [
        'ingestion',
        'ingestion.discovery_service',
        'ingestion.ai_enhanced_content_processor',
        'ingestion.uds3_document_classification_service',
        'uds3',
        'uds3_delete_operations',
        'uds3_polyglot_query',
    ]
    
    for logger_name in covina_loggers:
        logger = logging.getLogger(logger_name)
        for handler in logger.handlers:
            handler.addFilter(filter_instance)
        
        # Sicherer Handler falls noch keiner vorhanden
        if not logger.handlers:
            safe_handler = SafeStreamHandler()
            safe_handler.addFilter(filter_instance)
            logger.addHandler(safe_handler)


class SafeStreamHandler(logging.StreamHandler):
    """Stream Handler mit Unicode-Fallback."""
    
    def emit(self, record):
        try:
            super().emit(record)
        except UnicodeEncodeError:
            # Fallback zu ASCII-only Ausgabe
            try:
                # Konvertiere Nachricht zu ASCII
                if hasattr(record, 'msg'):
                    record.msg = str(record.msg).encode('ascii', errors='replace').decode('ascii')
                super().emit(record)
            except:
                # Letzter Fallback: Einfache Nachricht
                print(f"[LOG] {record.levelname}: {record.name} - Unicode encoding error")


# Auto-Setup beim Import
setup_global_logging_filter()