from __future__ import annotations
import os

ENABLE_LEGAL_GRAPH_NLP = os.getenv("ENABLE_LEGAL_GRAPH_NLP", "false").lower() == "true"
ENABLE_CONFIG_HOT_RELOAD = os.getenv("ENABLE_CONFIG_HOT_RELOAD", "false").lower() == "true"
AUTO_CONFIG_MODE = os.getenv("AUTO_CONFIG_MODE", "shadow")
