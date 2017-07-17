import socket
import sys
import signal
from reldat import *

def connect_to_server(socket, addr, window_size):
    return connect(socket, addr, window_size)

def transform(filename, socket, connection):
    lowercase = ""
    with open(filename, "r") as data:
        lowercase = data.read()
    retval = send_data(socket, "TRANSFORM" + lowercase, connection)
    if retval == -1:
        print("Connection timed out")
    else:
        print("file sent\n")
        transformed_file = receive_data(socket, connection)
        new_filename = filename.split('.')
        new_filename = new_filename[0] + "-received." + new_filename[1]
        with open(new_filename, 'w') as data:
            data.write(transformed_file)
        print("File written")

def disconnect(socket, connection):
    if type(connection) is Connection:
        print("Disconnecting")
        close_connection(socket, connection)
    else:
        print("\nNo connection to disconnect")

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
    connection = ""

    print("Please enter a command")
    print("Options are: transform and disconnect")

    # command loop
    while True:
        try:
            cmd = input("Command: ").split(" ")

            if len(cmd) > 2:
                print("invalid command")
                continue
            elif len(cmd) == 1:
                if str(cmd[0]) == "disconnect":
                    disconnect(socket, connection)
                elif str(cmd[0]) !=  "disconnect":
                    print("invalid command")
                    continue
            elif len(cmd) == 2:
                if str(cmd[0]) != "transform":
                    print("invalid command", str(cmd[0]))
                    continue
                elif str(cmd[0]) == "transform":
                    filename = str(cmd[1])
                    print("Connecting..")
                    connection = connect_to_server(socket, (addr,port), window_size)
                    if connection is -1:
                        print("Could not establish connection to server")
                    elif connection is 0:
                        print("Server terminated connection")
                    else:
                        print("====================================\n")
                        print("Connected")
                        print("sending file to transform")
                        print("====================================\n")
                        transform(filename, socket, connection)
                    continue
        except KeyboardInterrupt:
            disconnect(socket, connection)
            print("Exiting\n")
            sys.exit()

if __name__ == "__main__": main()
