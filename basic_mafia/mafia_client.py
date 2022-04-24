import logging
import asyncio
import threading

import grpc
import mafia_pb2 as pb2
import mafia_pb2_grpc as pb2_grpc

from client_tcp import Client


class MafiaClient:
    def __init__(self, address):
        self.voice_chat_client = Client()

        # start voice chat client
        threading.Thread(
            target=self.voice_chat_client.send_data_to_server, daemon=True).start()

        # connect to server
        channel = grpc.insecure_channel(address)
        self.conn = pb2_grpc.MafiaServerStub(channel)

        # start listening for messages
        threading.Thread(target=self.__listen_for_messages,
                         daemon=True).start()

        self.running = True
        self.playing = False

    async def run(self) -> None:
        # login
        name = input('Enter login: ')
        password = input('Enter password ')

        addr = self.voice_chat_client.addr[0]
        port = self.voice_chat_client.addr[1]

        resp = self.conn.ConnectClient(pb2.ConnectRequest(
            login=name, password=password, voiceChatServerAddr=addr, voiceChatServerPort=port))
        print(
            f"client received: {pb2.Result.Name(resp.result)} {resp.message}")

        if pb2.Result.Name(resp.result) != "OK":
            return

        # connect to room
        room_name = input('Enter room name: ')
        resp = self.conn.ConnectToSpecificRoom(
            pb2.ConnectToRoomRequest(room=room_name))
        print(
            f"client received: {pb2.Result.Name(resp.result)} {resp.message}")

        self.voice_chat_client.logged_in = True
        self.voice_chat_client.connected_to_room = True

        if pb2.Result.Name(resp.result) != "OK":
            return

        # wait for game to start
        print(f'Waiting for game to start...')
        while self.running and not self.playing:
            pass

        # game started
        self.round = 0

        while self.running:
            # daytime
            print(
                f'Day {self.round} started, possible actions: vote, end, exit, mute')

            self.voted = False

            while self.running and self.playing and self.is_day:
                action = input(f'What would you like to do? ')
                if action == 'vote':
                    if self.round == 0:
                        print('Can not vote on round 0')
                        continue

                    player_name = input(
                        'Which player do you want to vote for? ')
                    resp = self.conn.VoteForMafia(pb2.Player(name=player_name))

                    if pb2.Result.Name(resp.result) == "OK":
                        self.voted = True
                        print('ok')

                elif action == 'end':
                    if not self.voted and self.round:
                        print('You have to vote for someone')
                        continue

                    print('You have entered command "End day"')
                    resp = self.conn.EndDay(pb2.Empty())
                    # stop entering commands
                    if pb2.Result.Name(resp.result) == "OK":
                        break
                elif action == 'exit':
                    self.running = False
                    return
                elif action == 'mute':
                    self.voice_chat_client.muted = not self.voice_chat_client.muted
                    print(f'Muted = {self.voice_chat_client.muted}')
                else:
                    print('Unknown action')

                if pb2.Result.Name(resp.result) != "OK":
                    print(
                        f"Error: {pb2.Result.Name(resp.result)} {resp.message}")

            # waiting for day to end
            print('Waiting for other players to end day')
            while self.is_day and self.running and self.playing:
                pass

            print('Night time')

            while self.running and self.playing and not self.is_day:
                if self.role == 'mafia':
                    victim = input('Who do you want to shoot? ')
                    resp = self.conn.VoteToKill(pb2.Player(name=victim))
                    if pb2.Result.Name(resp.result) == "OK":
                        print('ok')
                        break
                elif self.role == 'commissar':
                    target = input('Who do you want to check? ')
                    resp = self.conn.CheckPlayer(pb2.Player(name=target))
                    if pb2.Result.Name(resp.result) == "OK":
                        print(f'{resp.message}')
                        break
                else:
                    break

            print('Waiting for other players to finish night activities')
            while self.running and self.playing and not self.is_day:
                pass

    def __listen_for_messages(self):
        for message in self.conn.GetMessages(pb2.Empty()):
            print(
                f'Received message: {pb2.MessageType.Name(message.type)} - {message.message}')
            if pb2.MessageType.Name(message.type) == "GameEnded":
                self.running = False
                self.playing = False
                break
            elif pb2.MessageType.Name(message.type) == "AssignedRole":
                self.role = message.message
                self.playing = True
                self.is_day = True
            elif pb2.MessageType.Name(message.type) == "DayEnded":
                self.round += 1
                print('Day ended')
                self.is_day = False
            elif pb2.MessageType.Name(message.type) == "NightEnded":
                print('Night ended')
                self.is_day = True
            elif pb2.MessageType.Name(message.type) == "YouWereKilled":
                print('You were killed')
                self.running = False
                self.playing = False
                break


if __name__ == '__main__':
    logging.basicConfig()
    address = input(
        'Enter mafia server address (e.g. localhost:50051): ').strip()
    client = MafiaClient(address)
    asyncio.run(client.run())
