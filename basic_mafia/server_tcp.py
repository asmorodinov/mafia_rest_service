#!/usr/bin/python3

import json
import socket
import threading

from protocol_tcp import Message, MessageType, MessageStruct


class Server:
    def __init__(self):
        while 1:
            try:
                hostname = socket.gethostname()
                local_ip = socket.gethostbyname(hostname)
                print("VC: name - ", hostname, "ip - ", local_ip, flush=True)

                self.ip = local_ip
                self.port = int(input('VC: enter server port number --> '))
                # self.port = 1111

                self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.s.bind((self.ip, self.port))

                break
            except:
                print("Couldn't bind to that port", flush=True)

        # some basic info about connections
        self.connections = []
        self.addresses = []

        # logins
        self.login_to_address = {}
        self.address_to_login = {}

        # rooms
        self.login_to_room = {}
        self.room_to_logins = {}

        print('Initialized voice chat server', flush=True)

    def accept_connections(self):
        self.s.listen(100)

        print('Running on IP: '+self.ip, flush=True)
        print('Running on port: '+str(self.port), flush=True)

        while True:
            c, addr = self.s.accept()

            self.connections.append(c)
            self.addresses.append(addr)

            print(f'Accepted connection {addr}', flush=True)
            print(
                f'{len(self.connections)} active connections: {self.addresses}', flush=True)

            threading.Thread(target=self.handle_client,
                             args=(c, addr,)).start()

    def broadcast(self, sock, room, message_type, data):
        if room is None:
            print('[Warning] Someone is trying to send data to None room', flush=True)
            return

        for i, client in enumerate(self.connections):
            addr = self.addresses[i]
            if addr in self.address_to_login and client != self.s and client != sock:
                login = self.address_to_login[addr]

                if login in self.login_to_room and self.login_to_room[login] == room:
                    try:
                        Message.send(message_type, data, client)
                    except:
                        pass

    def remove_connection(self, c, addr):
        login = self.address_to_login.pop(addr, None)
        room = self.login_to_room.pop(login, None)

        # send info to other members of the room
        if login is not None and room is not None:
            self.broadcast(c, room, MessageType.InfoFromServer,
                           f'User {login} left the room'.encode())

        print(
            f'Closed connection with {addr} login = "{login}", room = "{room}"', flush=True)

        self.login_to_address.pop(login, None)
        self.room_to_logins.get(room, set()).discard(login)

        self.connections.remove(c)
        self.addresses.remove(addr)
        print(
            f'{len(self.connections)} active connections: {self.addresses}', flush=True)

        c.close()

    def client_leave_room(self, c, addr, login):
        if login is None:
            return

        room = self.login_to_room.pop(login, None)
        if room is None:
            return

        self.broadcast(c, room, MessageType.InfoFromServer,
                       f'User {login} left the room'.encode())
        print(f'User {login} left room "{room}"', flush=True)

        self.room_to_logins.get(room, set()).discard(login)

    def login_client(self, c, addr, message):
        if message.header == MessageType.Login:
            login = message.data.decode()

            if login in self.login_to_address:
                Message.send(MessageType.LoginResponse, b'Login is taken', c)
                return None

            print(f'{addr} Logged in as "{login}"', flush=True)

            Message.send(MessageType.LoginResponse, b'ok', c)

            self.login_to_address[login] = addr
            self.address_to_login[addr] = login

            return login

        return None

    def connect_client_to_room(self, c, addr, login, message):
        if message.header == MessageType.ConnectToRoom:
            room = message.data.decode()

            if login is None:
                Message.send(MessageType.ConnectToRoomResponse,
                             b'only logged in users can connect to rooms', c)
                return None

            Message.send(MessageType.ConnectToRoomResponse, b'ok', c)
            self.login_to_room[login] = room
            self.room_to_logins[room] = self.room_to_logins.get(room, set()) | {
                login}

            # send some welcome info
            info = f'User {login}, welcome to the room "{room}"!\n'
            info += f'Room members: {list(self.room_to_logins[room])}'
            Message.send(MessageType.InfoFromServer, info.encode(), c)

            # send info to other members of the room
            self.broadcast(c, room, MessageType.InfoFromServer,
                           f'User {login} connected to the room'.encode())

            print(f'"{login}" connected to room "{room}"', flush=True)

            return room
        return None

    def handle_get_active_list_request(self, c, addr, room, message):
        if room not in self.room_to_logins:
            Message.send(MessageType.GetActiveListResponse,
                         b'invalid room name', c)
            return

        users = list(self.room_to_logins[room])
        resp_data = json.dumps(users).encode()
        Message.send(MessageType.GetActiveListResponse, resp_data, c)

    def handle_client(self, c, addr):
        while 1:
            try:
                login = self.address_to_login.get(addr, None)
                room = self.login_to_room.get(login, None)

                message = Message.recv(c)

                if message.header == MessageType.Login:
                    # handle login
                    self.login_client(c, addr, message)
                elif message.header == MessageType.ConnectToRoom:
                    # handle connect to room
                    self.connect_client_to_room(c, addr, login, message)
                elif message.header == MessageType.AudioData and room is not None:
                    # broadcast audio data
                    self.broadcast(
                        c, room, MessageType.AudioData, message.data)
                elif message.header == MessageType.GetActiveList:
                    # handle getActiveList request
                    self.handle_get_active_list_request(c, addr, room, message)
                elif message.header == MessageType.LeaveRoom:
                    self.client_leave_room(c, addr, login)
                elif message.header == MessageType.ClientCloseConnection:
                    self.remove_connection(c, addr)
                    break

            except socket.error:
                self.remove_connection(c, addr)
                break
