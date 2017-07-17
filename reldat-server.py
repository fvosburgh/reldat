import sys
from reldat import *


window_size = 0

socket = ReldatSocket()

def main():

    # check CLI arguments
    try:
        if len(sys.argv) != 4:
            raise Exception("Usage: reldat-server <port> <max window recv size>")
    except Exception as error:
        print(repr(error))
        sys.exit()

    port = int(str(sys.argv[2]))
    setup(port)

    window_size = int(str(sys.argv[3]))

    while True:
        try:
            connection = accept(socket, window_size)
            recv_data = receive_data(socket, connection)
            if "TRANSFORM" in recv_data:
                transform_and_send(recv_data.split(" ")[1], connection)
        except KeyboardInterrupt:
            disconnect(socket, connection)
            print("Exiting")

def setup(port):
    server_addr = '0.0.0.0'
    socket.bind(server_addr, port)

def transform_and_send(filename, connection):
    lowercase = ""
    with open(filename, "r") as data:
        lowercase = data.read()
    send_data(socket, lowercase.upper(), connection)

def disconnect(socket, connection):
    close_connection(socket, connection)


if __name__ == "__main__": main()
