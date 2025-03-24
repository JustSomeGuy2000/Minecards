import socket
import select

HOST = "127.0.0.1"  # The server's hostname or IP address
PORT = 65432  # The port used by the server

'''
Steps to make client socket:
1. Make socket object: s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
2. Connect to host (blocks until connected or failed): s.connect((HOST, PORT))
'''

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    #s.setblocking(False)
    s.connect((HOST, PORT))
    print(str(s.send(b"Connected")))
    data = s.recv(1024)
    print(f"Client: {data}")
    s.send(data)