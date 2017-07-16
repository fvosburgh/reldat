import socket
import hashlib
import pickle
from threading import Thread, Lock
from io import BytesIO

class Reldat:

    MAX_PAYLOAD_SIZE = 1000
    WINDOW_SIZE = 0

    SYN_SIZE = len()

    # pickle delimmeter for each dump is \x80\x04\x95#
    # the # after \x95 denotes an object rather than a primitive
    # Also look into using '.' as the delimmeter. Looks like pickle adds
    # a period after every dump

    def createSocket(addr, port):
        sock = ReldatSocket()
        sock.bind(addr, port)
        return sock

    def set_window(window_size):
        WINDOW_SIZE = window_size

    # create header
    def header(seq_num, ack_num):
        header = PacketHeader()
        header.seq_num = seq_num
        header.ack_num = ack_num
        return header

    # create syn packet
    def syn(seq_num, ack_num):
        header = header(seq_num, ack_num)
        header.syn = 1
        return ReldatPacket(header)

    # create ack packet
    def ack(seq_num, ack_num):
        header = header(seq_num, ack_num)
        header.ack = 1
        return ReldatPacket(header)

    # create data packet
    def data(seq_num, ack_num, fin = 0, data):
        header = header(seq_num, ack_num)
        header.fin = fin
        return ReldatPacket(header, data)

    # listen for and accept an incoming connection and complete the handshake
    def accept(socket):
        addr, data = socket.receive(247)

class Connection:
    def __init__(self, addr = None):
        self.addr = addr

class ReldatSocket:

    #TODO remove erronious prints when done testing
    def __init__(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Keep track of socket state for error handling
        self.state = "init"

        # Start with 10 second timeout
        self._socket.settimeout(10)

        # We don't need to keep track of dest_addr as the protocol
        # will demux the incoming packets and determine which client to
        # respond to
        self.source_addr = None

        print("Socket initialized")

    def bind(self, ip_addr, port):
        addr = (ip_addr, port)
        self.source_addr = addr
        self._socket.bind(addr)
        self.state = "bound"
        print("Socket bound to port", str(port))

    # The socket is considered connected only when the 3-way handshake is
    # complete. We leave this work to the Reldat protocol encapsulated class.
    def connected(self):
        self.state = "connected"

    def close(self):
        self._socket.close()
        self.state = "closed"

    def send(self, packet, dest_addr):
        try:
            self._socket.sendto(packet.serialize(), dest_addr)
            return 0
        except Exception as e:
            print("Socket error while sending: ", e)
            return -1

    #TODO better timeout calculation
    # This needs to be a threaded function since we will always be Listening
    # for incoming packets from various connections

    #TODO
    # How should we handle a changing window size? Is it appropriate to even
    # use window size here?
    def receive(self, recv_size):
        retval = 0
        while True:
            try:
                data, addr = self._socket.recvfrom(int(recv_size))
                retval = (addr, pickle.loads(data, protocol=pickle.HIGHEST_PROTOCOL))
                break
            except Exception as e:
                print("Socket error while receiving: ", e)
        return retval

class ReldatPacket:

    def __init__(self, header = None, data = None):
        self.header = header or PacketHeader()
        self.data = data or ' '
        self.header.payload_length = len(self.data)
        self.header.checksum = self.checksum()

    def checksum(self):
        s = self.header.to_string().encode('utf-8') + self.data.encode('utf-8')
        return hashlib.md5(s).hexdigest()

    def verify(self):
        # we don't include the checksum in the header when computing the
        # checksum for the packet. So, to verify a checksum, we recompute
        # the packets checksum and compare it to the one in the header
        return checksum() == self.header.checksum

    def serialize(self):
        # use pickle to serialize our objects to be sent over the wire
        # We use the HIGHEST_PROTOCOL to convert to a byte stream rather
        # than a string.
        return pickle.dumps(self, protocol=pickle.HIGHEST_PROTOCOL)

class PacketHeader:
    def __init__(self):
        self.source_port = 0
        self.dest_port = 0

        # sequencing
        self.seq_num = 0
        self.ack_num = 0

        # control
        self.syn = 0
        self.ack = 0
        self.fin = 0

        self.window = 0
        self.checksum = 0
        self.payload_length = 0

    # We stringify the header to have data for the packet checksum
    def to_string(self):
        retval = ""
        for value in self.__dict__.values():
            retval += str(value)
        return retval
