from concurrent import futures
import threading
import logging
import grpc
import mafia_pb2 as pb2
import mafia_pb2_grpc as pb2_grpc
import random
from datetime import datetime

from server_tcp import Server

import requests
import json


class GameState:
    def __init__(self, players, seed=None):
        self.players = list(players)  # copy players list
        self.round = 0
        self.is_day = True

        self.n = len(self.players)

        # set random seed
        self.seed = seed
        if self.seed is None:
            self.seed = datetime.now().timestamp()
        random.seed(self.seed)

        # assign roles
        shuffled_list = list(self.players)  # copy and shuffle players list
        random.shuffle(shuffled_list)

        assert(self.n == 4)
        self.mafias = {shuffled_list[0]}
        self.commissars = {shuffled_list[1]}
        self.civilians = {shuffled_list[2], shuffled_list[3]}

        logging.info(
            f'Game is initialised, mafias: {self.mafias}, commissars: {self.commissars}, civilians: {self.civilians}')

        self.roles = {}
        for mafia in self.mafias:
            self.roles[mafia] = 'mafia'
        for commissar in self.commissars:
            self.roles[commissar] = 'commissar'
        for civilian in self.civilians:
            self.roles[civilian] = 'civilian'

        self.is_dead = {player: False for player in self.players}

        self.vote = {player: None for player in self.players}
        self.end_day_vote = {player: False for player in self.players}

        self.startTime = datetime.now()

    def check_winning_condition(self):
        mafias = 0
        civilians = 0
        for mafia in self.mafias:
            mafias += 1 - int(self.is_dead[mafia])
        for civilian in self.civilians:
            civilians += 1 - int(self.is_dead[civilian])
        for commissar in self.commissars:
            civilians += 1 - int(self.is_dead[commissar])

        if not mafias:
            return True, 'Civilians'
        if mafias >= civilians:
            return True, 'Mafia'

        return False, ''

    def check_day_end(self):
        voted = 0
        ended_day = 0
        alive = 0
        votes = {}

        for player in self.players:
            if self.is_dead[player]:
                continue
            alive += 1
            if self.vote[player] is not None:
                voted += 1
                votes[self.vote[player]] = votes.get(self.vote[player], 0) + 1
            if self.end_day_vote[player]:
                ended_day += 1

        if not self.round and ended_day == alive:
            return True, set()

        if voted == alive and ended_day == alive:
            max_votes = max(votes.values())
            voted_for = set()
            for k, v in votes.items():
                if v == max_votes:
                    voted_for.add(k)

            return True, voted_for
        return False, set()

    def check_night_end(self):
        mafia_voted = 0
        commissars_checked = 0
        mafia = 0
        commissars = 0
        votes = {}

        for player in self.mafias:
            if self.is_dead[player]:
                continue

            mafia += 1
            if self.vote[player] is not None:
                mafia_voted += 1
                votes[self.vote[player]] = votes.get(self.vote[player], 0) + 1

        for player in self.commissars:
            if self.is_dead[player]:
                continue

            commissars += 1
            if self.vote[player] is not None:
                commissars_checked += 1

        if mafia_voted < mafia or commissars_checked < commissars:
            return False, set()

        voted_for = set()
        for k, v in votes.items():
            if v == mafia:
                voted_for.add(k)

        return True, voted_for

    def end_day(self):
        self.vote = {player: None for player in self.players}
        self.end_day_vote = {player: False for player in self.players}
        self.round += 1
        self.is_day = False

    def end_night(self):
        self.vote = {player: None for player in self.players}
        self.end_day_vote = {player: False for player in self.players}
        self.is_day = True


