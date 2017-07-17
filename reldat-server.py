import sys
from reldat import *


window_size = 0

socket = ReldatSocket()

def main():

    # check CLI arguments
    try:
        if len(sys.argv) != 3:
            raise Exception("Usage: reldat-server <port> <max window recv size>")
    except Exception as error:
        print(repr(error))
        sys.exit()

    port = int(str(sys.argv[1]))
    setup(port)

    window_size = int(str(sys.argv[2]))

    while True:
        try:
            connection = accept(socket, window_size)
            print("====================================\n")
            print("Connection from: ", connection.addr)
            print("====================================\n")
            recv_data = receive_data(socket, connection)
            if recv_data == -1:
                print("Connection timed out")
            elif "TRANSFORM" in recv_data:
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
