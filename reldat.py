import socket
import hashlib
import pickle
import sys
from threading import Thread, Lock
from io import BytesIO

class Reldat:

    MAX_PAYLOAD_SIZE = 1000
    MAX_RECV_SIZE = 3200 # max packet size is around 3100, add more for safety
    MAX_TIMEOUTS = 5

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
    def accept(socket, window):
        header = PacketHeader()
        header.ack = 1
        header.syn = 1
        header.seq_num = 0
        header.window = window
        syn_packet = ReldatPacket(header)
        syn_packet.source_addr = socket.gethostname()

        connection = Connection()

        while True:
            try:
                addr, packet = socket.receive(MAX_RECV_SIZE)
                packet = pickle.loads(syn_packet)
                if type(packet) is ReldatPacket:
                    if packet.verify() and is_syn(packet):
                        send_syn_ack(socket, 1, addr)
                    elif packet.verify() and is_ack(packet):
                        connection.addr = addr
                        connection.seq_num = packet.header.ack_num
                        connection.ack_num = 1
                        connection.receiver_window_size = packet.header.window
                        return connection
            except socket.timeout:
                continue
            except TypeError:
                continue


    # initiate a connection
    # CLINET SIDE
    def connect(socket, addr, window):
        header = PacketHeader()
        header.syn = 1
        header.seq_num = 0
        header.window = window
        syn_packet = ReldatPacket(header)
        syn_packet.source_addr = socket.gethostname()
        syn_packet.dest_addr = addr

        socket.send(pad_packet(syn_packet.serialize()), addr)

        connection = Connection()
        connection.addr = addr

        while True:
            try:
                addr, syn_ack_packet = socket.receive(MAX_PAYLOAD_SIZE)
                syn_ack_packet = pickle.loads(syn_ack_packet)
                if type(syn_ack_packet) is ReldatPacket:
                    if syn_ack_packet.verify() and is_syn_ack(syn_ack_packet):
                        print("Handshake successful.")
                        connection.seq_num = syn_ack_packet.header.ack_num
                        connection.ack_num = 1
                        connection.receiver_window_size = syn_ack_packet.header.window
                        send_ack(socket, 1, addr)
                        return connection
                    else:
                        print("Handshake failed.")
                        return -1
            except socket.timeout:
                print("Handshake timeout")
                return -1
            except TypeError:
                print("Got mangled SYNACK")
                return -1

    # send all data to remote
    def send_data(socket, data, connection):
        #1. determine number of packets needed to be sent
        num_packets = int(MAX_PAYLOAD_SIZE / sys.getsizeof(data))
        if (MAX_PAYLOAD_SIZE % sys.getsizeof(data)) is not 0:
            num_packets += 1

        #2. Packetize the data and store in dict

        # get the current seq_num for connection. Caclulate each packets
        # seq_num using this as a because
        curr_seq_num = connection.get_seq_num() + 1

        packets_to_send = {}
        for i in range(num_packets):
            seg_start = MAX_PAYLOAD_SIZE * i
            seg_end = (MAX_PAYLOAD_SIZE * i) + MAX_PAYLOAD_SIZE
            if num_packets - 1 == i:
                payload = data[seg_start:]
                curr_seq_num += 1
                header = PacketHeader()
                header.seq_num = curr_seq_num
                packet = ReldatPacket(header, payload)
                packets_to_send.update({curr_seq_num : packet})
            else:
                payload = data[seg_start:seg_end]
                curr_seq_num += 1
                header = PacketHeader()
                header.seq_num = curr_seq_num
                header.window = window
                packet = ReldatPacket(header, payload)
                packets_to_send.update({curr_seq_num : packet})

        # reset seq num for indexing into packets_to_send
        curr_seq_num = connection.get_seq_num() + 1

        # add payload length of first packet to send to current ack_num
        # to get the next desired ack
        next_ack_num = curr_seq_num

        #3. Send window sized batch of packets

        # pop sent packets off to_send dict into to_ack dict
        packets_to_ack = {}

        # keep track of timeouts
        timeouts = 0


        while len(packets_to_send) > 0 or len(packets_to_ack) > 0:

            receiver_window = connection.get_receiver_window_size - len(packets_to_ack)
            sender_window = connection.get_receiver_window_size

            # send batch of packets the size of the recv_window
            while receiver_window > 0 and len(packets_to_send) > 0:
                packet = packets_to_send[curr_seq_num].serialize()
                padded_packet = pad_packet(packet)
                print("SEND: sending packet: ", packet.header.seq_num)
                socket.send(padded_packet, connection.addr)

                # remove packet that was sent from dict and add to waiting to be
                # acked
                packets_to_ack.update({curr_seq_num : packet})
                del packets_to_send[curr_seq_num]

                curr_seq_num += 1
                receiver_window -= 1

            # get acks for send packets and update recv window
            # use try block to handle timeouts
            while sender_window > 0 and len(packets_to_ack) > 0:
                try:
                    addr, padded_packet = socket.receive(MAX_RECV_SIZE)

                    # concern about error handling here. Differentiate between
                    # timeout and packet corruption?
                    packet = pickle.loads(padded_packet)

                    if not type(packet) is ReldatPacket or not packet.verify():
                        # invalid packet so drop it
                        print("SEND: Packet not verified or wrong type. Type: ", type(packet))
                    else:
                        if packet.payload == "RELDAT_TIMEOUT":
                            print("SEND: Connection timeout at receiver. Closing")
                            return -1
                        # implement comparing sequence nums here
                        # go-back-n implementation
                        elif packet.header.ack_num < next_ack_num:
                            # delayed ack, drop it
                            print("SEND: Received ack less than expected: ", (packet.header.ack_num, next_ack_num))
                            if packet.header.ack_num in packets_to_ack:
                                del packets_to_ack[packet.header.ack_num]
                            sender_window -= 1
                        elif packet.header.ack_num > next_ack_num:
                            # received out of order ack packet
                            # can use this ack as the most recent
                            print("SEND: Received higher than expected ack ", (packet.header.ack_num, next_ack_num))
                            for i in range(next_ack_num, packet.header.ack_num + 1):
                                del packet_to_ack[i]
                            sender_window -= 1
                            next_ack_num = packet.header.ack_num + 1

                            connection.seq_num = packet.header.ack_num

                        elif packet.header.ack_num is next_ack_num:
                            # update next ack num using method above
                            print("SEND: recv next ack num: ", next_ack_num)
                            del packet_to_ack[next_ack_num]
                            next_ack_num += 1

                            connection.seq_num = packet.header.ack_num
                            sender_window -= 1



                except socket.timeout:
                    print("SEND: socket timeout. resending...")
                    timeouts += 1
                    if timeouts == MAX_TIMEOUTS:
                        print("SEND: max timeouts. closing connection")
                        signal_transfer_end(socket, connection, "RELDAT_TIMEOUT")
                        return -1
                    else:
                        continue
                except TypeError:
                    print("SEND: mangled packet waiting for", next_ack_num)
                    sender_window -= 1
                    continue

            # add any missed acks back to sender queue
            for i in packet_to_ack:
                packets_to_send.update({i : packet_to_ack[i]})

            # after getting acks, reset packets to send index to the next ack
            # expected
            curr_seq_num = next_ack_num

        # implement this method to signal to the client that the data transfer is over
        # put some identifying text in the payload or something
        signal_transfer_end(socket, connection, "RELDAT_FINISHED")

    # receive all data from remote
    def receive_data(socket, connection):

        # keep track of timeouts
        timeouts = 0
        transfer_done  = False
        data_buff = ""
        curr_seq_num = connection.get_ack_num()

        while True:
            recv_window = connection.get_receiver_window_size()
            while recv_window > 0:
                try:
                    addr, packet = socket.receive(MAX_RECV_SIZE)
                    packet = pickle.loads(packet)
                    recv_window -= 1
                    if not type(packet) is ReldatPacket or not packet.verify():
                        # invalid packet so drop it
                        print("RECV: Packet not verified or wrong type. Type: ", type(packet))
                    else:
                        if packet.payload == "RELDAT_TIMEOUT":
                            print("RECV: sender timeout. closing connection")
                            return -1
                        elif packet.payload == "RELDAT_CLOSE":
                            print("RECV: connection closed")
                            return 0
                        elif packet.header.seq_num == curr_seq_num:
                            print("RECV: got next expected packet: ", curr_seq_num)
                            send_ack(curr_seq_num, addr)
                            curr_seq_num += 1
                            if packet.payload == "RELDAT_FINISHED":
                                print("RECV: transfer complete")
                                return data_buff
                            else:
                                data_buff += packet.payload
                        elif packet.header.seq_num > curr_seq_num:
                            print("RECV: got higher order packet: ", curr_seq_num)
                            send_ack(curr_seq_num, addr)
                        elif packet.header.seq_num < curr_seq_num:
                            print("RECV: got duplicate packet. Dropping")

                except socket.timeout:
                    print("RECV: socket timeout")
                    timeouts += 1
                    if timeouts == MAX_TIMEOUTS:
                        print("RECV: max timeouts reached. closing")
                        signal_transfer_end(socket, connection, "RELDAT_TIMEOUT")
                        return -1
                    else:
                        continue
                except TypeError:
                    print("RECV: mangled packet.")
                    recv_window -= 1
                    send_ack(socket, curr_seq_num)
                    continue

    def close_connection(socket, connection):
        header = PacketHeader()
        packet = ReldatPacket(header, "RELDAT_CLOSE")
        socket.send(packet, connection.addr)

    def send_ack(socket, seq_num, addr):
        header = PacketHeader()
        header.ack_num = seq_num
        header.ack = 1
        packet = ReldatPacket(header)
        socket.send(packet, addr)

    def send_syn_ack(socket, seq_num):
        header = PacketHeader()
        header.ack_num = seq_num
        header.syn = 1
        header.ack = 1
        packet = ReldatPacket(header)
        socket.send(packet, addr)

    def is_syn(packet):
        return packet.header.syn == 1

    def is_syn_ack(packet):
        return packet.header.syn == 1 and packet.header.ack == 1

    def is_ack(packet):
        return packet.header.ack == 1

    def pad_packet(packet):
        # bytearray adds 57 bytes of overhead, so account for that
        padding_size = MAX_RECV_SIZE - sys.getsizeof(packet) - 57
        return packet + bytearray(paddingsize)

    def signal_transfer_end(socket, connection, data):
        header = PacketHeader()
        header.seq_num = connection.get_seq_num
        packet = pad_packet(ReldatPacket(header, data).serialize())
        socket.send(packet, connection.addr)


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
            data, addr = self._socket.recvfrom(int(recv_size))
            retval = (addr, pickle.loads(data, protocol=pickle.HIGHEST_PROTOCOL))
            break
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