class MafiaServer(pb2_grpc.MafiaServerServicer):
    def __init__(self):
        self.voice_chat_server = Server()
        # start voice chat server
        threading.Thread(
            target=self.voice_chat_server.accept_connections, daemon=True).start()

        # login info
        self.login_to_address = {}
        self.address_to_login = {}

        self.login_to_voice_chat_address = {}

        # room info
        self.room_to_logins = {}
        self.login_to_room = {}

        # list of messages
        self.messages = []

        # settings
        self.max_room_size = 4

        # game state (when the game is running)
        self.room_to_state = {}

        self.restServiceAddr = input("Enter REST service address ").strip()

        self.secretCode = "jfdsfndsfksdnfk"

    # login with some name to mafia server
    def ConnectClient(self, request: pb2.ConnectRequest, context) -> pb2.Response:
        logging.info(
            f'ConnectClient {{login="{request.login}", password="{request.password}"}} - {context.peer()}')

        login = request.login
        password = request.password

        r = requests.get(self.restServiceAddr + "/signin",
                         data=json.dumps({'login': login, 'password': password}))
        if r.status_code != 200:
            return pb2.Response(result=pb2.Result.Unauthorized, message='Failed to authorize (wrong password)')

        address = context.peer()

        if login in self.login_to_address:
            return pb2.Response(result=pb2.Result.LoginTaken, message='login is taken')

        if address in self.address_to_login:
            return pb2.Response(result=pb2.Result.AlreadyLoggedIn, message='you are already logged in')

        # login to voice chat
        vc_addr = (request.voiceChatServerAddr, request.voiceChatServerPort)

        if login in self.voice_chat_server.login_to_address:
            return pb2.Response(result=pb2.Result.LoginTaken, message='[VC] login is taken')

        self.voice_chat_server.login_to_address[login] = vc_addr
        self.voice_chat_server.address_to_login[vc_addr] = login

        self.login_to_voice_chat_address[login] = vc_addr

        # login to mafia
        self.login_to_address[login] = address
        self.address_to_login[address] = login

        logging.info('{login} successfully logged in')
        logging.debug(f'{self.login_to_address} {self.address_to_login}')

        return pb2.Response(result=pb2.Result.OK, message="ok")

    def __connect_to_voice_chat_room(self, login, room):
        if login not in self.login_to_voice_chat_address:
            return

        logging.debug(f'Connect to voice chat room {login} {room}')

        vc_addr = self.login_to_voice_chat_address[login]

        self.voice_chat_server.login_to_room[login] = room
        self.voice_chat_server.room_to_logins[room] = self.voice_chat_server.room_to_logins.get(
            room, set()) | {login}

    def __leave_voice_chat_room(self, login):
        if login not in self.login_to_voice_chat_address:
            return

        room = self.voice_chat_server.login_to_room.pop(login, None)
        if room is None:
            return

        self.voice_chat_server.room_to_logins.get(room, set()).discard(login)

    # connect to room
    def ConnectToSpecificRoom(self, request: pb2.ConnectToRoomRequest, context) -> pb2.Response:
        logging.info(
            f'ConnectToSpecificRoom {{room="{request.room}"}} - {context.peer()}')

        # address and room
        address = context.peer()
        room = request.room

        # check if logged in
        if address not in self.address_to_login:
            return pb2.Response(result=pb2.Result.Unauthorized, message='You need to login to connect to room')

        login = self.address_to_login[address]

        # check if we are not in this room already
        if login in self.room_to_logins.get(room, set()):
            return pb2.Response(result=pb2.Result.AlreadyInThisRoom, message='You are already in this room')

        # check if we are not in some other room already
        if login in self.login_to_room:
            return pb2.Response(result=pb2.Result.AlreadyInSomeOtherRoom, message='You are already in some other room')

        # check if room is not full
        if len(self.room_to_logins.get(room, set())) >= self.max_room_size:
            return pb2.Response(result=pb2.Result.RoomFull, message='Room is full')

        # add user to the room
        self.room_to_logins[room] = self.room_to_logins.get(room, set()) | {
            login}
        self.login_to_room[login] = room

        self.__connect_to_voice_chat_room(login, room)

        # send welcome message
        self.messages.append({'type': pb2.MessageType.Info,
                             'message': f'Welcome to room "{room}", {login}!', 'to': address})
        self.messages.append({'type': pb2.MessageType.Info,
                             'message': f'Players in the room: {self.room_to_logins[room]}.', 'to': address})

        # send info to other members of the room
        for other in self.room_to_logins[room]:
            if other != login:
                other_address = self.login_to_address[other]
                self.messages.append(
                    {'type': pb2.MessageType.Info, 'message': f'{login} joined room', 'to': other_address})

        logging.info(f'{login} connected successfully to room "{room}"')
        logging.debug(f'{self.room_to_logins}')

        # start game in the room
        if len(self.room_to_logins[room]) == self.max_room_size:
            self.room_to_state[room] = GameState(self.room_to_logins[room])

            # tell players their roles
            for player, role in self.room_to_state[room].roles.items():

                r = requests.post(self.restServiceAddr + "/stats",
                                  data=json.dumps({'login': player, 'password': self.secretCode, 'games_played_delta': 1,
                                                   'games_won_delta': 0, 'games_lost_delta': 0, 'time_played_delta': 0}))
                if r.status_code != 200:
                    logging.error('update stats err code: '+str(r.status_code))

                addr = self.login_to_address[player]
                self.messages.append(
                    {'type': pb2.MessageType.Info, 'message': f'Game is starting!', 'to': addr})
                self.messages.append(
                    {'type': pb2.MessageType.Info, 'message': f'Your role is - {role}', 'to': addr})
                self.messages.append(
                    {'type': pb2.MessageType.AssignedRole, 'message': f'{role}', 'to': addr})

        return pb2.Response(result=pb2.Result.OK, message="ok")

    def __can_perform_action_in_game(self, address):
        # check if logged in
        if address not in self.address_to_login:
            return False, pb2.Response(result=pb2.Result.Unauthorized, message='You need to login to connect to room'), None, None, None

        login = self.address_to_login[address]

        # check if in a room
        if login not in self.login_to_room:
            return False, pb2.Response(result=pb2.Result.NotInRoom, message='You need to connect to room'), None, None, None

        room = self.login_to_room[login]

        # check if game is running
        if room not in self.room_to_state:
            return False, pb2.Response(result=pb2.Result.GameNotRunning, message='Game is not running'), None, None, None

        state = self.room_to_state[room]

        return True, None, login, room, state

    def __end_day_check(self, room, state):
        end, voted_for = state.check_day_end()
        if not end:
            return False

        if voted_for:
            # send info
            for player in state.players:
                if player in self.login_to_address:
                    address = self.login_to_address[player]
                    self.messages.append(
                        {'type': pb2.MessageType.Info, 'message': f'Players voted for {voted_for}', 'to': address})

            # execute players
            for player in voted_for:
                if player in self.login_to_address:
                    address = self.login_to_address[player]
                    self.__disconnect(address)

        # check end game
        self.__check_game_state(room)

        # day ended
        for player in state.players:
            if player in self.login_to_address:
                address = self.login_to_address[player]
                self.messages.append(
                    {'type': pb2.MessageType.DayEnded, 'message': f'Day ended', 'to': address})

        # disconnect non-mafia from voice chat
        for player in state.players:
            if state.is_dead[player]:
                continue
            if state.roles[player] != 'mafia':
                self.__leave_voice_chat_room(player)

        state.end_day()

        return True

    def __end_night_check(self, room, state):
        end, voted_for = state.check_night_end()
        if not end:
            return False

        if voted_for:
            # send info
            for player in state.players:
                if player in self.login_to_address:
                    address = self.login_to_address[player]
                    self.messages.append(
                        {'type': pb2.MessageType.Info, 'message': f'Mafia killed {voted_for}', 'to': address})

            # execute players
            for player in voted_for:
                if player in self.login_to_address:
                    address = self.login_to_address[player]
                    self.__disconnect(address)

        # check end game
        self.__check_game_state(room)

        # night ended
        for player in state.players:
            if player in self.login_to_address:
                address = self.login_to_address[player]
                self.messages.append(
                    {'type': pb2.MessageType.NightEnded, 'message': f'Night ended', 'to': address})

        # connect mafia to voice chat
        for player in state.players:
            if state.is_dead[player]:
                continue
            if state.roles[player] == 'mafia':
                self.__connect_to_voice_chat_room(player, room)

        state.end_night()

        return True

    def VoteToKill(self, request: pb2.Player, context) -> pb2.Response:
        address = context.peer()

        success, err, login, room, state = self.__can_perform_action_in_game(
            address)
        if not success:
            return err

        if state.is_day:
            return pb2.Response(result=pb2.Result.CantVoteDuringNight, message='Can not kill during day time')

        if request.name not in state.players or state.is_dead[request.name]:
            return pb2.Response(result=pb2.Result.IncorrectName, message='Invalid name to choose')

        state.vote[login] = request.name

        self.__end_night_check(room, state)

        return pb2.Response(result=pb2.Result.OK, message='ok')

    def CheckPlayer(self, request: pb2.Player, context) -> pb2.Response:
        address = context.peer()

        success, err, login, room, state = self.__can_perform_action_in_game(
            address)
        if not success:
            return err

        if state.is_day:
            return pb2.Response(result=pb2.Result.CantVoteDuringNight, message='Can not check during day time')

        if request.name not in state.players or state.is_dead[request.name]:
            return pb2.Response(result=pb2.Result.IncorrectName, message='Invalid name to choose')

        state.vote[login] = request.name

        self.__end_night_check(room, state)

        return pb2.Response(result=pb2.Result.OK, message=f'{request.name} is {state.roles[request.name]}')

    def VoteForMafia(self, request: pb2.Player, context) -> pb2.Response:
        address = context.peer()

        success, err, login, room, state = self.__can_perform_action_in_game(
            address)
        if not success:
            return err

        if not state.is_day:
            return pb2.Response(result=pb2.Result.CantVoteDuringNight, message='Can not vote during night time')

        if not state.round:
            return pb2.Response(result=pb2.Result.CantVoteOnFirstDay, message='Can not vote on first day')

        if request.name not in state.players or state.is_dead[request.name]:
            return pb2.Response(result=pb2.Result.IncorrectName, message='Invalid name to vote for')

        state.vote[login] = request.name

        self.__end_day_check(room, state)

        return pb2.Response(result=pb2.Result.OK, message='ok')

    def EndDay(self, request: pb2.Empty, context) -> pb2.Response:
        address = context.peer()

        success, err, login, room, state = self.__can_perform_action_in_game(
            address)
        if not success:
            return err

        if not state.is_day:
            return pb2.Response(result=pb2.Result.CantVoteDuringNight, message='It is already day')

        state.end_day_vote[login] = True

        self.__end_day_check(room, state)

        return pb2.Response(result=pb2.Result.OK, message='ok')

    def __check_game_state(self, room):
        if room not in self.room_to_state:
            return

        state = self.room_to_state[room]
        is_ended, result = state.check_winning_condition()
        if is_ended:
            logging.info("game ended, check_game_state")

            gameEndedTime = datetime.now()
            delta = gameEndedTime - state.startTime

            for player, role in state.roles.items():
                team = 'Civilians'
                if role == 'mafia':
                    team = 'Mafia'

                won = 0
                lost = 0
                if team == result:
                    won = 1
                else:
                    lost = 1

                r = requests.post(self.restServiceAddr + "/stats",
                                  data=json.dumps({'login': player, 'password': self.secretCode, 'games_played_delta': 0,
                                                   'games_won_delta': won, 'games_lost_delta': lost, 'time_played_delta': int(delta.total_seconds() * 1000_000_000)}), timeout=60)

            # notify players that game has ended
            if room in self.room_to_logins:
                for player in self.room_to_logins[room]:
                    address = self.login_to_address[player]
                    self.messages.append(
                        {'type': pb2.MessageType.GameEnded, 'message': f'Game has ended! {result} won.', 'to': address})

            # delete game state (since game has ended)
            self.room_to_state.pop(room, None)

            # disconnect all players
            if room in self.room_to_logins:
                for player in list(self.room_to_logins[room]):
                    if player in self.login_to_address:
                        address = self.login_to_address[player]
                        self.__disconnect(address)

    def __disconnect(self, addr):
        logging.info(f'Client disconnected - {addr}')

        login = self.address_to_login.pop(addr, None)
        room = self.login_to_room.pop(login, None)

        # send info to other members of the room
        if login is not None and room in self.room_to_logins:
            for other in self.room_to_logins[room]:
                if other != login:
                    other_address = self.login_to_address[other]
                    self.messages.append(
                        {'type': pb2.MessageType.Info, 'message': f'{login} left room', 'to': other_address})

        self.login_to_address.pop(login, None)
        self.room_to_logins.get(room, set()).discard(login)

        # mark player as dead if he was playing a game
        if login is not None and room in self.room_to_state:
            self.room_to_state[room].is_dead[login] = True

            self.messages.append(
                {'type': pb2.MessageType.YouWereKilled, 'message': f'You were killed', 'to': addr})

        # check if game is ended as a result
        if login is not None:
            self.__check_game_state(room)

    # send messages to connected client
    def GetMessages(self, request: pb2.Empty, context):
        lastindex = 0

        address = context.peer()

        # infinite loop for every client
        while context.is_active():
            while len(self.messages) > lastindex:
                msg = self.messages[lastindex]
                message = pb2.Message()
                message.type = msg['type']
                message.message = msg['message']

                lastindex += 1

                if msg['to'] == address:
                    yield message

        self.__disconnect(address)


# run server
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    pb2_grpc.add_MafiaServerServicer_to_server(MafiaServer(), server)

    logging.info("Starting server")

    ip = input('Select ip to run server on (e.g. "[::]"): ').strip()
    port = input("Select port to run server on (e.g. 50051): ").strip()

    server.add_insecure_port(ip + ':' + str(port))
    server.start()
    server.wait_for_termination()
