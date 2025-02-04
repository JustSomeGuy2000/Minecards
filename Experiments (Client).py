import socket
import selectors

HOST = "127.0.0.1"  # The server's hostname or IP address
PORT = 65432  # The port used by the server

s= socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))
s.setblocking(False)
print(str(s.send(b"Connected")))
data = s.recv(1024)
print(f"Client: {data}")
s.send(data)