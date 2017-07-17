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
            print("handshake done")
            print(connection.addr)
            recv_data = receive_data(socket, connection)
            if "TRANSFORM" in recv_data:
                print("transforming data")
                data = recv_data.split("TRANSFORM")[1]
                transform_and_send(data, connection)
        except KeyboardInterrupt:
            disconnect(socket, connection)
            print("Exiting")
            sys.exit()

def setup(port):
    server_addr = '0.0.0.0'
    socket.bind(server_addr, port)

def transform_and_send(data, connection):
    print("Strating transform")
    send_data(socket, data.upper(), connection)

def disconnect(socket, connection):
    close_connection(socket, connection)


if __name__ == "__main__": main()
