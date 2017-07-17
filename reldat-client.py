import socket
import sys
import signal
from reldat import *

def connect_to_server(socket, addr, window_size):
    return connect(socket, addr, window_size)

def transform(filename, connection):
    lowercase = ""
    with open(filename, "r") as data:
        lowercase = data.read()
    send_data(socket, "TRANSFORM" + lowercase, connection)
    transformed_file = receive_data(socket, connection)
    return transformed_file

def disconnect(socket, connection):
    close_connection(socket, connection)

def main():

    # check input arguments
    try:
        if len(sys.argv) != 3:
            raise Exception("Usage: reldat-client <host>:<port> <max window recv size>")
    except Exception as error:
        print(repr(error))
        sys.exit()

    # arg parsing
    addrstr = str(sys.argv[1])
    addr,port = addrstr.split(":")
    port = int(port)
    window_size = int(str(sys.argv[2]))

    # set up socket
    socket = ReldatSocket()

    print("Please enter a command")
    print("Options are: transform and disconnect")

    # command loop
    while True:
        try:
            cmd = input("Command: ").split(" ")

            if len(cmd) > 2:
                print("invalid command")
                continue
            elif len(cmd) == 1 and cmd is "disconnect":
                disconnect()
            elif len(cmd) == 1 and cmd is not "disconnect":
                print("invalid command")
                continue
            elif len(cmd) == 2:
                if str(cmd[0]) != "transform":
                    print("invalid command", str(cmd[0]))
                    continue
                elif str(cmd[0]) == "transform":
                    filename = str(cmd[1])
                    connection = connect_to_server(socket, (addr,port), window_size)
                    if connection is -1:
                        print("Could not establish connection to server")
                    elif connection is 0:
                        print("Server terminated connection")
                    else:
                        new_file = transform(filename)
                    continue
        except KeyboardInterrupt:
            disconnect()
            sys.exit()

if __name__ == "__main__": main()
