from __future__ import annotations
from typing import Optional

class Neo4jClient:
    def __init__(self, uri: str, user: str, password: str) -> None:
        self.uri = uri
        self.user = user
        self.password = password
        self._driver = None  # lazy

    def is_connected(self) -> bool:
        return self._driver is not None
