import socket, inspect
print(socket.__file__)
print(hasattr(socket, 'EAI_ADDRFAMILY'), getattr(socket, 'EAI_ADDRFAMILY', None))