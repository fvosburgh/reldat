import socket
import md5
import pickle
from threading import Thread, Lock
from io import BytesIO

class Reldat:

    # pickle delimmeter for each dump is \x80\x04\x95#
    # the # after \x95 denotes an object rather than a primitive
    # Also look into using '.' as the delimmeter. Looks like pickle adds
    # a period after every dump

    def createSocket(addr, port):
        sock = ReldatSocket()
        sock.bind(addr, port)
        return sock



class ReldatSocket:

    #TODO remove erronious prints when done testing

    #TODO do we need threading?
    # Use this mutex to control when to throttle the listening threading
    throttle_mutex = Lock()

    def __init__(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Keep track of socket state for error handling
        self.state = "init"

        # Start with 10 second timeout
        self._socket.settimeout(10)

        # Need to keep track of
        self.source_addr = None
        self.dest_addr = None

        # This determines whether or not we need to stop receiving so that the
        # protocol can finish processing the recv_buffer
        throttle_mutex.acquire()
        self.throttle = False
        throttle_mutex.release()

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

    # The socket is considered connected only when the 3-way handshake is
    # complete. We leave this work to the Reldat protocol encapsulated class.
    def connected(self):
        self.state = "connected"

    def close(self):
        self._socket.close()
        self.state = "closed"

    def send(self, packet):
        self._socket.sendto(packet.serialize(), self.dest_addr)

    def throttle(self):
        throttle_mutex.acquire()
        self.throttle = True
        throttle_mutex.release()

    def remove_throttle(self):
        throttle_mutex.acquire()
        self.throttle = False
        throttle_mutex.release()

    #TODO better timeout calculation
    # This needs to be a threaded function since we will always be Listening
    # for incoming packets from various connections
    def receive(self, recv_window_size, recv_buffer):
        while True and not self.throttle:
            try:
                data, addr = self._socket.recvfrom(int(recv_window_size))
                recv_buffer.write(data)
            except Exception as e:
                print("Socket error while receiving: ", e)



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

        # We stringify the header to have data for the packet checksum
        def to_string(self):
            retval = ""
            for attr, value in self.__dict__.items():
                if attr != "checksum":
                    retval += value
            return retval

        # END PACKETHEADER CLASS

    def __init__(self, data = None):
        self.header = PacketHeader()
        self.data = data or ' '
        self.header.payload_length = len(self.data)
        self.header.checksum = checksum()

    def checksum(self):
        return md5.new(self.header.to_string + self.data).digest()

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
