import socket
import sys
import signal

max_payload = 1000
window_size = 0

# set up UDP socket
udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

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

    try:
        listen()
    except KeyboardInterrupt:
        teardown()
        print "Exiting"

def setup(port):
    server_addr = ('0.0.0.0', port)
    udp_socket.bind(server_addr)

def teardown()
