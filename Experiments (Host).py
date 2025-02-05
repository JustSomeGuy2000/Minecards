import socket
import select

HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
PORT = 65432  # Port to listen on (non-privileged ports are > 1023)

'''
Steps to make host socket:
1. Make socket object: s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
2. Bind: s.bind((HOST, PORT))
3. Start listening: s.listen()
4. Start accepting connections (blocks until a connection is accepted): s.accept()

Notes:
 - Send info over the socket: s.send(b), b is a bytes object
 - Blocks until sent, but this time is inconsequential for small data.
 - Receive info from the socket: s.recv(int), receives at maximum int bytes from the socket
 - Blocks until the socket has something to receive. Very problematic.
'''

s= socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))
s.listen()
s.setblocking(False)

