import pygame
from socket import *
import random
import threading
import sys
import os
import time
import enum

host = '26.153.209.176'
port = 777
addr = (host, port)
volume = 1
volume2 = 5
udp_socket = socket(AF_INET, SOCK_DGRAM)
data = [0, '0']


def load_image(name, colorkey=None):
    fullname = os.path.join(name)
    if not os.path.isfile(fullname):
        print(f"Файл с изображением '{fullname}' не найден")
        sys.exit()
    image = pygame.image.load(fullname)
    return image


def sendPacket(packet):
    udp_socket.sendto(packet.encode(), addr)


class CellType(enum.Enum):
    Empty = 0
    Blocked = 1
    Ship = 2


class Button(pygame.sprite.Sprite):
    def __init__(self, group, mainGroup, image):
        super().__init__(group)
        mainGroup.add(self)
        self.image = image
        self.rect = self.image.get_rect()

    def press(self):
        pass


class Chat:
    def __init__(self, x, y, w, h, lines):
        self.rect = pygame.Rect(x, y, w, h)
        self.maxlines = lines
        self.lineHeight = self.rect.height // self.maxlines
        self.lines = []

    def addLine(self, line):
        self.lines.append(line)
        if len(self.lines) > 10:
            self.lines = self.lines[1:]

    def draw(self):
        pygame.draw.rect(screen, (0, 0, 0), self.rect, 2)
        for i in range(len(self.lines)):
            line = self.lines[i]
            text = pygame.font.Font(None, 72).render(line, 0, (20, 20, 20))
            screen.blit(text, (self.rect.x + 5, self.rect.y + 5 + self.lineHeight * i))


class Gamefield(pygame.sprite.Sprite):
    def __init__(self, *group):
        super().__init__(*group)
        self.image = load_image("sprites/game_field.png")
        self.rect = self.image.get_rect()
        self.field = [[CellType.Empty for j in range(10)] for i in range(10)]

    def get_cell(self, mousepos):
        x = mousepos[0] - self.rect.x - 40
        y = mousepos[1] - self.rect.y - 40
        x = x // 40 + 1
        y = y // 40 + 1
        if not (1 <= x <= 10 and 1 <= y <= 10):
            return None
        return x, y

    def getClosest(self, x, y):
        if not (self.rect.x + 40 <= x <= self.rect.x + self.rect.width
                and self.rect.y + 40 <= y <= self.rect.y + self.rect.height):
            return None
        i = x - self.rect.x - 40
        j = y - self.rect.y - 40
        if i % 40 <= 20:
            i = i // 40
        else:
            i = i // 40 + 1
        if j % 40 <= 20:
            j = j // 40
        else:
            j = j // 40 + 1
        return i, j

    def setShip(self, ship):
        for cell in ship.get_cells():
            i, j = cell
            self.field[j][i] = CellType.Ship
        for cell in ship.get_outer_cells():
            i, j = cell
            self.field[j][i] = CellType.Blocked

    def clearField(self):
        self.field = [[CellType.Empty for j in range(10)] for i in range(10)]


