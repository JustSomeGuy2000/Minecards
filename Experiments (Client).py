import socket
import select
import sys
import traceback as tb

HOST = "172.20.102.211"
PORT = int(input("Input PORT > "))
#172.20.102.211

def excepthook(type, value, traceback):
    global sock
    temp=tb.format_tb(traceback)
    print(type.__name__)
    print(value)
    for i in range(len(temp)):
        print(f"{temp[i]}\n")
    sock.close()

sys.excepthook=excepthook

def create():
    sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setblocking(False)
    return sock

sock=create()

while True:
    try:
        sock.connect((HOST, PORT))
        break
    except OSError as exc:
        if exc.errno == 10057 or exc.errno == 10022:
            sock.close()
            print("This PORT is not connected. Please connect to a different one.")
            PORT=int(input("Input PORT > "))
            sock=create()
        elif exc.errno == 10056:
            sock.send("HandshakeEND".encode())
            break
        elif exc.errno != 115 and exc.errno != 10035 and exc.errno != 10056:
            sock.close()
            raise

sock.send("Hello Internet!END".encode())
print(f"Connected: {sock.getpeername()}")
while True:
    msg=input("Message (STOP to stop) > ")
    sock.send((msg+"END").encode())
    if msg == "STOP":
        print(f"{'\033[93m'}INT_SYS: Ending connection.{'\033[0m'}")
        sock.close()
        break