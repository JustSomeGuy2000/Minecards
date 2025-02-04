import socket
import selectors

HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
PORT = 65432  # Port to listen on (non-privileged ports are > 1023)
sel=selectors.DefaultSelector()

s= socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))
s.listen()
s.setblocking(False)
sel.register(s, selectors.EVENT_READ, data=None)

def accept_wrapper(sock):
    conn, addr = sock.accept()  # Should be ready to read
    print(f"Accepted connection from {addr}")
    conn.setblocking(False) #as accept returns a new socket, it needs to be unblocked again 
    data = types.SimpleNamespace(addr=addr, inb=b"", outb=b"")
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    sel.register(conn, events, data=data)

try:
    while True:
        events=sel.select(timeout=None)
        for key, mask in events:
            if key.data == None: #socket looking to connect
                accept_wrapper(key.file_obj)
            else: #already connected socket looking for information
                service_connection(key,mask)
except:
    pass
finally:
    sel.close()