class Ship(pygame.sprite.Sprite):
    def __init__(self, group, main, size, x, y, myField):
        super().__init__(group)
        self.image = load_image("sprites/ship-" + str(size) + ".png")
        self.rect = self.image.get_rect()
        main.add(self)
        self.myField = myField
        self.size = size
        self.rect.x = x
        self.rect.y = y
        self.i = None
        self.j = None
        self.defX = self.rect.x
        self.defY = self.rect.y
        self.size = size
        self.vertical = False
        self.isSet = False

    def get_coords(self):
        return self.rect.x, self.rect.y

    def get_cells(self):
        cells = []
        if self.vertical:
            for n in range(self.size):
                cells.append((self.i, self.j + n))
        else:
            for n in range(self.size):
                cells.append((self.i + n, self.j))
        return cells

    def reset(self):
        self.isSet = False
        self.i = None
        self.j = None
        self.setRed(False, force=True)
        if self.vertical:
            self.rotate(force=True)
        self.rect.x = self.defX
        self.rect.y = self.defY

    def set_cell(self, i, j):
        self.i = i
        self.j = j
        self.rect.x = self.myField.rect.x + 40 + 40 * i
        self.rect.y = self.myField.rect.y + 40 + 40 * j

    def rotate(self, force=False):
        self.vertical = not self.vertical
        x, y = self.rect.x, self.rect.y
        self.image = pygame.transform.rotate(self.image, 90)
        self.rect = self.image.get_rect()
        self.rect.x, self.rect.y = x, y
        if not force:
            if not self.isLegit():
                self.setRed(True)
            else:
                self.setRed(False)
                self.isSet = True
                self.myField.setShip(self)

    def get_outer_cells(self):
        cells = []
        for i in range(self.size + 2):
            for j in range(-1, 2):
                if self.vertical:
                    cells.append((self.i + j, self.j + i - 1))
                else:
                    cells.append((self.i + i - 1, self.j + j))
        cells = list(filter(lambda x: 0 <= x[0] <= 9 and 0 <= x[1] <= 9 and x not in self.get_cells(), cells))
        return cells

    def isLegit(self):
        cells = self.get_cells()
        for cell in cells:
            i, j = cell
            if self.myField.field[j][i] != CellType.Empty:
                return False
        return True

    def setRed(self, red, force=False):
        if red:
            image = load_image("sprites/ship-" + str(self.size) + "_red.png")
        else:
            image = load_image("sprites/ship-" + str(self.size) + ".png")
        self.image = image
        if self.vertical:
            self.image = pygame.transform.rotate(self.image, 90)
        self.rect = self.image.get_rect()
        if not force:
            self.set_cell(self.i, self.j)


class InputBox:
    def __init__(self, x, y, w, h, text=''):
        self.rect = pygame.Rect(x, y, w, h)
        self.COLOR_INACTIVE = pygame.Color((80, 80, 80))
        self.COLOR_ACTIVE = pygame.Color((20, 20, 20))
        self.FONT = pygame.font.Font(None, 72)
        self.color = self.COLOR_INACTIVE
        self.text = text
        self.txt_surface = self.FONT.render(text, True, self.color)
        self.active = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.active = not self.active
                if self.text == "Your name":
                    self.text = ""
            else:
                self.active = False
            self.color = self.COLOR_ACTIVE if self.active else self.COLOR_INACTIVE
        if event.type == pygame.KEYDOWN:
            if self.active:
                if event.key == pygame.K_RETURN:
                    pass
                elif event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                else:
                    self.text += event.unicode
                self.txt_surface = self.FONT.render(self.text, True, self.color)

    def draw(self, screen):
        screen.blit(self.txt_surface, (self.rect.x + 5, self.rect.y + 5))
        pygame.draw.rect(screen, self.color, self.rect, 2)


class Window:
    def __init__(self):
        self.sprites = pygame.sprite.Group()
        self.buttons = pygame.sprite.Group()
        self.ptypes = []

    def set(self):
        global all_sprites
        self.sprites.draw(screen)
        self.sprites.update()
        all_sprites = self.sprites

    def draw(self):
        pass

    def check_click(self, event):
        x, y = event.pos
        for b in self.buttons.sprites():
            if b.rect.collidepoint(x, y):
                b.press()

    def check_release(self, mouse_pos):
        pass

    def check_move(self):
        pass

    def check_keypress(self, event):
        pass

    def handlePacket(self, packet):
        ptype = packet.split(";")
        if ptype not in self.ptypes:
            return


