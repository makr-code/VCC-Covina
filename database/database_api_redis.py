#!/usr/bin/env python3
"""
Redis Key-Value Database Backend
"""

import logging
import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from database.database_api_base import DatabaseBackend
# UDS3 v3.0 Import mit Fallback
try:
    from uds3_core import UnifiedDatabaseStrategy
    get_unified_database_strategy = UnifiedDatabaseStrategy
    UDS3_AVAILABLE = True
except ImportError:
    UDS3_AVAILABLE = False
    get_unified_database_strategy = None

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


class RedisKeyValueBackend(DatabaseBackend):
    """Redis Key-Value Database"""
    
    def __init__(self, config: Dict):
        if not REDIS_AVAILABLE:
            logger.warning("Redis library not available at import time; connect() will fail if used")
        
        self.config = config
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 6379)
        self.db = config.get('db', 0)
        self.password = config.get('password')
        self.decode_responses = config.get('decode_responses', True)
        self.client = None
        # Defensive UDS3 strategy initialization
        try:
            if callable(get_unified_database_strategy):
                self.strategy = get_unified_database_strategy()
            else:
                self.strategy = None
        except Exception as exc:
            logger.warning(f"UDS3 strategy initialization failed for Redis: {exc}")
            self.strategy = None
        strategy_version = getattr(self.strategy, 'version', 'UDS3') if self.strategy else 'UDS3'
        logger.info(f"Redis Backend initialisiert mit Strategie {strategy_version}")
        self.connection = None
        
    def connect(self) -> bool:
        try:
            connection_params = {
                'host': self.host,
                'port': self.port,
                'db': self.db,
                'decode_responses': self.decode_responses,
                'socket_timeout': 5
            }
            
            if self.password:
                connection_params['password'] = self.password
            
            self.connection = redis.Redis(**connection_params)
            
            # Test connection
            self.connection.ping()
            
            logging.info(f"Redis verbunden: {self.host}:{self.port}/{self.db}")
            return True
            
        except Exception as e:
            logging.error(f"Redis Verbindung fehlgeschlagen: {e}")
            return False
    
    def disconnect(self):
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def is_available(self) -> bool:
        try:
            if self.connection:
                self.connection.ping()
                return True
        except:
            pass
        return False
    
    def get_backend_type(self) -> str:
        return "Redis"
    
    # Key-Value Operations
    def set(self, key: str, value: Any, expire: int = None) -> bool:
        """
        Setzt einen Key mit beliebigen Metadaten/Properties (inkl. Relationen) als JSON-Value.
        """
        try:
            if not self.connection:
                logging.error("Redis connection not established. Call connect() first.")
                return False

            value_json = json.dumps(value)
            # Use the established connection object
            if expire:
                self.connection.set(key, value_json, ex=expire)
            else:
                self.connection.set(key, value_json)
            return True
        except Exception as e:
            logging.error(f"Fehler beim Setzen des Keys: {e}")
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """Hole Value für Key"""
        try:
            if not self.connection:
                return None
            
            value = self.connection.get(key)
            if value is None:
                return None
            
            # Versuche JSON zu deserialisieren
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
                
        except Exception as e:
            logging.error(f"Redis Get fehlgeschlagen: {e}")
            return None
    
    def delete(self, *keys: str) -> int:
        """Lösche Keys"""
        try:
            if not self.connection:
                return 0
            
            return self.connection.delete(*keys)
            
        except Exception as e:
            logging.error(f"Redis Delete fehlgeschlagen: {e}")
            return 0
    
    def exists(self, *keys: str) -> int:
        """Prüfe ob Keys existieren"""
        try:
            if not self.connection:
                return 0
            
            return self.connection.exists(*keys)
            
        except Exception as e:
            logging.error(f"Redis Exists fehlgeschlagen: {e}")
            return 0
    
    def keys(self, pattern: str = "*") -> List[str]:
        """Hole alle Keys mit Pattern"""
        try:
            if not self.connection:
                return []
            
            return self.connection.keys(pattern)
            
        except Exception as e:
            logging.error(f"Redis Keys fehlgeschlagen: {e}")
            return []
    
    def expire(self, key: str, seconds: int) -> bool:
        """Setze Expiration für Key"""
        try:
            if not self.connection:
                return False
            
            return self.connection.expire(key, seconds)
            
        except Exception as e:
            logging.error(f"Redis Expire fehlgeschlagen: {e}")
            return False
    
    def ttl(self, key: str) -> int:
        """Hole Time-To-Live für Key"""
        try:
            if not self.connection:
                return -2
            
            return self.connection.ttl(key)
            
        except Exception as e:
            logging.error(f"Redis TTL fehlgeschlagen: {e}")
            return -2
    
    # Hash Operations
    def hset(self, name: str, mapping: Dict) -> int:
        """Setze Hash Fields"""
        try:
            if not self.connection:
                return 0
            
            # JSON serialisierung für komplexe Values
            processed_mapping = {}
            for key, value in mapping.items():
                if isinstance(value, (dict, list)):
                    processed_mapping[key] = json.dumps(value)
                else:
                    processed_mapping[key] = value
            
            return self.connection.hset(name, mapping=processed_mapping)
            
        except Exception as e:
            logging.error(f"Redis HSet fehlgeschlagen: {e}")
            return 0
    
    def hget(self, name: str, key: str) -> Optional[Any]:
        """Hole Hash Field"""
        try:
            if not self.connection:
                return None
            
            value = self.connection.hget(name, key)
            if value is None:
                return None
            
            # Versuche JSON zu deserialisieren
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
                
        except Exception as e:
            logging.error(f"Redis HGet fehlgeschlagen: {e}")
            return None
    
    def hgetall(self, name: str) -> Dict:
        """Hole alle Hash Fields"""
        try:
            if not self.connection:
                return {}
            
            raw_hash = self.connection.hgetall(name)
            
            # JSON deserialisierung für alle Values
            processed_hash = {}
            for key, value in raw_hash.items():
                try:
                    processed_hash[key] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    processed_hash[key] = value
            
            return processed_hash
            
        except Exception as e:
            logging.error(f"Redis HGetAll fehlgeschlagen: {e}")
            return {}
    
    def hdel(self, name: str, *keys: str) -> int:
        """Lösche Hash Fields"""
        try:
            if not self.connection:
                return 0
            
            return self.connection.hdel(name, *keys)
            
        except Exception as e:
            logging.error(f"Redis HDel fehlgeschlagen: {e}")
            return 0
    
    # List Operations
    def lpush(self, name: str, *values: Any) -> int:
        """Push to List (left)"""
        try:
            if not self.connection:
                return 0
            
            # JSON serialisierung für komplexe Values
            processed_values = []
            for value in values:
                if isinstance(value, (dict, list)):
                    processed_values.append(json.dumps(value))
                else:
                    processed_values.append(value)
            
            return self.connection.lpush(name, *processed_values)
            
        except Exception as e:
            logging.error(f"Redis LPush fehlgeschlagen: {e}")
            return 0
    
    def rpush(self, name: str, *values: Any) -> int:
        """Push to List (right)"""
        try:
            if not self.connection:
                return 0
            
            # JSON serialisierung für komplexe Values
            processed_values = []
            for value in values:
                if isinstance(value, (dict, list)):
                    processed_values.append(json.dumps(value))
                else:
                    processed_values.append(value)
            
            return self.connection.rpush(name, *processed_values)
            
        except Exception as e:
            logging.error(f"Redis RPush fehlgeschlagen: {e}")
            return 0
    
    def lrange(self, name: str, start: int = 0, end: int = -1) -> List[Any]:
        """Get List Range"""
        try:
            if not self.connection:
                return []
            
            raw_list = self.connection.lrange(name, start, end)
            
            # JSON deserialisierung
            processed_list = []
            for item in raw_list:
                try:
                    processed_list.append(json.loads(item))
                except (json.JSONDecodeError, TypeError):
                    processed_list.append(item)
            
            return processed_list
            
        except Exception as e:
            logging.error(f"Redis LRange fehlgeschlagen: {e}")
            return []
    
    def llen(self, name: str) -> int:
        """Get List Length"""
        try:
            if not self.connection:
                return 0
            
            return self.connection.llen(name)
            
        except Exception as e:
            logging.error(f"Redis LLen fehlgeschlagen: {e}")
            return 0
    
    # Set Operations
    def sadd(self, name: str, *values: Any) -> int:
        """Add to Set"""
        try:
            if not self.connection:
                return 0
            
            # JSON serialisierung für komplexe Values
            processed_values = []
            for value in values:
                if isinstance(value, (dict, list)):
                    processed_values.append(json.dumps(value))
                else:
                    processed_values.append(value)
            
            return self.connection.sadd(name, *processed_values)
            
        except Exception as e:
            logging.error(f"Redis SAdd fehlgeschlagen: {e}")
            return 0
    
    def smembers(self, name: str) -> set:
        """Get Set Members"""
        try:
            if not self.connection:
                return set()
            
            raw_set = self.connection.smembers(name)
            
            # JSON deserialisierung
            processed_set = set()
            for item in raw_set:
                try:
                    processed_set.add(json.loads(item))
                except (json.JSONDecodeError, TypeError):
                    processed_set.add(item)
            
            return processed_set
            
        except Exception as e:
            logging.error(f"Redis SMembers fehlgeschlagen: {e}")
            return set()
    
    def scard(self, name: str) -> int:
        """Get Set Cardinality"""
        try:
            if not self.connection:
                return 0
            
            return self.connection.scard(name)
            
        except Exception as e:
            logging.error(f"Redis SCard fehlgeschlagen: {e}")
            return 0
    
    # Database Operations
    def flushdb(self) -> bool:
        """Lösche alle Keys in aktueller DB"""
        try:
            if not self.connection:
                return False
            
            self.connection.flushdb()
            return True
            
        except Exception as e:
            logging.error(f"Redis FlushDB fehlgeschlagen: {e}")
            return False
    
    def info(self) -> Dict:
        """Redis Server Info"""
        try:
            if not self.connection:
                return {}
            
            return self.connection.info()
            
        except Exception as e:
            logging.error(f"Redis Info fehlgeschlagen: {e}")
            return {}
    
    def dbsize(self) -> int:
        """Anzahl Keys in DB"""
        try:
            if not self.connection:
                return 0
            
            return self.connection.dbsize()
            
        except Exception as e:
            logging.error(f"Redis DBSize fehlgeschlagen: {e}")
            return 0
    
    # Cache-spezifische Methoden
    def cache_set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """Cache Value mit Standard Expiration"""
        return self.set(f"cache:{key}", value, expire)
    
    def cache_get(self, key: str) -> Optional[Any]:
        """Hole Cache Value"""
        return self.get(f"cache:{key}")
    
    def cache_delete(self, key: str) -> int:
        """Lösche Cache Value"""
        return self.delete(f"cache:{key}")
    
    def session_set(self, session_id: str, data: Dict, expire: int = 1800) -> bool:
        """Session Data speichern"""
        return self.hset(f"session:{session_id}", data) and self.expire(f"session:{session_id}", expire)
    
    def session_get(self, session_id: str) -> Dict:
        """Session Data abrufen"""
        return self.hgetall(f"session:{session_id}")
    
    def session_delete(self, session_id: str) -> int:
        """Session löschen"""
        return self.delete(f"session:{session_id}")


def get_backend_class():
    """Factory-Funktion für Redis Backend"""
    return RedisKeyValueBackend

"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys. 
Modification will be detected and may result in license violations.
"""

# === VERITAS PROTECTION KEYS (DO NOT MODIFY) ===
module_name = "database_api_redis"
module_licenced_organization = "VERITAS_TECH_GMBH"
module_licence_key = "eyJjbGllbnRfaWQi...NvOJ4zw="  # Gekuerzt fuer Sicherheit
module_organization_key = "55b19155192b35a721ff6bc424065c85deb10704a8bce2ad36b83db2ea88f015"
module_file_key = "f1c46ed416fac7a1725b77eb2599a83608f9f8438739472cdf6b4422e1590c54"
module_version = "1.0"
module_protection_level = 3
# === END PROTECTION KEYS ===
