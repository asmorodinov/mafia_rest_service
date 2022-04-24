#!/usr/bin/python3

import json
import os
import sys
import socket
import threading
import pyaudio
import getch

from protocol_tcp import Message, MessageType, MessageStruct


class Client:
    def login(self):
        try:
            self.name = input('Enter login --> ')
            Message.send(MessageType.Login, self.name.encode(), self.s)
        except BaseException as err:
            if self.debug:
                print(f'login err {type(err)} - {err}', flush=True)

    def connect_to_room(self):
        try:
            self.room_name = input('Enter room name --> ')
            Message.send(MessageType.ConnectToRoom,
                         self.room_name.encode(), self.s)
        except BaseException as err:
            if self.debug:
                print(f'connect to room err {type(err)} - {err}', flush=True)

    def __init__(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.running = True
        self.muted = False

        self.logged_in = False
        self.connected_to_room = False

        self.debug = True

        while 1:
            try:
                self.target_ip = input(
                    '[VC] Enter IP address of server --> ').strip()
                # self.target_ip = socket.gethostbyname(self.target_ip)

                self.target_port = int(
                    input('[VC] Enter target port of server --> ').strip())

                self.s.connect((self.target_ip, self.target_port))
                # self.s.connect(('192.168.64.1', 1111))

                break
            except:
                print("[VC] Couldn't connect to server", flush=True)

        print(f'[VC] addr: {self.s.getsockname()}', flush=True)
        self.addr = self.s.getsockname()

        chunk_size = 1024  # 512
        audio_format = pyaudio.paInt16
        channels = 1
        rate = 20000

        # initialise microphone recording
        self.p = pyaudio.PyAudio()
        self.playing_stream = self.p.open(
            format=audio_format, channels=channels, rate=rate, output=True, frames_per_buffer=chunk_size)
        self.recording_stream = self.p.open(
            format=audio_format, channels=channels, rate=rate, input=True, frames_per_buffer=chunk_size)

        print("[VC] Connected to Server", flush=True)

        # start thread
        receive_thread = threading.Thread(target=self.receive_server_data)
        receive_thread.daemon = True
        receive_thread.start()

    def handle_console_input(self):
        print(
            "Press 'x' to e[X]it application, 'm' to [M]ute, 'r' to [R]econnect, 'o' to view list of [O]nline users,", flush=True)
        print(
            "'l' to [L]eave room, 'c' to [C]onnect to room, 'g' to lo[G]in", flush=True)

        while self.running:
            try:
                c = getch.getch()
                # c = input().encode()

                if c == b'x':
                    print('Exiting...', flush=True)

                    # notify server just in case
                    Message.send(
                        MessageType.ClientCloseConnection, b'', self.s)

                    self.s.close()
                    self.running = False
                elif c == b'm':
                    self.muted = not self.muted
                    print(f'muted = {self.muted}', flush=True)
                elif c == b'o':
                    Message.send(MessageType.GetActiveList, b'', self.s)
                elif c == b'l':
                    Message.send(MessageType.LeaveRoom, b'', self.s)
                    self.connected_to_room = False
                    print('Left room', flush=True)
                elif c == b'c':
                    self.connect_to_room()
                elif c == b'g':
                    self.login()
            except BaseException as err:
                print(
                    f'handle_console_input error: {type(err)} - {err}', flush=True)

    def receive_server_data(self):
        while self.running:
            try:
                message = Message.recv(self.s)
                if message.header == MessageType.AudioData:
                    self.playing_stream.write(message.data)
                elif message.header == MessageType.GetActiveListResponse:
                    users = json.loads(message.data.decode())
                    print(f'Users online: {users}', flush=True)
                elif message.header == MessageType.InfoFromServer:
                    print('[Info]', message.data.decode(), flush=True)
                elif message.header == MessageType.LoginResponse:
                    if message.data == b'ok':
                        print('Logged in successfully', flush=True)
                        self.logged_in = True
                    else:
                        print(f'Log in failed: {message.data}')
                elif message.header == MessageType.ConnectToRoomResponse:
                    if message.data == b'ok':
                        print('Connected to room', flush=True)
                        self.connected_to_room = True
                    else:
                        print(f'Connection to room failed: {message.data}')

            except BaseException as err:
                if self.debug:
                    print(f'receive: {type(err)} - {err}', flush=True)
                break

    def send_data_to_server(self):
        while self.running:
            if self.muted or not self.logged_in or not self.connected_to_room:
                continue
            try:
                # send audio data
                data = self.recording_stream.read(1024)
                Message.send(MessageType.AudioData, data, self.s)
            except BaseException as err:
                if self.debug:
                    print(f'send: {type(err)} - {err}', flush=True)
                break