class Menu(Window):
    def __init__(self):
        super().__init__()

        self.background = pygame.sprite.Sprite(self.sprites)
        self.background.image = load_image("sprites/background.png")
        self.background.rect = self.background.image.get_rect()

        self.button_play = Button(self.buttons, self.sprites, load_image("sprites/start_button.png"))
        self.button_play.press = self.play

        self.button_exit = Button(self.buttons, self.sprites, pygame.transform.scale(load_image("sprites/exit.png"),
                                                                                     (50, 50)))
        self.button_exit.press = self.exit

        self.settings = Button(self.buttons, self.sprites, pygame.transform.scale(load_image("sprites/nastroiki.png"),
                                                                                  (50, 50)))
        self.settings.press = self.setts

        self.settings.rect.x, self.settings.rect.y = width - 60, 10
        self.button_exit.rect.x, self.button_exit.rect.y = 10, 10
        self.button_play.rect.x, self.button_play.rect.y = width // 2 - self.button_play.rect.width // 2, \
                                                           height // 4

    def play(self):
        global activeWindow
        activeWindow = RoomChoice()
        activeWindow.set()

    def exit(self):
        sendPacket("disconnect")
        exit()

    def setts(self):
        global activeWindow
        activeWindow = Nactroiki()
        activeWindow.set()


class Nactroiki(Window):
    def __init__(self):
        super().__init__()
        self.background = pygame.sprite.Sprite(self.sprites)
        self.background.image = load_image("sprites/background.png")
        self.background.rect = self.background.image.get_rect()
        self.button_back = Button(self.buttons, self.sprites,
                                  pygame.transform.scale(load_image("sprites/button_back.png"),
                                                         (50, 50)))
        self.button_back.press = self.back
        self.musicText = pygame.font.SysFont('comicsansms', 45).render(
            'Громкость:  1  2  3  4  5  6  7  8  9  10    (Музыка)', 0,
            (0, 0, 0))
        self.soundText = pygame.font.SysFont('comicsansms', 45).render(
            'Громкость:  1  2  3  4  5  6  7  8  9  10    (Звуки)',
            0, (0, 0, 0))
        self.setVolume()
        pygame.mixer.music.set_volume(volume * 0.1)
        shot.set_volume(volume2 * 0.1)

    def check_click(self, event):
        super().check_click(event)
        global volume, volume2
        x, y = event.pos
        if 360 <= x <= 890 and 115 <= y <= 150:
            volume = (x - 360) // 50 + 1
            if volume > 10:
                volume = 10
        elif 360 <= x <= 890 and 215 <= y <= 250:
            volume2 = (x - 360) // 50 + 1
            if volume2 > 10:
                volume2 = 10
        self.setVolume()

    def back(self):
        global activeWindow
        activeWindow = Menu()
        activeWindow.set()

    def setVolume(self):
        pygame.mixer.music.set_volume(volume * 0.1)
        shot.set_volume(volume2 * 0.1)

    def draw(self):
        screen.blit(self.musicText, (100, 100))
        screen.blit(self.soundText, (100, 200))
        pygame.draw.line(screen, pygame.Color('black'), (360 + (volume - 1) * 53, 155),
                         (390 + (volume - 1) * 53, 155), 3)
        pygame.draw.line(screen, pygame.Color('black'), (360 + (volume2 - 1) * 53, 255),
                         (390 + (volume2 - 1) * 53, 255), 3)


