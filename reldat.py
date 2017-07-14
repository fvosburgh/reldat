import socket
import md5
import pickle
from threading import Thread, Lock
from io import BytesIO

class Reldat:

    MAX_PAYLOAD_SIZE = 1000
    WINDOW_SIZE = 0

    recv_buff = BytesIO()

    # Since we're writing to this buffer in another thread, we need a mutex
    recv_buff_mutex = Lock()


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

    # This function is a wrapper for the receving thread start function for
    # the socket. This should only be called once.
    def listen(socket):
        recv_window = 1048
        socket.start_receive(recv_window, recv_buff, recv_buff_mutex)

    def get_data():
        while recv_buff.getvalue() is 0:
            pass
        #TODO parse the buffer into packets to be deserialized
        # working regex (?<!\\x)(\d{2,3}\.){3}\d{1,3}
        # has issues in interpreter, dont know why yet

        # Use pickle protocol 0 for ascii encoding, then convert to string
        # before regexing?





class ReldatSocket:

    #TODO remove erronious prints when done testing

    #TODO do we need threading?
    # Use this mutex to control when to throttle the listening threading
    throttle_mutex = Lock()

    # Use this mutex to ensure that we're not listening when we're trying to
    # send on the socket and vice versa
    socket_mutex = Lock()

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

    # The socket is considered connected only when the 3-way handshake is
    # complete. We leave this work to the Reldat protocol encapsulated class.
    def connected(self):
        self.state = "connected"

    def close(self):
        self._socket.close()
        self.state = "closed"

    def send(self, packet, dest_addr):

        #NOTE
        # some concern about deadlock here. What if we're stuck listening
        # because nothing is coming in, but we want to send data still?
        # Can we rely on a timeout of some sort for listening?
        socket_mutex.acquire()
        self._socket.sendto(packet.serialize(), dest_addr)
        socket_mutex.release()

    def throttle(self):
        throttle_mutex.acquire()
        self.throttle = True
        throttle_mutex.release()

    def remove_throttle(self):
        throttle_mutex.acquire()
        self.throttle = False
        throttle_mutex.release()

    # This function spawns a thread that continuously receives data
    # on the socket. The thread runs as a daemon so that it is non blocking
    # on program termination
    def start_receive(recv_window_size, recv_buffer, recv_buffer_mutex):
        t = Thread(target = receive, args = (recv_window_size, recv_buffer,
                                             recv_buffer_mutex))
        t.setDaemon(True)
        t.start()

    #TODO better timeout calculation
    # This needs to be a threaded function since we will always be Listening
    # for incoming packets from various connections

    #TODO
    # How should we handle a changing window size? Is it appropriate to even
    # use window size here?
    def receive(self, recv_window_size, recv_buffer, recv_buffer_mutex):
        while True and not self.throttle:
            try:
                socket_mutex.acquire()
                data, addr = self._socket.recvfrom(int(recv_window_size))
                socket_mutex.release()
                recv_buffer_mutex.acquire()
                recv_buffer.write(bytes(addr, encoding='ascii') + data)
                recv_buffer_mutex.release()
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
