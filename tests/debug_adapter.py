import logging
logging.basicConfig(level=logging.INFO)

from database.database_api_postgresql import PostgreSQLRelationalBackend

config = {
    'host': '192.168.178.94',
    'port': 5432,
    'username': 'postgres',
    'password': 'postgres',
    'database': 'postgres'
}

print("Creating adapter...")
adapter = PostgreSQLRelationalBackend(config)

print(f"Adapter object: {adapter}")
print(f"Adapter.__dict__ BEFORE connect: {adapter.__dict__}")

print("\nCalling connect()...")
success = adapter.connect()

print(f"\nConnect returned: {success}")
print(f"Adapter.__dict__ AFTER connect: {adapter.__dict__}")
print(f"Has 'connection' attribute: {hasattr(adapter, 'connection')}")

if hasattr(adapter, 'connection'):
    print(f"Connection value: {adapter.connection}")
    print(f"Connection type: {type(adapter.connection)}")
else:
    print("NO CONNECTION ATTRIBUTE!")