class Room(Window):
    def __init__(self):
        super().__init__()
        self.ptypes = ["room_update", "chat_update"]
        self.background = pygame.sprite.Sprite(self.sprites)
        self.background.image = load_image("sprites/game_bg.png")
        self.background.rect = self.background.image.get_rect()
        self.button_back = Button(self.buttons, self.sprites,
                                  pygame.transform.scale(load_image("sprites/button_back.png"),
                                                         (50, 50)))
        self.button_back.press = self.exit
        self.playersLine = pygame.font.SysFont('comicsansms', 45).render('Players:', 0,
                                                                         (0, 0, 0))
        self.player1 = pygame.font.SysFont('comicsansms', 40).render('1. ' + "Empty", 0,
                                                                     (0, 0, 0))
        self.player2 = pygame.font.SysFont('comicsansms', 40).render('2. ' + "Empty", 0,
                                                                     (0, 0, 0))
        self.spec1 = pygame.font.SysFont('comicsansms', 40).render("", 0,
                                                                   (0, 0, 0))
        self.spec2 = pygame.font.SysFont('comicsansms', 40).render("", 0,
                                                                   (0, 0, 0))
        self.spec3 = pygame.font.SysFont('comicsansms', 40).render("", 0,
                                                                   (0, 0, 0))
        self.spectatorsLine = pygame.font.SysFont('comicsansms', 40).render('Spectators:', 0,
                                                                            (0, 0, 0))

        self.chat = Chat(100, 400, 600, 200, lines=10)
        self.inputMessage = InputBox(100, 700, 400, 100)

    def exit(self):
        global window, activeWindow
        window = "menu"
        activeWindow = Menu()
        activeWindow.set()

    def draw(self):
        pygame.draw.rect(screen, pygame.Color('black'), (80, 120, 320, 80), 4)
        pygame.draw.rect(screen, pygame.Color('black'), (80, 200, 320, 80), 4)
        screen.blit(self.playersLine, (80, 25))
        screen.blit(self.player1, (90, 130))
        screen.blit(self.player2, (90, 210))
        screen.blit(self.spectatorsLine, (80, 300))
        screen.blit(self.spec1, (80, 380))
        screen.blit(self.spec2, (80, 460))
        screen.blit(self.spec3, (80, 540))
        self.chat.draw()
        self.inputMessage.draw(screen)

    def handlePacket(self, packet):
        super().handlePacket(packet)
        ptype = packet.split(";")[0]
        if ptype == "room_update":
            players = packet.split(";")[1:]
            while len(players) != 5:
                players.append("Empty")
            self.player1 = pygame.font.SysFont('comicsansms', 40).render('1. ' + players[0], 0,
                                                                         (0, 0, 0))
            self.player2 = pygame.font.SysFont('comicsansms', 40).render('2. ' + players[1], 0,
                                                                         (0, 0, 0))
            for i in range(2, 5):
                if players[i] == "Empty":
                    players[i] = ""
            self.spec1 = pygame.font.SysFont('comicsansms', 40).render(players[2], 0,
                                                                       (0, 0, 0))
            self.spec2 = pygame.font.SysFont('comicsansms', 40).render(players[3], 0,
                                                                       (0, 0, 0))
            self.spec3 = pygame.font.SysFont('comicsansms', 40).render(players[4], 0,
                                                                       (0, 0, 0))
        if ptype == "chat_update":
            message = packet.split(";")[1]
            self.chat.addLine(message)

    def check_keypress(self, event):
        self.inputMessage.handle_event(event)
        if event.key == pygame.K_RETURN and self.inputMessage.active:
            sendPacket("chat_message;" + self.inputMessage.text)
            self.inputMessage.text = ""

    def check_click(self, event):
        super().check_click(event)
        self.inputMessage.handle_event(event)


