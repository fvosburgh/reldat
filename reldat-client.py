import socket
import sys
import signal

max_payload = 1000
window_size = 0

udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def main():

    # check input arguments
    try:
        if len(sys.argv) != 2:
            raise Exception("Usage: reldat-client <host>:<port> <max window recv size>")
    except Exception as error:
        print(repr(error))
        sys.exit()

    # arg parsing
    addrstr = int(str(sys.argv[0]))
    addr,port = addrstr.split(":")
    window_size = int(str(sys.argv[1]))
    set_window(window_size)

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