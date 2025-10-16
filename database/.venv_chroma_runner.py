
import chromadb
from chromadb.server import create_app
app = create_app(persist_directory=r'Y:\VCC\Covina\database\chroma_db')
import uvicorn
uvicorn.run(app, host='0.0.0.0', port=8000)
