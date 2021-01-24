from socketserver import *
import enum
from random import choice, randint

host = '26.153.209.176'  # IP сервера в локальной сети
port = 777
addr = (host, port)
socket = None
players = []  # Все игроки
rooms = []  # Все комнаты
flag = 0


class RoomStatus(enum.Enum):  # Состояние комнаты (ожидание игроков/установка кораблей/игра)
    WAIT = 1
    SHIPSETTING = 2
    GAME = 3


class CellType(enum.Enum):  # Содержимое клетки игрового поля
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


class Gamefield:  # Игровое поле
    def __init__(self):
        self.field = [[CellType.Empty for j in range(10)] for i in range(10)]  # Само поле
        self.shipPositions = ""
        self.isEmpty = True

    def setShips(self, string):  # Установка кораблей по данным пользователя
        self.shipPositions = string
        ships = string.split("$")
        for i in range(len(ships)):
            size, vertical, x, y = ships[i].split("|")
            self.setShip(size, vertical, x, y, i + 1)
        self.isEmpty = False

    def setShip(self, size, vertical, x, y, i):  # Установка корабля
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

    def clearField(self):  # Очистить поле
        self.field = [[CellType.Empty for j in range(10)] for i in range(10)]
        self.isEmpty = True


class Player:  # Игрок
    def __init__(self, name, addr):
        self.name = name  # Имя, IP и порт игрока
        self.addr = addr
        self.room = None
        players.append(self)

    def sendPacket(self, socket, packet):  # Отправить данные игроку
        socket.sendto(packet.encode(), self.addr)

    def disconnect(self):  # Отключить игрока от сервера
        global players, rooms
        if self.room is not None:
            if self.room.hostPlayer is self:
                for i in range(len(self.room.members)):
                    self.room.kickPlayer(i)
                rooms.remove(self.room)
            else:
                if self.room.status != RoomStatus.WAIT and self.room.members.index(self) <= 1:
                    for i in range(len(self.room.members)):
                        p = self.room.members[i]
                        if p != "":
                            self.room.kickPlayer(i)
                else:
                    self.room.members.remove(self)
                    self.room.update()
                    self.room.sendMessage(self.name + " left")

        if self in players:
            players.remove(self)


class Room:  # Комната
    def __init__(self, hostPlayer):
        self.name = hostPlayer.name  # Установка игрока-хозяина комнаты
        self.addr = hostPlayer.addr
        self.hostPlayer = hostPlayer
        self.members = ["", "", "", "", ""]  # Игроки комнаты. Максимум 5. Пустая строка - свободный слот.
        self.status = RoomStatus.WAIT
        self.connectPlayer(hostPlayer)  # Подключение хозяина комнаты происходит сразу в init
        self.hostPlayer.sendPacket(socket, "got_host")
        self.field1 = Gamefield()
        self.field2 = Gamefield()
        self.move = None
        rooms.append(self)

    def connectPlayer(self, player):  # Подключить игрока
        self.members[self.members.index("")] = player
        player.room = self
        packet = "room_connection;" + str(self.name)
        player.sendPacket(socket, packet)
        self.update()

    def setMove(self, move):  # Установка хода (то есть игрока, который делает ход)
        self.move = move
        self.members[move].sendPacket(socket, "move;your")
        for i in range(len(self.members)):
            if i != move:
                if self.members[i] != "":
                    self.members[i].sendPacket(socket, "move;" + str(move))

    def update(self):  # Обновление комнаты у игроков, когда игрок присоединяется или выходит
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

    def sendMessage(self, message):  # Отправить сообщение в чат
        for p in self.members:
            if p != "":
                p.sendPacket(socket, "chat_update;" + message)

    def kickPlayer(self, index):  # Выгнать игрока из комнаты
        global players
        p = self.members[index]
        if p != "":
            p.sendPacket(socket, "room_kick")
            self.members[index] = ""
            self.sendMessage(p.name + " was kicked by the host")
            self.update()
            p.room = None
            players.remove(p)

    def fillMembersList(self):
        while len(self.members) < 5:
            self.members.append("")


def getPlayer(address):  # Получить игрока по адресу
    for p in players:
        if p.addr == address:
            return p


def getRoom(name):  # Получить комнату по имени хоста
    for r in rooms:
        if r.hostPlayer.name == name:
            return r


