from socketserver import *
import enum
from random import choice, randint

host = '26.153.209.176'
port = 777
addr = (host, port)
socket = None
players = []
rooms = []
flag = 0


class RoomStatus(enum.Enum):
    WAIT = 1
    SHIPSETTING = 2
    GAME = 3


class CellType(enum.Enum):
    Empty = 0
    Blocked = 11
    Shot = 12
    Miss = 13
    Ship_4 = 1
    Ship_3_1 = 2
    Ship_3_2 = 3
    Ship_2_1 = 4
    Ship_2_2 = 5
    Ship_2_3 = 6
    Ship_1_1 = 7
    Ship_1_2 = 8
    Ship_1_3 = 9
    Ship_1_4 = 10


class Gamefield:
    def __init__(self):
        self.field = [[CellType.Empty for j in range(10)] for i in range(10)]
        self.shipPositions = ""
        self.isEmpty = True

    def setShips(self, string):
        self.shipPositions = string
        ships = string.split("$")
        for i in range(len(ships)):
            size, vertical, x, y = ships[i].split("|")
            self.setShip(size, vertical, x, y, i + 1)
        self.isEmpty = False

    def setShip(self, size, vertical, x, y, i):
        vertical = vertical == "True"
        if vertical:
            for j in range(int(size) + 2):
                for i1 in range(-1, 2):
                    h, w = int(y) + j - 1, int(x) + i1
                    if 0 <= h <= 9 and 0 <= w <= 9:
                        self.field[h][w] = CellType.Blocked
            for j in range(int(size)):
                self.field[int(y) + j][int(x)] = CellType(i)
        else:
            for j in range(int(size) + 2):
                for i1 in range(-1, 2):
                    h, w = int(y) + i1, int(x) + j - 1
                    if 0 <= h <= 9 and 0 <= w <= 9:
                        self.field[h][w] = CellType.Blocked
            for j in range(int(size)):
                self.field[int(y)][int(x) + j] = CellType(i)

    def clearField(self):
        self.field = [[CellType.Empty for j in range(10)] for i in range(10)]
        self.isEmpty = True


class Player:
    def __init__(self, name, addr):
        self.name = name
        self.addr = addr
        self.room = None
        players.append(self)

    def sendPacket(self, socket, packet):
        socket.sendto(packet.encode(), self.addr)

    def disconnect(self):
        global players, rooms
        if self.room is not None:
            self.room.members.remove(self)
            self.room.update()
            self.room.sendMessage(self.name + " left")
            if self.room.hostPlayer is self:
                for i in range(len(self.room.members)):
                    self.room.kickPlayer(i)
                rooms.remove(self.room)
            if self.room.status == RoomStatus.SHIPSETTING or self.room.status == RoomStatus.GAME:
                for p in self.room.members:
                    if p != "":
                        packet = "room_connection;" + str(self.name)
                        p.sendPacket(socket, packet)
                        self.room.update()
                self.room.status = RoomStatus.WAIT
                self.room.sendMessage("One of the players left, so the game was stopped")

        if self in players:
            players.remove(self)


class Room:
    def __init__(self, hostPlayer):
        self.name = hostPlayer.name
        self.addr = hostPlayer.addr
        self.hostPlayer = hostPlayer
        self.members = ["", "", "", "", ""]
        self.status = RoomStatus.WAIT
        self.connectPlayer(hostPlayer)
        self.hostPlayer.sendPacket(socket, "got_host")
        self.field1 = Gamefield()
        self.field2 = Gamefield()
        self.move = None
        rooms.append(self)

    def connectPlayer(self, player):
        self.members[self.members.index("")] = player
        player.room = self
        packet = "room_connection;" + str(self.name)
        player.sendPacket(socket, packet)
        self.update()

    def setMove(self, move):
        self.move = move
        self.members[move].sendPacket(socket, "move;your")
        for i in range(len(self.members)):
            if i != move:
                if self.members[i] != "":
                    self.members[i].sendPacket(socket, "move;" + str(move))

    def update(self):
        packet = "room_update;"
        names = []
        for p in self.members:
            if p != "":
                names.append(p.name)
            else:
                names.append("")
        for p in self.members:
            if p != "":
                p.sendPacket(socket, packet + ";".join(names))

    def sendMessage(self, message):
        for p in self.members:
            if p != "":
                p.sendPacket(socket, "chat_update;" + message)

    def kickPlayer(self, index):
        global players
        p = self.members[index]
        if p != "":
            p.sendPacket(socket, "room_kick")
            self.members[index] = ""
            self.sendMessage(p.name + " was kicked by the host")
            self.update()
            p.room = None
            players.remove(p)


def getPlayer(address):
    for p in players:
        if p.addr == address:
            return p


def getRoom(name):
    for r in rooms:
        if r.hostPlayer.name == name:
            return r


