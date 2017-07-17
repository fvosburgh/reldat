import socket
import hashlib
import pickle
import sys
import time
from threading import Thread, Lock
from io import BytesIO

class Reldat:

    MAX_PAYLOAD_SIZE = 1000
    MAX_RECV_SIZE = 3200 # max packet size is around 3100, add more for safety

    window = 0

    # pickle delimmeter for each dump is \x80\x04\x95#
    # the # after \x95 denotes an object rather than a primitive
    # Also look into using '.' as the delimmeter. Looks like pickle adds
    # a period after every dump

    def createSocket(addr, port):
        sock = ReldatSocket()
        sock.bind(addr, port)
        return sock

    def set_window(size):
        window = size

    # listen for and accept an incoming connection and complete the handshake
    # SERVER SIDE
    def accept(socket):
        client_syn_packet = receive_data(socket)

        # if client_syn_packet is legit
        syn_ack_packet = ReldatPacket()
        syn_ack_packet.header = PacketHeader()
        syn_ack_packet.header.syn = 1
        syn_ack_packet.header.ack = 1

        send_data(socket, syn_ack_packet, connection)

    # initiate a connection
    # CLIENT SIDE
    # We are essentially doing a two way handshake because we don't need to
    # synchronize seq/ack nums, we always start at 0. Third packet in handshake
    # is just the first sent packet
    def connect(socket, addr): # Do we need socket AND addr?
        syn_packet = ReldatPacket()
        syn_packet.header = PacketHeader()
        syn_packet.header.syn = 1
        syn_packet.source_addr = socket.gethostname()
        syn_packet.dest_addr = addr

        connection = Connection()
        connection.addr = addr

        send_data(socket, syn_packet, connection)

        while 1:
            syn_ack_packet = receive_data(socket)
            if syn_ack_packet is not None:
                if syn_ack_packet.verify():
                    print "Handshake successful."
                    return connection
                else:
                    print "Handshake failed."
                    break

    # send all data to remote
    def send_data(socket, data, connection):
        #1. determine number of packets needed to be sent
        num_packets = int(MAX_PAYLOAD_SIZE / len(data))
        if (MAX_PAYLOAD_SIZE % len(data)) is not 0:
            num_packets += 1

        #2. Packetize the data and store in dict

        # get the current seq_num for connection. Caclulate each packets
        # seq_num using this as a because
        curr_seq_num = connection.get_seq_num

        packets_to_send = {}
        for i in range(num_packets):
            seg_start = MAX_PAYLOAD_SIZE * i
            seg_end = (MAX_PAYLOAD_SIZE * i) + MAX_PAYLOAD_SIZE
            if num_packets - 1 == i:
                payload = data[seg_start:]
                curr_seq_num += len(payload)
                header = PacketHeader()
                header.seq_num = curr_seq_num
                header.fin = 1
                packet = ReldatPacket(header, payload)
                packets_to_send.update({str(curr_seq_num) : packet})
            else:
                payload = data[seg_start:seg_end]
                curr_seq_num += len(payload)

                header = PacketHeader()
                header.seq_num = curr_seq_num
                header.window = window
                packet = ReldatPacket(header, payload)
                packets_to_send.update({str(curr_seq_num) : packet})

        # reset seq num for indexing into packets_to_send
        curr_seq_num = connection.get_seq_num

        # add payload length of first packet to send to current ack_num
        # to get the next desired ack
        next_ack_num = connection.get_ack_num() +  \
                       len(packets_to_send[str(curr_seq_num)].data)

        #3. Send window sized batch of packets

        # pop sent packets off to_send dict into to_ack dict
        packets_to_ack = {}

        receiver_window = connection.get_receiver_window_size
        sender_window = receiver_window

        while len(packets_to_send) > 0:

            # send batch of packets the size of the recv_window
            while receiver_window > 0:
                packet = packets_to_send[str(curr_seq_num)].serialize()
                padded_packet = pad_packet(packet)
                socket.send(padded_packet, connection.addr)

                # remove packet that was sent from dict and add to waiting to be
                # acked
                packets_to_ack.update({str(curr_seq_num) : packet})
                del packets_to_send[str(curr_seq_num)]

                curr_seq_num += packet.header.payload_length
                receiver_window -= 1

            # get acks for send packets and update recv window
            # use try block to handle timeouts
            while sender_window > 0:
                try:
                    addr, padded_packet = socket.receive(MAX_RECV_SIZE)

                    # concern about error handling here. Differentiate between
                    # timeout and packet corruption?
                    packet = pickle.loads(padded_packet)

                    if not isinstance(type(packet), Reldatpacket.Reldatpacket) or packet.verify():
                        # invalid packet so drop it
                        # ALSO CHECK TO SEE IF THE PACKET IS EVEN OF TYPE PACKET
                        pass
                    else:
                        # implement comparing sequence nums here
                        # go-back-n implementation
                        if packet.header.ack_num < next_ack_num:
                            # sent packet lost in network, need to resend
                            # also check to see if we didn't already get a higher ack
                            # e.g this could be a dup ack. consult the packets_to_be_acked dict
                            # ordered data structure for queued packets?
                            pass
                        elif packet.header.ack_num > next_ack_num:
                            # received out of order ack packet
                            # we can update next ack num since we know any preceding
                            # waiting to be acked packets have been received by the client
                            # use the seq num in this packet to determine next ack num
                            # as in line 78
                            # BE SURE TO REMOVE PACKET FROM packet_to_ack
                            pass
                        elif packet.header.ack_num is next_ack_num:
                            # update next ack num using method above
                            pass
                except socket.timeout:
                    # HANDLE TIMEOUTS
                    pass

        # implement this method to signal to the client that the data transfer is over
        # put some identifying text in the payload or something
        signal_transfer_end(socket)






    # receive all data from remote
    def receive_data(socket):
        pass

    def pad_packet(packet):
        # bytearray adds 57 bytes of overhead, so account for that
        padding_size = MAX_RECV_SIZE - sys.getsizeof(packet) - 57
        return packet + bytearray(paddingsize)

    def signal_transfer_end(socket):
        pass

class Connection:
    def __init__(self, addr = None, sn = 0, an = 0, rws = 0):
        self.addr = addr
        self.seq_num = sn
        self.ack_num = an
        self.receiver_window_size = rws

    def seq_num(seq_num):
        self.seq_num = seq_num

    def get_seq_num():
        return self.seq_num

    def ack_num(ack_num):
        self.ack_num = ack_num

    def get_ack_num():
        return self.ack_num

    def receiver_window_size(size):
        self.receiver_window_size = size

    def get_receiver_window_size(size):
        return self.receiver_window_size

class ReldatSocket:

    #TODO remove erronious prints when done testing
    def __init__(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Keep track of socket state for error handling
        self.state = "init"

        # Start with 10 second timeout
        self._socket.settimeout(10)

        self.source_addr = None
        self.dest_addr = None

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
            self._socket.sendto(packet, dest_addr)
        except Exception as e:
            print("Socket error while sending: ", e)

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
        return self.checksum() == self.header.checksum

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
        for key, value in self.__dict__.items():
            if key is not 'checksum':
                retval += str(value)
        return retval
