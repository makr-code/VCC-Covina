from database.database_api_couchdb import CouchDBAdapter

cfg = {
    'host': '192.168.178.94',
    'port': 32931,
    'username': 'admin',
    'password': 'admin',
    'db': 'test_batch_operations'
}

print("Testing CouchDB connection...")
adapter = CouchDBAdapter(cfg)
success = adapter.connect()

print(f"Connection: {'✅ SUCCESS' if success else '❌ FAILED'}")
if success:
    print(f"Database: {adapter.db_name}")
    print(f"Server: {adapter.server}")
    adapter.disconnect()
else:
    print("Could not connect to CouchDB")