class MyUDPHandler(DatagramRequestHandler):
    def handle(self):
        global flag, socket, players, rooms
        packet = self.request[0].decode()
        ptype = packet.split(";")[0]
        socket = self.request[1]
        if ptype == "connect":
            name = packet.split(";")[1]
            address = self.client_address
            for pl in players:
                if pl.name == name and pl.room is not None:
                    socket.sendto("connectionRefuse;name".encode(), self.client_address)
                    break
                if pl.addr[0] == address[0] and pl.room is not None:
                    socket.sendto("connectionRefuse;address".encode(), self.client_address)
                    break
            else:
                p = Player(name, address)
                p.sendPacket(socket, "connectionAccept")
        if ptype == "disconnect":
            p = getPlayer(self.client_address)
            if p is not None:
                p.disconnect()
        if ptype == "createroom":
            p = getPlayer(self.client_address)
            if p is None:
                socket.sendto("not_exist".encode(), self.client_address)
            else:
                r = Room(p)
        if ptype == "randomroom":
            p = getPlayer(self.client_address)
            if p is None:
                socket.sendto("not_exist".encode(), self.client_address)
            else:
                rs = list(filter(lambda x: "" in x.members and x.status == RoomStatus.WAIT, rooms))
                if len(rs) != 0:
                    r = choice(rs)
                    r.connectPlayer(p)
                else:
                    p.sendPacket(socket, "room_refuse;not_exist")

        if ptype == "direct_connect":
            p = getPlayer(self.client_address)
            if p is not None:
                r = getRoom(packet.split(";")[1])
                if r is not None:
                    if "" in r.members and r.status == RoomStatus.WAIT:
                        r.connectPlayer(p)
                    elif "" in r.members and r.status != RoomStatus.WAIT:
                        p.sendPacket(socket, "room_refuse;ingame")
                    elif "" not in r.members:
                        p.sendPacket(socket, "room_refuse;full")
                else:
                    p.sendPacket(socket, "room_refuse;not_exist")
            else:
                socket.sendto("not_exist".encode(), self.client_address)

        if ptype == "chat_message":
            message = ";".join(packet.split(";")[1:])
            p = getPlayer(self.client_address)
            if p is not None:
                r = p.room
                if r is not None:
                    if not (r.status == RoomStatus.GAME and r.members.index(p) > 1):
                        r.sendMessage("{}: ".format(p.name) + message)

        if ptype == "quit_room":
            p = getPlayer(self.client_address)
            if p is not None:
                r = p.room
                if r is not None:
                    r.members.remove(p)
                    r.update()
                    r.sendMessage(p.name + " left")
                    if r.hostPlayer is p:
                        for i in range(len(r.members)):
                            r.kickPlayer(i)
                        rooms.remove(r)
                players.remove(p)

        if ptype == "leave":
            p = getPlayer(self.client_address)
            if p is not None:
                r = p.room
                if r is not None:
                    p.sendPacket(socket, "room_connection;" + r.hostPlayer.name)

        if ptype == "start_game":
            p = getPlayer(self.client_address)
            if p.room.status == RoomStatus.WAIT and p.room.hostPlayer.addr == p.addr:
                r = p.room
                if r.members[0] == "" or r.members[1] == "":
                    p.sendPacket(socket, "game_refuse;not_enough")
                else:
                    r.status = RoomStatus.SHIPSETTING
                    for i in range(len(r.members)):
                        pl = r.members[i]
                        if pl != "":
                            if i == 0:
                                pl.sendPacket(socket, "game_start;player;" + pl.name + ";" + r.members[1].name)
                            elif i == 1:
                                pl.sendPacket(socket, "game_start;player;" + pl.name + ";" + r.members[0].name)
                            else:
                                pl.sendPacket(socket, "game_start;spectator;" + r.members[0].name + r.members[1].name)

        if ptype == "kickPlayer":
            p = getPlayer(self.client_address)
            if p is not None:
                r = p.room
                if r is not None:
                    if r.hostPlayer.addr[0] == p.addr[0]:
                        if r.hostPlayer is not r.members[int(packet.split(";")[1])]:
                            r.kickPlayer(int(packet.split(";")[1]))
        if ptype == "makeHost":
            p = getPlayer(self.client_address)
            if p is not None:
                r = p.room
                if r is not None:
                    if r.hostPlayer.addr[0] == p.addr[0]:
                        if r.hostPlayer is not r.members[int(packet.split(";")[1])]:
                            p.sendPacket(socket, "lost_host")
                            player = r.members[int(packet.split(";")[1])]
                            r.hostPlayer = player
                            player.sendPacket(socket, "got_host")
                            r.sendMessage(player.name + " has become the host")
        if ptype == "change_role":
            p = getPlayer(self.client_address)
            if p is not None:
                r = p.room
                if r is not None:
                    if r.hostPlayer.addr[0] == p.addr[0]:
                        first, second = packet.split(";")[1:]
                        r.sendMessage("Host: changed " + r.members[int(first)].name
                                      + " and " + r.members[int(second)].name + " places")
                        r.members[int(first)], r.members[int(second)] = r.members[int(second)], r.members[int(first)]
                        r.update()
        if ptype == "shipPositions":
            p = getPlayer(self.client_address)
            if p is not None:
                r = p.room
                if r is not None:
                    if r.status == RoomStatus.SHIPSETTING:
                        try:
                            index = r.members.index(p)
                            if index == 0:
                                r.field1.setShips(packet.split(";")[1])
                            elif index == 1:
                                r.field2.setShips(packet.split(";")[1])
                            r.sendMessage(r.members[index].name + " is ready!")
                            if r.field1.isEmpty or r.field2.isEmpty:
                                for player in r.members:
                                    if player != "":
                                        player.sendPacket(socket, "ships_accept;wait")
                            else:
                                for player in r.members:
                                    if player != "":
                                        player.sendPacket(socket, "ships_accept;start")
                                r.sendMessage("Starting!")
                                r.status = RoomStatus.GAME
                                r.setMove(randint(0, 1))
                        except ValueError:
                            pass
        if ptype == "shot":
            p = getPlayer(self.client_address)
            if p is not None:
                r = p.room
                if r is not None:
                    if r.members.index(p) == r.move:
                        i, j = list(map(int, packet.split(";")[1:]))
                        if r.move == 0:
                            pl = r.members[1]
                            cell = r.field2.field[j][i]
                            if cell == CellType.Blocked or cell == CellType.Empty:
                                p.sendPacket(socket, "shot_result;miss;" + str(i) + ";" + str(j))
                                pl.sendPacket(socket, "got_shot;miss;" + str(i) + ";" + str(j))
                                for spectator in r.members[2:]:
                                    if spectator != "":
                                        spectator.sendPacket(socket, "got_shot;1;miss;" + str(i) + ";" + str(j))
                                r.field2.field[j][i] = CellType.Miss
                                r.setMove(1)
                            elif cell == CellType.Miss or cell == CellType.Shot:
                                p.sendPacket(socket, "shot_result;deny")
                            else:
                                p.sendPacket(socket, "shot_result;hit;" + str(i) + ";" + str(j))
                                pl.sendPacket(socket, "got_shot;hit;" + str(i) + ";" + str(j))
                                for spectator in r.members[2:]:
                                    if spectator != "":
                                        spectator.sendPacket(socket, "got_shot;1;hit;" + str(i) + ";" + str(j))
                                r.field2.field[j][i] = CellType.Shot
                                flag = True
                                for x in range(10):
                                    for y in range(10):
                                        if r.field2.field[y][x] not in [CellType.Blocked, CellType.Empty, CellType.Miss,
                                                                        CellType.Shot]:
                                            flag = False
                                if flag:
                                    r.status = RoomStatus.WAIT
                                    p.sendPacket(socket, "game_result;victory")
                                    pl.sendPacket(socket, "game_result;loss")
                                    for spectator in r.members[2:]:
                                        if spectator != "":
                                            spectator.sendPacket(socket, "game_result;0")
                        else:
                            pl = r.members[0]
                            cell = r.field1.field[j][i]
                            if cell == CellType.Blocked or cell == CellType.Empty:
                                p.sendPacket(socket, "shot_result;miss;" + str(i) + ";" + str(j))
                                pl.sendPacket(socket, "got_shot;miss;" + str(i) + ";" + str(j))
                                for spectator in r.members[2:]:
                                    if spectator != "":
                                        spectator.sendPacket(socket, "got_shot;0;miss;" + str(i) + ";" + str(j))
                                r.field1.field[j][i] = CellType.Miss
                                r.setMove(0)
                            elif cell == CellType.Miss or cell == CellType.Shot:
                                p.sendPacket(socket, "shot_result;deny")
                            else:
                                p.sendPacket(socket, "shot_result;hit;" + str(i) + ";" + str(j))
                                pl.sendPacket(socket, "got_shot;hit;" + str(i) + ";" + str(j))
                                for spectator in r.members[2:]:
                                    if spectator != "":
                                        spectator.sendPacket(socket, "got_shot;0;hit;" + str(i) + ";" + str(j))
                                r.field1.field[j][i] = CellType.Shot
                                flag = True
                                for x in range(10):
                                    for y in range(10):
                                        if r.field1.field[y][x] not in [CellType.Blocked, CellType.Empty, CellType.Miss,
                                                                        CellType.Shot]:
                                            flag = False
                                if flag:
                                    r.status = RoomStatus.WAIT
                                    p.sendPacket(socket, "game_result;victory")
                                    pl.sendPacket(socket, "game_result;loss")
                                    for spectator in r.members[2:]:
                                        if spectator != "":
                                            spectator.sendPacket(socket, "game_result;1")


if __name__ == "__main__":
    server = UDPServer(addr, MyUDPHandler)
    print('starting server...')
    server.serve_forever()