class RoomChoice(Window):
    def __init__(self):
        super().__init__()
        self.ptypes = ["connectionAccept", "connectionRefuse", "room_connection", "not_exist"]

        self.background = pygame.sprite.Sprite(self.sprites)
        self.background.image = load_image("sprites/background.png")
        self.background.rect = self.background.image.get_rect()

        self.button_back = Button(self.buttons, self.sprites,
                                  pygame.transform.scale(load_image("sprites/button_back.png"), (50, 50)))
        self.button_back.press = self.back

        self.button_new_room = Button(self.buttons, self.sprites, load_image("sprites/new_room.png"))
        self.button_new_room.rect.x, self.button_new_room.rect.y = width // 2 - self.button_new_room.rect.width // 2, 200
        self.button_new_room.press = self.new_room

        self.button_random = Button(self.buttons, self.sprites, load_image("sprites/random_room.png"))
        self.button_random.rect.x, self.button_random.rect.y = width // 2 - self.button_random.rect.width // 2, 400
        self.button_random.press = self.randomRoom

        self.button_direct = Button(self.buttons, self.sprites, load_image("sprites/direct_connect.png"))
        self.button_direct.rect.x, self.button_direct.rect.y = width // 2 - self.button_direct.rect.width // 2, 600
        self.button_direct.press = self.directConnect

        self.nameInput = InputBox(width // 2 - 200, 50, 400, 75, "Your name")
        self.nameText_normal = pygame.font.SysFont("inkfree", 54).render("Type in your name: ", 0, (0, 0, 0))
        self.nameError_text = pygame.font.SysFont("inkfree", 54).render("This name is occupied!", 0, (120, 0, 0))
        self.addrError_text = pygame.font.SysFont("inkfree", 54).render("You are already connected!", 0, (120, 0, 0))
        self.enterName = pygame.font.SysFont("inkfree", 54).render("Type in your name first: ", 0, (120, 0, 0))
        self.nameText = self.nameText_normal

    def draw(self):
        self.nameInput.draw(screen)
        screen.blit(self.nameText, (170, 50))

    def check_keypress(self, event):
        self.nameInput.handle_event(event)
        self.nameText = self.nameText_normal

    def check_click(self, event):
        super().check_click(event)
        self.nameInput.handle_event(event)

    def back(self):
        global activeWindow
        activeWindow = Menu()
        activeWindow.set()

    def new_room(self):
        if self.nameInput.text != "Your name" and self.nameInput.text != "":
            packet = "connect;" + self.nameInput.text
            sendPacket(packet)
        sendPacket("createroom")

    def randomRoom(self):
        if self.nameInput.text != "Your name" and self.nameInput.text != "":
            packet = "connect;" + self.nameInput.text
            sendPacket(packet)
        sendPacket("randomroom")

    def directConnect(self):
        pass

    def handlePacket(self, packet):
        global activeWindow
        super().handlePacket(packet)
        ptype = packet.split(";")[0]
        if ptype == "connectionAccept":
            print("Ты лох")
        if ptype == "connectionRefuse":
            cause = packet.split(";")[1]
            if cause == "name":
                self.nameText = self.nameError_text
            elif cause == "address":
                self.nameText = self.addrError_text
        if ptype == "not_exist":
            self.nameText = self.enterName
        if ptype == "room_connection":
            activeWindow = Room()
            activeWindow.set()


class Game(Window):
    def __init__(self):
        super().__init__()
        self.ships = pygame.sprite.Group()
        self.buttons = pygame.sprite.Group()
        self.ship_on_cursor = None

        self.background = pygame.sprite.Sprite(self.sprites)
        self.background.image = load_image("sprites/game_bg.png")
        self.background.rect = self.background.image.get_rect()
        self.myField = Gamefield(self.sprites)
        self.opponentField = Gamefield(self.sprites)
        self.myField.rect = self.myField.rect.move(40, 39)
        self.opponentField.rect = self.opponentField.rect.move(800, 39)

        self.ship_4 = Ship(self.ships, self.sprites, size=4, x=1400, y=40, myField=self.myField)
        self.ship_3_1 = Ship(self.ships, self.sprites, size=3, x=1400, y=120, myField=self.myField)
        self.ship_3_2 = Ship(self.ships, self.sprites, size=3, x=1600, y=120, myField=self.myField)
        self.ship_2_1 = Ship(self.ships, self.sprites, size=2, x=1400, y=200, myField=self.myField)
        self.ship_2_2 = Ship(self.ships, self.sprites, size=2, x=1520, y=200, myField=self.myField)
        self.ship_2_3 = Ship(self.ships, self.sprites, size=2, x=1640, y=200, myField=self.myField)
        self.ship_1_1 = Ship(self.ships, self.sprites, size=1, x=1400, y=280, myField=self.myField)
        self.ship_1_2 = Ship(self.ships, self.sprites, size=1, x=1480, y=280, myField=self.myField)
        self.ship_1_3 = Ship(self.ships, self.sprites, size=1, x=1560, y=280, myField=self.myField)
        self.ship_1_4 = Ship(self.ships, self.sprites, size=1, x=1640, y=280, myField=self.myField)

        self.acceptButton = Button(self.buttons, self.sprites, load_image("sprites/buttonAccept.png"))
        self.acceptButton.rect = self.acceptButton.rect.move(1560, 400)
        self.acceptButton.press = self.accept
        self.resetButton = Button(self.buttons, self.sprites, load_image("sprites/reset.png"))
        self.resetButton.rect = self.resetButton.rect.move(1400, 400)
        self.resetButton.press = self.resetShips

    def resetShips(self):
        for ship in self.ships.sprites():
            ship.reset()
        self.updateMyField()

    def accept(self):
        for ship in self.ships.sprites():
            if not ship.isSet or not ship.isLegit():
                return
        packet = "shipPositions;"
        for ship in self.ships.sprites():
            packet += "|".join([str(ship.size), str(ship.vertical), str(ship.i), str(ship.j)])
            packet += "$"
        sendPacket(packet)

    def updateMyField(self):
        self.myField.clearField()
        for ship in self.ships.sprites():
            if ship.isSet:
                self.myField.setShip(ship)

    def check_click(self, mouse_pos):
        super().check_click(mouse_pos)
        if pygame.mouse.get_pressed()[0]:
            for ship in self.ships.sprites():
                if ship.rect.collidepoint(pygame.mouse.get_pos()):
                    self.ship_on_cursor = ship
                    self.ship_on_cursor.isSet = False
                    self.updateMyField()
                    break
        if pygame.mouse.get_pressed()[2]:
            for ship in self.ships.sprites():
                if ship.rect.collidepoint(pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1]) and ship.isSet:
                    ship.isSet = False
                    self.updateMyField()
                    ship.rotate()
                    self.updateMyField()

    def check_release(self, mouse_pos):
        if self.ship_on_cursor is not None:
            if not pygame.mouse.get_pressed()[0]:
                x, y = self.ship_on_cursor.get_coords()
                if self.myField.getClosest(x, y) is None:
                    self.ship_on_cursor.reset()
                else:
                    self.ship_on_cursor.set_cell(self.myField.getClosest(x, y)[0], self.myField.getClosest(x, y)[1])
                    self.ship_on_cursor.isSet = True
                    if not self.ship_on_cursor.isLegit():
                        self.ship_on_cursor.setRed(True)
                    else:
                        self.ship_on_cursor.setRed(False)
                        self.ship_on_cursor.myField.setShip(self.ship_on_cursor)

                self.ship_on_cursor = None

    def check_move(self):
        if self.ship_on_cursor is not None:
            self.ship_on_cursor.rect = self.ship_on_cursor.rect.move(pygame.mouse.get_rel())

    def draw(self):
        pygame.mouse.get_rel()


