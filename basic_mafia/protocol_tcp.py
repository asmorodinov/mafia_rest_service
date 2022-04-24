import struct
import enum

class MessageType(enum.IntEnum):
    InvalidMessage = 0, # most likely this will be returned if socket is closed
    Login = 1
    GetActiveList = 2
    AudioData = 3
    LoginResponse = 4
    GetActiveListResponse = 5,
    ConnectToRoom = 6,
    ConnectToRoomResponse = 7,
    InfoFromServer = 8,
    LeaveRoom = 9,
    ClientCloseConnection = 10,

class MessageStruct:
    def __init__(self, header, data):
        self.header = header
        self.data = data

    def to_bytes(self):
        bytearr = bytearray(b'')
        bytearr.append(self.header)
        return bytes(bytearr + self.data)

    @staticmethod
    def from_bytes(bytes_data):
        if bytes_data is None:
            return MessageStruct(MessageType.InvalidMessage, b'')

        header = MessageType(bytes_data[0])
        data = bytes_data[1:]
        return MessageStruct(header, data)

def recvall(sock, n):
    # Helper function to recv n bytes or return None if EOF is hit
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data.extend(packet)
    return bytes(data)

class Message:
    # public methods
    @staticmethod
    def send(header, data, socket):
        Message.__from_header_data(header, data).__send(socket)

    @staticmethod
    def recv(socket):
        return MessageStruct.from_bytes(Message.__recv(socket).data)

    def __init__(self, data):
        self.data = data

    # private members
    @staticmethod
    def __from_header_data(header, data):
        return Message(MessageStruct(header, data).to_bytes())

    def __send(self, socket):
        socket.sendall(self.__out())

    @staticmethod
    def __data_length(buffer):
        length = struct.unpack_from(">I", buffer, 0)[0]
        return length

    def __out(self):
        length = len(self.data)

        return struct.pack(">I", length) + self.data

    @staticmethod
    def __recv(socket):
        length_buffer = recvall(socket, 4)

        if length_buffer is None:
            return Message(None)

        length = Message.__data_length(length_buffer)
        data_buffer = recvall(socket, length)

        return Message(data_buffer)
