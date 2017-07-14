import socket

class Reldat:


class ReldatSocket:

    def __init__(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Keep track of socket state for error handling
        self.state = "init"

        # Start with 10 second timeout
        self._socket.settimeout(10)

        # Need to keep track of
        self.source_addr = None
        self.dest_addr = None

        print("Socket initialized")

    def bind(self, ip_addr, port):
        addr = (ip_addr, port)
        self.source_addr = addr
        self._socket.bind(addr)
        self.state = "bound"
        print("Socket bound to port", str(port))

    def set_dest(self, ip_addr, port):
        addr = (ip_addr, port)
        self.dest_addr = addr

class ReldatPacket:
    class PacketHeader:
        def __init__(self):
            self.source_port = 0
            self.dest_port = 0
            self.seq_num = 0
            self.ack_num = 0
            self.syn = 0
            self.ack = 0
            self.fin = 0
            self.window = 0
            self.checksum = 0
            self.payload_length = 0

    def __init__(self, data = None):
        self.header = PacketHeader()
        self.data = data or ' '
        self.header.payload_length = len(self.data)
        self.header.checksum = checksum()

    def checksum(self):