def cikle():
    while True:
        try:
            sms = udp_socket.recvfrom(1024)
            if sms[0].decode() == '':
                continue
            activeWindow.handlePacket(sms[0].decode())
            print(sms[0].decode())
        except OSError:
            continue


pygame.init()
pygame.mixer.music.load('sounds/bg_music.mp3')
pygame.mixer.music.set_volume(volume * 0.1)
pygame.mixer.music.play(-1)
shot = pygame.mixer.Sound('sounds/shot.wav')
shot.set_volume(volume2 * 0.1)

pygame.display.set_caption('')
height, width = pygame.display.Info().current_h, pygame.display.Info().current_w
size = width, height
screen = pygame.display.set_mode(size)

# pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
window = 'menu'
running = True

all_sprites = pygame.sprite.Group()

activeWindow = Menu()
activeWindow.set()

FPS = 30

clock = pygame.time.Clock()
client_handler = threading.Thread(
    target=cikle,
    args=(),
    daemon=True
)
client_handler.start()

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            sendPacket("disconnect")
        if event.type == pygame.MOUSEBUTTONDOWN:
            activeWindow.check_click(event)
        if event.type == pygame.MOUSEMOTION:
            activeWindow.check_move()
        if event.type == pygame.MOUSEBUTTONUP:
            activeWindow.check_release(pygame.mouse.get_pos())
        if event.type == pygame.KEYDOWN:
            activeWindow.check_keypress(event)
            if event.key == pygame.K_w:
                activeWindow = Game()
                activeWindow.set()
    screen.fill((0, 0, 0))
    all_sprites.draw(screen)
    all_sprites.update()
    activeWindow.draw()
    pygame.display.flip()
    clock.tick(FPS)
