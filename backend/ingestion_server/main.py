from __future__ import annotations
import uvicorn
from .app_factory import get_app

if __name__ == "__main__":
    uvicorn.run(get_app(), host="127.0.0.1", port=45679)