class MyUDPHandler(DatagramRequestHandler):  # Обработка пакетов от пользователей
    def handle(self):
        global flag, socket, players, rooms
        packet = self.request[0].decode()
        ptype = packet.split(";")[0]
        socket = self.request[1]  # Получение пакета и декодирование
        # Дальше огромный if else для каждого типа пакета. Не судите строго
        if ptype == "connect":  # Подключение к серверу
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
        if ptype == "disconnect":  # Отключение от сервера
            p = getPlayer(self.client_address)
            if p is not None:
                p.disconnect()
        if ptype == "createroom":  # Создание комнаты игроком
            p = getPlayer(self.client_address)
            if p is None:
                socket.sendto("not_exist".encode(), self.client_address)
            else:
                r = Room(p)
        if ptype == "randomroom":  # Подключение к случайной комнате
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

        if ptype == "direct_connect":  # Прямое подключение (по имени хоста)
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

        if ptype == "chat_message":  # Сообщение в чат
            message = ";".join(packet.split(";")[1:])
            p = getPlayer(self.client_address)
            if p is not None:
                r = p.room
                if r is not None:
                    if not message.startswith("/"):  # Обработка команд в чате
                        r.sendMessage("{}: ".format(p.name) + message)
                    else:
                        if message.startswith("/leave"):
                            if r.hostPlayer is p:
                                for i in range(len(r.members)):
                                    r.kickPlayer(i)
                                rooms.remove(r)
                            else:
                                if r.status != RoomStatus.WAIT and r.members.index(p) <= 1:
                                    for i in range(len(r.members)):
                                        pl = r.members[i]
                                        if pl != "":
                                            r.kickPlayer(i)
                                else:
                                    r.members.remove(p)
                                    r.fillMembersList()
                                    r.update()
                                    r.sendMessage(p.name + " left")
                                    players.remove(p)
                        if r.hostPlayer is p:
                            if message.startswith("/break") and r.status != RoomStatus.WAIT:
                                for i in range(len(r.members)):
                                    r.kickPlayer(i)
                                rooms.remove(r)
                            pname = message.split()
                            if len(pname) > 1:
                                pname = " ".join(pname[1:])
                                index = -1
                                for i in range(len(r.members)):
                                    if r.members[i] != "":
                                        if r.members[i].name == pname:
                                            index = i
                                            break
                                if message.startswith("/kick") and index != -1:
                                    r.kickPlayer(index)
                                if message.startswith("/makehost") and index != -1:
                                    p.sendPacket(socket, "lost_host")
                                    player = r.members[index]
                                    r.hostPlayer = player
                                    r.name = player.name
                                    player.sendPacket(socket, "got_host")
                                    r.sendMessage(player.name + " has become the host")

        if ptype == "quit_room":  # Выход из комнаты
            p = getPlayer(self.client_address)
            if p is not None:
                r = p.room
                if r is not None:
                    if r.hostPlayer is p:
                        for i in range(len(r.members)):
                            r.kickPlayer(i)
                        rooms.remove(r)
                    else:
                        if r.status != RoomStatus.WAIT and r.members.index(p) <= 1:
                            for i in range(len(r.members)):
                                pl = r.members[i]
                                if pl != "":
                                    r.kickPlayer(i)
                        else:
                            r.members.remove(p)
                            r.fillMembersList()
                            r.update()
                            r.sendMessage(p.name + " left")
                            players.remove(p)

        if ptype == "start_game":  # Начало игры
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
                                pl.sendPacket(socket, "game_start;spectator;" +
                                              r.members[0].name + ";" + r.members[1].name)

        if ptype == "kickPlayer":  # Выгнать игрока
            p = getPlayer(self.client_address)
            if p is not None:
                r = p.room
                if r is not None:
                    if r.hostPlayer.addr[0] == p.addr[0]:
                        if r.hostPlayer is not r.members[int(packet.split(";")[1])]:
                            r.kickPlayer(int(packet.split(";")[1]))
        if ptype == "makeHost":  # Передать права хоста игроку
            p = getPlayer(self.client_address)
            if p is not None:
                r = p.room
                if r is not None:
                    if r.hostPlayer.addr[0] == p.addr[0]:
                        if r.hostPlayer is not r.members[int(packet.split(";")[1])]:
                            p.sendPacket(socket, "lost_host")
                            player = r.members[int(packet.split(";")[1])]
                            r.hostPlayer = player
                            r.name = player.name
                            player.sendPacket(socket, "got_host")
                            r.sendMessage(player.name + " has become the host")
        if ptype == "change_role":  # Поменять местами игроков
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
        if ptype == "shipPositions":  # Позиции кораблей
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
        if ptype == "shot":  # Выстрел. Самый страшный кусок кода в проекте.
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
                                p.sendPacket(socket, "shot_result;deny;" + str(i) + ";" + str(j))
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
                                p.sendPacket(socket, "shot_result;deny;" + str(i) + ";" + str(j))
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


if __name__ == "__main__":  # Запуск сервера
    server = UDPServer(addr, MyUDPHandler)
    print('starting server...')
    server.serve_forever()
