# -*- coding: utf-8 -*-

from socketserver import *
import enum
from random import choice
import time

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
        self.isEmpty = True

    def setShips(self, string):
        ships = string.split("$")
        for i in range(len(ships)):
            size, vertical, x, y = ships[i].split("|")
            self.setShip(size, vertical, x, y, i + 1)
        self.isEmpty = False

    def setShip(self, size, vertical, x, y, i):
        if vertical:
            for j in range(int(size) + 2):
                for i1 in range(-1, 2):
                    self.field[int(y) + j - 1][int(x) + i1] = CellType.Blocked
            for j in range(int(size)):
                self.field[int(y) + j][int(x)] = CellType(i)
        else:
            for j in range(int(size) + 2):
                for i1 in range(-1, 2):
                    self.field[int(y) + i1][int(x) + j - 1] = CellType.Blocked
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
        p = self.members[index]
        if p != "":
            p.sendPacket(socket, "room_kick")
            self.members = self.members[:index] + self.members[index + 1:]
            while len(self.members) < 5:
                self.members.append("")
            self.sendMessage(p.name + " was kicked by the host")
            self.update()
            p.room = None
            players.remove(p)


def getPlayer(address):
    for p in players:
        if p.addr == address:
            return p


class MyUDPHandler(DatagramRequestHandler):
    def handle(self):
        global flag, socket
        packet = self.request[0].decode()
        ptype = packet.split(";")[0]
        socket = self.request[1]
        if ptype == "connect":
            name = packet.split(";")[1]
            address = self.client_address
            for pl in players:
                if pl.name == name:
                    socket.sendto("connectionRefuse;name".encode(), self.client_address)
                    break
                if pl.addr[0] == address[0]:
                    socket.sendto("connectionRefuse;address".encode(), self.client_address)
                    break
            else:
                p = Player(name, address)
                p.sendPacket(socket, "connectionAccept")
        if ptype == "disconnect":
            p = getPlayer(self.client_address)
            if p is not None:
                p.disconnect()
                print("disconnected")
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
                r = choice(list(filter(lambda x: len(x.members) < 5, rooms)))
                r.connectPlayer(p)
        if ptype == "chat_message":
            message = ";".join(packet.split(";")[1:])
            p = getPlayer(self.client_address)
            if p is not None:
                r = p.room
                if r is not None:
                    r.sendMessage("{}: ".format(p.name) + message)

        if ptype == "start_game":
            p = getPlayer(self.client_address)
            if p.room.status == RoomStatus.WAIT and p.room.hostPlayer.addr == p.addr:
                r = p.room
                if r.members[0] == "" or r.members[1] == "":
                    p.sendPacket("game_refuse;not_enough")
                else:
                    r.status = RoomStatus.SHIPSETTING
                    for i in range(len(r.members)):
                        pl = r.members[i]
                        if pl != "":
                            if i <= 1:
                                pl.sendPacket(socket, "game_start;player")
                            else:
                                pl.sendPacket(socket, "game_start;spectator")

        if ptype == "kickPlayer":
            p = getPlayer(self.client_address)
            if p is not None:
                r = p.room
                if r is not None:
                    if r.hostPlayer.addr == p.addr:
                        if r.hostPlayer is not p:
                            r.kickPlayer(int(packet.split(";")[1]))
        if ptype == "makeHost":
            p = getPlayer(self.client_address)
            if p is not None:
                r = p.room
                if r is not None:
                    if r.hostPlayer.addr == p.addr:
                        if r.hostPlayer is not p:
                            p.sendPacket(socket, "lost_host")
                            player = r.members[int(packet.split(";")[1])]
                            r.hostPlayer = player
                            player.sendPacket(socket, "got_host")
                            r.sendMessage(player.name + " has become the host")

        if ptype == "ship_positions":
            p = getPlayer(self.client_address)
            if p is not None:
                r = p.room
                if r is not None:
                    if r.status == RoomStatus.WAIT:
                        try:
                            index = r.members.index(p)
                            if index == 0:
                                r.field1.setShips(packet.split(";")[1])
                            elif index == 1:
                                r.field2.setShips(packet.split(";")[1])
                            for spectator in r.members[2:]: # Отправка расположения кораблей наблюдателям
                                if spectator != "":
                                    spectator.sendPacket("ships_pos;" + str(index) + ";" + packet.split(";")[1])
                            if r.field1.isEmpty or r.field2.isEmpty:
                                for player in r.members:
                                    if player != "":
                                        p.sendPacket(socket, "ships_accept;wait")
                            else:
                                for player in r.members:
                                    if player != "":
                                        p.sendPacket(socket, "ships_accept;start")
                                r.status = RoomStatus.GAME
                        except ValueError:
                            print("Not in members")


if __name__ == "__main__":
    server = UDPServer(addr, MyUDPHandler)
    print('starting server...')
    server.serve_forever()
