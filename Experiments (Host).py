import socket
import select
import sys
import traceback as tb

HOST = "172.20.102.211"
PORT = 0
sock=''

def excepthook(type, value, traceback):
    global sock
    temp=tb.format_tb(traceback)
    print(type.__name__)
    print(value)
    for i in range(len(temp)):
        print(f"{temp[i]}\n")
    sock.close()

sys.excepthook=excepthook
sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.setblocking(False)
sock.bind((HOST, PORT))
print(f"PORT: {sock.getsockname()[1]}")
sock.listen()

while True:
    read, write, error=select.select([sock],[sock],[sock],0)
    if sock in read:
        sock, addr= sock.accept()
        break

print(f"Connected: {addr}")

while True:
    double_break=False
    read, write, error=select.select([sock],[sock],[sock],0)
    if sock in read:
        data=sock.recv(1024).decode()
        if data != '':
            data=data.split("END")
        for datum in data:
            if datum == "STOP":
                double_break=True
                break
            if datum != '':
                print(datum)
    if sock in write:
        pass
    if sock in error:
        raise RuntimeError("Sockets, am I right?")
    if double_break:
        print(f"{'\033[93m'}INT_SYS: Ending connection.{'\033[0m'}")
        sock.close()
        break