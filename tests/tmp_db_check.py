import traceback
print('sys.path[0]=', __import__('sys').path[0])
try:
    from database import database_api_base as base
    from database import database_api_chromadb as chroma
    from database import database_manager as manager_mod
    from database import config as cfg
    print('Imported base, chroma, manager, config')
    Cls = getattr(chroma, 'ChromaVectorBackend', None)
    print('ChromaVectorBackend present:', Cls is not None)
    if Cls:
        inst = Cls({'host':'127.0.0.1','port':8000,'timeout':0.2})
        print('Chroma instantiated type:', type(inst))
        try:
            print('chroma.connect():', inst.connect())
        except Exception as e:
            print('connect() raised:', e)
    backend_instances = cfg.get_database_backend_dict()
    print('backend_instances keys:', list(backend_instances.keys()))
    dm = manager_mod.DatabaseManager(backend_instances)
    print('DatabaseManager created:', type(dm))
    print('vector backend:', type(dm.vector_backend) if getattr(dm, 'vector_backend', None) else None)
    print('relational backend:', type(dm.relational_backend) if getattr(dm, 'relational_backend', None) else None)
except Exception:
    traceback.print_exc()
finally:
    print('done')
