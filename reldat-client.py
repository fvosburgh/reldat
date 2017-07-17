import socket
import sys
import signal
from reldat import *

def main():

    # check input arguments
    try:
        if len(sys.argv) != 3:
            raise Exception("Usage: reldat-client <host>:<port> <max window recv size>")
    except Exception as error:
        print(repr(error))
        sys.exit()

    # arg parsing
    addrstr = int(str(sys.argv[1]))
    addr,port = addrstr.split(":")
    window_size = int(str(sys.argv[2]))

    # set up socket
    socket = ReldatSocket()

    print("Please enter a command")
    print("Options are: transform and disconnect")

    # command loop
    while True:
        cmd = input("Command: ").split(" ")

        if len(cmd) > 2:
            print("invalid command")
            continue
        elif len(cmd) == 1 and cmd is "disconnect"
            disconnect()
        elif len(cmd) == 1 and cmd is not "disconnect"
            print("invalid command")
            continue
        elif len(cmd) == 2
            if cmd[0] is not "transform":
                print("invalid command")
                continue
            elif cmd[0] is "transform":
                filename = cmd[1]
                connection = connect(socket, addr, window_size)
                if connection is -1:
                    print("Could not establish connection to server")
                elif connection is 0:
                    print("Server terminated connection")
                else:
                    new_file = transform(filename)
                continue

    def connect(socket, addr, window_size):
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

if __name__ == "__main__": main()


























    # 1. CONNECT TO SERV PROCEDURE
    connection = setup(addr, port)

    # 2. TRANSFORM COMMAND & SENDING PROCEDURE
    activeClient(connection)

    # 3. DISCONNECT PROCEDURE
    teardown()

def setup(addr, port):
    print "Setting up connection to server..."
    try:
        udp_socket = createSocket(addr, port)
        connection = connect(udp_socket, addr)
        print "Connection successful."
        return connection
    except Exception as error:
        print(repr(error))
        print "Connection failed."
        sys.exit()

def activeClient(connection):
    while 1:
        input_str = raw_input("Command: ")
        command,filename = input_str.split(" ")
        if command == "transform":
            transform(filename, connection)
        elif command == "disconnect":
            teardown()
        else:
            print "Usage: transform <txt file>"
            print "OR disconnect"

def transform(filename):
    try:
        file_object = open(filename, "r")
        file_string = file_object.read()
        file_object.close()

        # send file_string as packet to server
        send_data(udp_socket, file_string, connection)

    except Exception as error:
        print(repr(error))
        print "File must exist in this directory and be a txt file. Please try again or disconnect."

def teardown():
    print "Closing connection to server..."
    try:
        udp_socket.close()
        print "Disconnection successful."
    except Exception as error:
        print(repr(error))
        print "Disconnection failed."

    # just exit here?
    sys.exit()
