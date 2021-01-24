import pygame
from socket import *
import threading
import sys
import os
import enum

host = '26.153.209.176'  # IP-адрес сервера. Вводится здесь.
port = 777  # Порт можно оставить таким, маловероятно то, что он будет занят
addr = (host, port)
volume = 5  # Громкости музыки и звуков
volume2 = 5
udp_socket = socket(AF_INET, SOCK_DGRAM)


def load_image(name, colorkey=None):  # Загрузка картинок. Украдено из методички Яндекса, признаю.
    fullname = os.path.join(name)
    if not os.path.isfile(fullname):
        print(f"Файл с изображением '{fullname}' не найден")
        sys.exit()
    image = pygame.image.load(fullname)
    return image


def sendPacket(packet):  # Отправка пакетов на сервер
    udp_socket.sendto(packet.encode(), addr)


class CellType(enum.Enum):  # Содержимое клетки
    Empty = 0
    Blocked = 1
    Ship = 2


class Button(pygame.sprite.Sprite):  # Класс кнопки
    def __init__(self, group, mainGroup, image):  # group - группа кнопок в окне, mainGroup - группа всех спрайтов окна
        super().__init__(group)
        mainGroup.add(self)
        self.image = image
        self.rect = self.image.get_rect()

    def press(self):  # Переопределяемый метод. Описывает то, что делает кнопка
        pass

    def remove(self):  # Убрать кнопку с экрана
        self.rect.x, self.rect.y = 1450, 820


class Chat:  # Класс чата
    def __init__(self, x, y, w, h, lines, font):
        self.rect = pygame.Rect(x, y, w, h)
        self.maxlines = lines
        self.font = font
        self.lineHeight = self.rect.height // self.maxlines + 7
        self.lines = []

    def addLine(self, line):
        self.lines.append(line)
        if len(self.lines) > self.maxlines:
            self.lines = self.lines[1:]

    def draw(self):  # Отрисовка
        for i in range(len(self.lines)):
            line = self.lines[i]
            text = self.font.render(line, False, (20, 20, 20))
            screen.blit(text, (self.rect.x + 5, self.rect.y + 5 + self.lineHeight * i))


class Gamefield(pygame.sprite.Sprite):  # Клетчатое поле для кораблей
    def __init__(self, *group):
        super().__init__(*group)
        self.image = load_image("sprites/game_field.png")
        self.rect = self.image.get_rect()
        self.field = [[CellType.Empty for j in range(10)] for i in range(10)]
        self.ships = []

    def get_cell(self, mousepos):  # Получить клетку по координатам
        x = mousepos[0] - self.rect.x - 30
        y = mousepos[1] - self.rect.y - 30
        x = x // 30 + 1
        y = y // 30 + 1
        if not (1 <= x <= 10 and 1 <= y <= 10):
            return None
        return x, y

    def getClosest(self, x, y):  # Получить ближайшую клетку по координатам
        if not (self.rect.x + 30 <= x <= self.rect.x + self.rect.width
                and self.rect.y + 30 <= y <= self.rect.y + self.rect.height):
            return None
        i = x - self.rect.x - 30
        j = y - self.rect.y - 30
        if i % 30 <= 15:
            i = i // 30
        else:
            i = i // 30 + 1
        if j % 30 <= 15:
            j = j // 30
        else:
            j = j // 30 + 1
        return i, j

    def setShip(self, ship):  # Установка корабля
        for cell in ship.get_cells():
            i, j = cell
            self.field[j][i] = CellType.Ship
        for cell in ship.get_outer_cells():
            i, j = cell
            self.field[j][i] = CellType.Blocked
        self.ships.append(ship)

    def clearField(self):
        self.field = [[CellType.Empty for j in range(10)] for i in range(10)]
        self.ships.clear()


class Ship(pygame.sprite.Sprite):  # Класс корабля
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

    def remove(self):
        self.rect.x, self.rect.y = 1450, 820

    def get_cells(self):  # Клетки корабля
        cells = []
        if self.i is None or self.j is None:
            return None
        if self.vertical:
            for n in range(self.size):
                cells.append((self.i, self.j + n))
        else:
            for n in range(self.size):
                cells.append((self.i + n, self.j))
        return cells

    def reset(self):  # Вернуть в исходное положение
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
        self.rect.x = self.myField.rect.x + 30 + 30 * i
        self.rect.y = self.myField.rect.y + 30 + 30 * j

    def rotate(self, force=False):  # Поворот
        if not force:
            if (self.vertical and self.i + self.size - 1 > 9) or (not self.vertical and self.j + self.size - 1 > 9):
                self.reset()
                return
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

    def get_outer_cells(self):  # Клетки, стоящие вплотную к кораблю
        cells = []
        for i in range(self.size + 2):
            for j in range(-1, 2):
                if self.vertical:
                    cells.append((self.i + j, self.j + i - 1))
                else:
                    cells.append((self.i + i - 1, self.j + j))
        cells = list(filter(lambda x: 0 <= x[0] <= 9 and 0 <= x[1] <= 9 and x not in self.get_cells(), cells))
        return cells

    def isLegit(self):  # Проверка, соответствует ли положение правилам игры
        cells = self.get_cells()
        if cells is None:
            return None
        for cell in cells:
            i, j = cell
            if not (0 <= i <= 9 and 0 <= j <= 9):
                self.reset()
                return None
            if self.myField.field[j][i] == CellType.Blocked:
                return False
        for ship in self.myField.ships:
            if ship is not self:
                this = set(self.get_cells())
                other = set(ship.get_cells())
                if len(list(this.intersection(other))):
                    return False
        return True

    def setRed(self, red, force=False):  # Установка красного вида корабля
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


class ShotResult(pygame.sprite.Sprite):  # Анимация выстрела
    def __init__(self, group, mainGroup, field, i, j, image):
        super().__init__(group)
        self.image = pygame.transform.scale(load_image(image), (60, 60))
        self.image.set_alpha(135)
        self.alpha = 135
        self.path = image
        self.rect = self.image.get_rect()
        self.field = field
        self.i = i
        self.j = j
        self.rect = self.rect.move(field.rect.x + i * 30, field.rect.y + j * 30)
        mainGroup.add(self)

    def update(self):
        if self.alpha != 255:
            self.alpha += 4
            self.image = pygame.transform.scale(load_image(self.path), (self.rect.width - 1, self.rect.height - 1))
            self.image.set_alpha(self.alpha)
            self.rect = self.image.get_rect()
            self.rect.x, self.rect.y = self.field.rect.x + self.i * 30 + (60 - self.rect.width), \
                                       self.field.rect.y + self.j * 30 + (60 - self.rect.height)


class GameResult(pygame.sprite.Sprite):  # Анимация победы или поражения
    def __init__(self, group, result):
        super().__init__(group)
        self.doupdate = False
        self.image = load_image("sprites/loss.png")
        self.rect = self.image.get_rect()
        self.clock = 0
        self.opacity = 0
        if result == "victory":
            self.image = load_image("sprites/victory.png")
            victory.play()
        else:
            self.image = load_image("sprites/loss.png")
            loss.play()
        self.rect = self.image.get_rect()
        self.image.set_alpha(self.opacity)
        self.doupdate = True

    def update(self):
        if self.doupdate:
            if 0 <= self.clock <= 15:
                self.opacity += 17
                self.image.set_alpha(self.opacity)
            elif 75 <= self.clock <= 90:
                self.opacity -= 17
            self.image.set_alpha(self.opacity)
            self.clock += 1


class InputBox:  # Ручной ввод
    def __init__(self, x, y, w, h, text='', lenlimit=20, drawrect=True):
        self.rect = pygame.Rect(x, y, w, h)
        self.COLOR_INACTIVE = pygame.Color((80, 80, 80))
        self.COLOR_ACTIVE = pygame.Color((20, 20, 20))
        self.drawrect = drawrect
        self.FONT = pygame.font.Font(None, 72)
        self.color = self.COLOR_INACTIVE
        self.lenlimit = lenlimit
        self.text = text
        self.defaultText = text
        self.txt_surface = self.FONT.render(text, True, self.color)
        self.active = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                if not self.active:
                    self.active = True
                if self.text == self.defaultText:
                    self.text = ""
            else:
                self.active = False
            if not self.active and self.text == "":
                self.text = self.defaultText
            self.color = self.COLOR_ACTIVE if self.active else self.COLOR_INACTIVE
        if event.type == pygame.KEYDOWN:
            if self.active:
                if event.key == pygame.K_RETURN:
                    self.enter()
                elif event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                else:
                    if len(self.text) < self.lenlimit and self.txt_surface.get_width() < self.rect.width - 50:
                        self.text += event.unicode

    def draw(self, screen):
        self.txt_surface = self.FONT.render(self.text, True, self.color)
        screen.blit(self.txt_surface, (self.rect.x + 5, self.rect.y + 5))
        if self.drawrect:
            pygame.draw.rect(screen, self.color, self.rect, 2)

    def enter(self):
        pass


class Window:  # Класс окна
    def __init__(self):
        self.sprites = pygame.sprite.Group()
        self.buttons = pygame.sprite.Group()
        self.ptypes = []  # Виды принимаемых пакетов

    def set(self):  # Установка
        global all_sprites
        self.sprites.draw(screen)
        self.sprites.update()
        all_sprites = self.sprites

    def draw(self):  # Отрисовка доп. элементов (не спрайтов)
        pass

    def check_click(self, event):  # Событие нажатия
        x, y = event.pos
        for b in self.buttons.sprites():
            if b.rect.collidepoint(x, y):
                b.press()

    def check_release(self, mouse_pos):  # Событие отжатия
        pass

    def check_move(self):  # Событие движения
        pass

    def check_keypress(self, event):  # Событие клавиатуры
        pass

    def handlePacket(self, packet):  # Обработка пакета
        ptype = packet.split(";")
        if ptype not in self.ptypes:
            return


class Menu(Window):
    def __init__(self):
        super().__init__()
        pygame.mixer.music.unload()
        pygame.mixer.music.load('sounds/bg_music.mp3')
        pygame.mixer.music.set_volume(volume * 0.1)
        pygame.mixer.music.play(-1)

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
            'Громкость:  1  2  3  4  5  6  7  8  9  10    (Музыка)', False,
            (0, 0, 0))
        self.soundText = pygame.font.SysFont('comicsansms', 45).render(
            'Громкость:  1  2  3  4  5  6  7  8  9  10    (Звуки)',
            False, (0, 0, 0))
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
        wrong.set_volume(volume2 * 0.1)
        splash.set_volume(volume2 * 0.1)
        victory.set_volume(volume2 * 0.1)
        loss.set_volume(volume2 * 0.1)

    def draw(self):
        screen.blit(self.musicText, (100, 100))
        screen.blit(self.soundText, (100, 200))
        pygame.draw.line(screen, pygame.Color('black'), (360 + (volume - 1) * 53, 155),
                         (390 + (volume - 1) * 53, 155), 3)
        pygame.draw.line(screen, pygame.Color('black'), (360 + (volume2 - 1) * 53, 255),
                         (390 + (volume2 - 1) * 53, 255), 3)


class PlayerText:  # Окно с именем игрока в комнате
    def __init__(self, x, y, w, h, font, text, drawrect=True):
        self.rect = pygame.Rect(x, y, w, h)
        self.font = font
        self.text = text
        self.draw_rect = drawrect

    def draw(self):
        if self.draw_rect:
            pygame.draw.rect(screen, (0, 0, 0), self.rect, 3)
        screen.blit(self.font.render(self.text, False, (0, 0, 0)), (self.rect.x + 5, self.rect.y + 5))


class Room(Window):
    def __init__(self):
        super().__init__()
        self.ptypes = ["room_update", "chat_update", "got_host", "lost_host", "game_start", "room_kick"]
        self.background = pygame.sprite.Sprite(self.sprites)
        self.background.image = load_image("sprites/game_bg.png")
        self.background.rect = self.background.image.get_rect()
        self.button_back = Button(self.buttons, self.sprites,
                                  pygame.transform.scale(load_image("sprites/button_back.png"),
                                                         (50, 50)))
        self.hosting = False
        self.player_on_cursor = None
        self.target_player = -1
        self.button_back.press = self.exit
        self.playersLine = pygame.font.SysFont('comicsansms', 45).render('Players:', False,
                                                                         (0, 0, 0))
        self.player1 = PlayerText(60, 90, 540, 60, pygame.font.SysFont('comicsansms', 40), "1. Empty")
        self.player2 = PlayerText(60, 150, 540, 60, pygame.font.SysFont('comicsansms', 40), "2. Empty")
        self.spec1 = PlayerText(60, 300, 540, 60, pygame.font.SysFont('comicsansms', 40), "", drawrect=False)
        self.spec2 = PlayerText(60, 360, 540, 60, pygame.font.SysFont('comicsansms', 40), "", drawrect=False)
        self.spec3 = PlayerText(60, 420, 540, 60, pygame.font.SysFont('comicsansms', 40), "", drawrect=False)
        self.spectatorsLine = pygame.font.SysFont('comicsansms', 40).render('Spectators:', False,
                                                                            (0, 0, 0))
        self.button_start = Button(self.buttons, self.sprites, load_image("sprites/start_game.png"))
        self.button_start.remove()
        self.button_start.press = self.start

        self.button_kick = Button(self.buttons, self.sprites, load_image("sprites/kick_button.png"))
        self.button_kick.remove()
        self.button_kick.press = self.kickPlayer

        self.button_changeRole = Button(self.buttons, self.sprites, load_image("sprites/change_role.png"))
        self.button_changeRole.remove()
        self.button_changeRole.press = self.changeRole

        self.button_makeHost = Button(self.buttons, self.sprites, load_image("sprites/make_host.png"))
        self.button_makeHost.remove()
        self.button_makeHost.press = self.makeHost

        self.chat = Chat(900, 350, 600, 200, lines=20, font=pygame.font.SysFont('comicsansms', 20))
        self.inputMessage = InputBox(910, 700, 400, 30, drawrect=False, text="Type here", lenlimit=30)
        self.inputMessage.FONT = pygame.font.SysFont("comicsansms", 24)
        self.players = [self.player1, self.player2, self.spec1, self.spec2, self.spec3]

    def exit(self):
        global activeWindow
        activeWindow = Menu()
        activeWindow.set()
        sendPacket("quit_room")

    def kickPlayer(self):
        if not self.hosting:
            return
        sendPacket("kickPlayer;" + str(self.player_on_cursor))
        self.player_on_cursor = None
        self.button_changeRole.remove()
        self.button_kick.remove()
        self.button_makeHost.remove()

    def changeRole(self):
        if not self.hosting:
            return
        self.target_player = self.player_on_cursor
        self.player_on_cursor = None

    def makeHost(self):
        if not self.hosting:
            return
        sendPacket("makeHost;" + str(self.player_on_cursor))

    def draw(self):
        screen.blit(self.playersLine, (60, 25))
        screen.blit(self.spectatorsLine, (60, 240))
        for pr in self.players:
            if pr != "":
                pr.draw()
        screen.blit(pygame.font.SysFont("comicsansms", 36).render(">", False, (0, 0, 0)), (900, 695))
        self.chat.draw()
        self.inputMessage.draw(screen)

    def start(self):
        if not self.hosting:
            return
        sendPacket("start_game")

    def handlePacket(self, packet):
        global activeWindow
        super().handlePacket(packet)
        ptype = packet.split(";")[0]
        if ptype == "room_update":
            players = packet.split(";")[1:]
            for i in range(len(players)):
                if i <= 1 and players[i] == "":
                    players[i] = "Empty"
            self.player1.text = '1. ' + players[0]
            self.player2.text = '2. ' + players[1]
            self.spec1.text = players[2]
            self.spec2.text = players[3]
            self.spec3.text = players[4]
        if ptype == "chat_update":
            message = packet.split(";")[1]
            self.chat.addLine(message)
        if ptype == "got_host":
            self.hosting = True
            self.button_start.rect.x, self.button_start.rect.y = 650, 100
        if ptype == "lost_host":
            self.hosting = False
            self.button_start.remove()
            self.button_changeRole.remove()
            self.button_kick.remove()
            self.button_makeHost.remove()
        if ptype == "room_kick":
            activeWindow = RoomChoice()
            activeWindow.set()
        if ptype == "game_start":
            args = packet.split(";")
            activeWindow = Game(spectator=args[1] == "spectator", name1=args[2], name2=args[3])
            activeWindow.set()

    def check_keypress(self, event):
        self.inputMessage.handle_event(event)
        if event.key == pygame.K_RETURN and self.inputMessage.active and self.inputMessage.text \
                != "Type here" and self.inputMessage.text != "":
            sendPacket("chat_message;" + self.inputMessage.text)
            self.inputMessage.text = ""

    def check_click(self, event):
        super().check_click(event)
        self.inputMessage.handle_event(event)
        x, y = event.pos
        if self.hosting:
            for p in self.players:
                if p.rect.collidepoint(x, y) and not p.text.endswith("Empty") and p.text != "":
                    if self.target_player == -1:
                        self.player_on_cursor = self.players.index(p)
                        self.button_makeHost.rect.x, self.button_makeHost.rect.y = 650, 400
                        self.button_kick.rect.x, self.button_kick.rect.y = 650, 500
                        self.button_changeRole.rect.x, self.button_changeRole.rect.y = 650, 600
                        break
                    else:
                        sendPacket("change_role;" + str(self.target_player) + ";" + str(self.players.index(p)))
                        self.target_player = -1
            else:
                self.player_on_cursor = None
                self.button_makeHost.remove()
                self.button_kick.remove()
                self.button_changeRole.remove()


class RoomChoice(Window):
    def __init__(self):
        super().__init__()
        self.ptypes = ["connectionAccept", "connectionRefuse", "room_connection", "not_exist", "room_refuse"]

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

        self.nameInput = InputBox(width // 2 - 300, 100, 600, 75, "Your name")
        self.nameText_normal = pygame.font.SysFont("inkfree", 54).render("Type in your name: ", False, (0, 0, 0))
        self.nameError_text = pygame.font.SysFont("inkfree", 54).render("This name is occupied!", False, (120, 0, 0))
        self.addrError_text = pygame.font.SysFont("inkfree", 54).render("You are already connected!", False,
                                                                        (120, 0, 0))

        self.addrInput = InputBox(110, 700, 600, 75, "Enter host's name", drawrect=False)
        self.addrInput.FONT = pygame.font.SysFont("comicsansms", 32)

        self.enterName = pygame.font.SysFont("inkfree", 54).render("Type in your name first: ", False, (120, 0, 0))
        self.nameText = self.nameText_normal

        self.msgText = ""
        self.msg = pygame.font.SysFont("comicsansms", 42).render(self.msgText, False, (0, 0, 0))

    def draw(self):
        self.nameInput.draw(screen)
        self.addrInput.draw(screen)
        screen.blit(self.nameText, (500, 30))
        self.msg = pygame.font.SysFont("comicsansms", 42).render(self.msgText, False, (0, 0, 0))
        screen.blit(self.msg, (60, 60 - self.msg.get_height()))

    def check_keypress(self, event):
        self.nameInput.handle_event(event)
        self.addrInput.handle_event(event)
        self.nameText = self.nameText_normal

    def check_click(self, event):
        super().check_click(event)
        self.nameInput.handle_event(event)
        self.addrInput.handle_event(event)
        self.msgText = ""

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
        if self.nameInput.text != "Your name" and self.nameInput.text != "":
            packet = "connect;" + self.nameInput.text
            sendPacket(packet)
            name = self.addrInput.text
            if name == "" or name == "Enter host's name":
                self.msgText = "Host's name is empty!"
            else:
                sendPacket("direct_connect;" + name)

    def handlePacket(self, packet):
        global activeWindow
        super().handlePacket(packet)
        ptype = packet.split(";")[0]
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
        if ptype == "room_refuse":
            reason = packet.split(";")[1]
            if reason == "not_exist":
                self.msgText = "Room not found!"
            elif reason == "full":
                self.msgText = "The room is full!"
            elif reason == "ingame":
                self.msgText = "The game is in process!"


class Game(Window):
    def __init__(self, spectator=True, name1="", name2=""):
        super().__init__()
        self.ptypes = ["chat_update", "ships_accept", "move", "shot_result", "got_shot", "game_result",
                       "room_connection", "room_kick"]
        pygame.mixer.music.unload()
        pygame.mixer.music.load('sounds/bg_music2.mp3')
        pygame.mixer.music.set_volume(volume * 0.1)
        pygame.mixer.music.play(-1)
        self.shipsSet = False
        self.nameDraw = True
        self.mesText = ""
        self.name1 = name1
        self.name2 = name2
        self.activeCell = (None, None)
        self.message = pygame.font.SysFont("comicsansms", 30).render(self.mesText, False, (0, 0, 0))

        self.ships = pygame.sprite.Group()
        self.buttons = pygame.sprite.Group()
        self.shots = pygame.sprite.Group()
        self.ship_on_cursor = None
        self.cellsize = 30
        self.spectator = spectator
        self.move = None

        self.chat = Chat(900, 420, 600, 200, lines=20, font=pygame.font.SysFont('comicsansms', 20))

        self.background = pygame.sprite.Sprite(self.sprites)
        self.background.image = load_image("sprites/game_bg.png")
        self.background.rect = self.background.image.get_rect()
        self.myField = Gamefield(self.sprites)
        self.opponentField = Gamefield(self.sprites)
        self.myField.rect = self.myField.rect.move(self.cellsize, self.cellsize - 1)
        self.opponentField.rect = self.opponentField.rect.move(20 * self.cellsize, self.cellsize - 1)
        self.leave_button = Button(self.buttons, self.sprites,
                                   pygame.transform.scale(load_image("sprites/button_back.png"),
                                                          (50, 50)))
        self.leave_button.remove()
        self.leave_button.press = self.leave
        self.inputMessage = InputBox(910, 770, 400, 30, drawrect=False, text="Type here", lenlimit=30)
        self.inputMessage.FONT = pygame.font.SysFont("comicsansms", 24)
        if not self.spectator:
            self.acceptButton = Button(self.buttons, self.sprites, load_image("sprites/buttonAccept.png"))
            self.acceptButton.rect = self.acceptButton.rect.move(39 * self.cellsize, 10 * self.cellsize)
            self.acceptButton.press = self.accept
            self.resetButton = Button(self.buttons, self.sprites, load_image("sprites/reset.png"))
            self.resetButton.rect = self.resetButton.rect.move(35 * self.cellsize, 10 * self.cellsize)
            self.resetButton.press = self.resetShips
            self.shot_button = Button(self.buttons, self.sprites, load_image("sprites/button_fire_inactive.png"))
            self.shot_button.rect = self.shot_button.rect.move(50, 460)
            self.shot_button.press = self.shot
            self.ship_4 = Ship(self.ships, self.sprites, size=4, x=35 * self.cellsize, y=self.cellsize,
                               myField=self.myField)
            self.ship_3_1 = Ship(self.ships, self.sprites, size=3, x=35 * self.cellsize, y=3 * self.cellsize,
                                 myField=self.myField)
            self.ship_3_2 = Ship(self.ships, self.sprites, size=3, x=40 * self.cellsize, y=3 * self.cellsize,
                                 myField=self.myField)
            self.ship_2_1 = Ship(self.ships, self.sprites, size=2, x=35 * self.cellsize, y=5 * self.cellsize,
                                 myField=self.myField)
            self.ship_2_2 = Ship(self.ships, self.sprites, size=2, x=38 * self.cellsize, y=5 * self.cellsize,
                                 myField=self.myField)
            self.ship_2_3 = Ship(self.ships, self.sprites, size=2, x=41 * self.cellsize, y=5 * self.cellsize,
                                 myField=self.myField)
            self.ship_1_1 = Ship(self.ships, self.sprites, size=1, x=35 * self.cellsize, y=7 * self.cellsize,
                                 myField=self.myField)
            self.ship_1_2 = Ship(self.ships, self.sprites, size=1, x=37 * self.cellsize, y=7 * self.cellsize,
                                 myField=self.myField)
            self.ship_1_3 = Ship(self.ships, self.sprites, size=1, x=39 * self.cellsize, y=7 * self.cellsize,
                                 myField=self.myField)
            self.ship_1_4 = Ship(self.ships, self.sprites, size=1, x=41 * self.cellsize, y=7 * self.cellsize,
                                 myField=self.myField)

    def resetShips(self):
        for ship in self.ships.sprites():
            ship.reset()
        self.updateMyField()

    def accept(self):
        if self.spectator:
            return
        for ship in self.ships.sprites():
            if not ship.isSet or not ship.isLegit():
                return
        packet = "shipPositions;"
        ships = []
        for ship in self.ships.sprites():
            ships.append("|".join([str(ship.size), str(ship.vertical), str(ship.i), str(ship.j)]))
        packet += "$".join(ships)
        sendPacket(packet)
        self.shipsSet = True
        self.resetButton.remove()
        self.acceptButton.remove()

    def leave(self):
        global activeWindow
        activeWindow = RoomChoice()
        activeWindow.set()
        sendPacket("quit_room")

    def updateMyField(self):
        self.myField.clearField()
        for ship in self.ships.sprites():
            if ship.isSet:
                self.myField.setShip(ship)

    def shot(self):
        if self.activeCell == (None, None):
            return
        sendPacket("shot;" + str(self.activeCell[0]) + ";" + str(self.activeCell[1]))
        self.activeCell = (None, None)

    def check_click(self, event):
        super().check_click(event)
        self.inputMessage.handle_event(event)
        if self.move:
            x, y = event.pos
            if self.opponentField.rect.collidepoint(x, y) and self.nameDraw:
                self.activeCell = self.opponentField.get_cell((x, y))[0] - 1, self.opponentField.get_cell((x, y))[1] - 1
            else:
                self.activeCell = (None, None)
        if self.shipsSet or self.spectator:
            return
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
                    if self.ship_on_cursor.isLegit() is None:
                        self.ship_on_cursor.reset()
                    elif not self.ship_on_cursor.isLegit():
                        self.ship_on_cursor.setRed(True)
                    else:
                        self.ship_on_cursor.setRed(False)
                        self.ship_on_cursor.myField.setShip(self.ship_on_cursor)

                self.ship_on_cursor = None

    def handlePacket(self, packet):
        super().handlePacket(packet)
        global activeWindow
        ptype = packet.split(";")[0]
        if ptype == "ships_accept":
            verdict = packet.split(";")[1]
            if verdict == "wait" and not self.spectator:
                if self.shipsSet:
                    self.mesText = "Waiting for opponent..."
                else:
                    self.mesText = "Opponent is ready!"
            elif verdict == "start":
                self.animateStart()
        if ptype == "chat_update":
            message = packet.split(";")[1]
            self.chat.addLine(message)
        if ptype == "room_kick":
            activeWindow = RoomChoice()
            activeWindow.set()
        if ptype == "move":
            move = packet.split(";")[1]
            if move == "your" and not self.spectator:
                self.setShotButtonActive(True)
                self.message = "Your move!"
                self.move = 1
            elif move != "your" and not self.spectator:
                self.setShotButtonActive(False)
                self.message = "Opponent makes move..."
                self.move = 0
            elif move != "your" and self.spectator:
                self.move = not bool(int(move))
        if ptype == "shot_result":
            result, i, j = packet.split(";")[1:]
            if result == "deny":
                self.message = "You have already shot there!"
                wrong.play()
                return
            self.animateShot(self.opponentField, int(i), int(j), result)
            self.activeCell = (None, None)
        if ptype == "got_shot":
            if not self.spectator:
                result, i, j = packet.split(";")[1:]
                self.animateShot(self.myField, int(i), int(j), result)
            else:
                player, result, i, j = packet.split(";")[1:]
                if player == "0":
                    field = self.myField
                else:
                    field = self.opponentField
                self.animateShot(field, int(i), int(j), result)
        if ptype == "game_result":
            result = packet.split(";")[1]
            if not self.spectator:
                self.animateEnd(result)
            else:
                if result == "0":
                    winner = self.name1
                else:
                    winner = self.name2
                self.message = winner + " won!"
                self.nameDraw = False
                self.leave_button.rect.x, self.leave_button.rect.y = 695, 750
        if ptype == "room_connection":
            activeWindow = Room()
            activeWindow.set()

    def setShotButtonActive(self, active):
        if self.spectator:
            return
        if active:
            self.shot_button.image = load_image("sprites/button_fire.png")
        else:
            self.shot_button.image = load_image("sprites/button_fire_inactive.png")

    def animateShot(self, field, i, j, result):
        if result == "miss":
            shotresult = ShotResult(self.shots, self.sprites, field, i, j, "sprites/miss.png")
            splash.play()
        elif result == "hit":
            shotresult = ShotResult(self.shots, self.sprites, field, i, j, "sprites/cross.png")
            shot.play()

    def animateStart(self):
        self.mesText = ""

    def animateEnd(self, result):
        self.nameDraw = False
        self.setShotButtonActive(False)
        self.leave_button.rect.x, self.leave_button.rect.y = 695, 750
        animation = GameResult(self.sprites, result)

    def check_move(self):
        if self.ship_on_cursor is not None:
            self.ship_on_cursor.rect = self.ship_on_cursor.rect.move(pygame.mouse.get_rel())

    def draw(self):
        pygame.mouse.get_rel()  # Это нужно вызывать постоянно, чтобы корабли двигались нормально, поэтому это здесь
        self.message = pygame.font.SysFont("comicsansms", 30).render(self.mesText, False, (0, 0, 0))
        screen.blit(self.message, (50, 760 - self.message.get_height()))
        color1 = (120, 0, 0) if self.move else (0, 0, 0)
        color2 = (120, 0, 0) if not self.move else (0, 0, 0)
        if self.activeCell != (None, None):
            pygame.draw.rect(screen, pygame.Color(120, 0, 0, a=100),
                             pygame.rect.Rect(self.opponentField.rect.x + 30 + 30 * self.activeCell[0],
                                              self.opponentField.rect.y + 30 + 30 * self.activeCell[1], 30, 30))
        if self.move is None:
            color1, color2 = (0, 0, 0), (0, 0, 0)
        screen.blit(pygame.font.SysFont("comicsansms", 34).render(self.name1, False, color1), (30, 390))
        if self.nameDraw:
            screen.blit(pygame.font.SysFont("comicsansms", 34).render(self.name2, False, color2), (600, 390))
            self.chat.draw()
        screen.blit(pygame.font.SysFont("comicsansms", 36).render(">", False, (0, 0, 0)), (900, 765))
        self.inputMessage.draw(screen)

    def check_keypress(self, event):
        self.inputMessage.handle_event(event)
        if event.key == pygame.K_RETURN and self.inputMessage.active and self.inputMessage.text \
                != "Type here" and self.inputMessage.text != "":
            sendPacket("chat_message;" + self.inputMessage.text)
            self.inputMessage.text = ""


def cikle():  # Параллельный поток для получения пакетов
    while True:
        try:
            sms = udp_socket.recvfrom(1024)
            if sms[0].decode() == '':
                continue
            activeWindow.handlePacket(sms[0].decode())
        except OSError:
            continue


pygame.init()
shot = pygame.mixer.Sound('sounds/shot.wav')  # Звуки и музыка
shot.set_volume(volume2 * 0.1)
wrong = pygame.mixer.Sound('sounds/wrong_cell.wav')
wrong.set_volume(volume2 * 0.1)
splash = pygame.mixer.Sound('sounds/splash.wav')
splash.set_volume(volume2 * 0.1)
victory = pygame.mixer.Sound('sounds/victory.mp3')
victory.set_volume(volume2 * 0.1)
loss = pygame.mixer.Sound('sounds/loss.mp3')
loss.set_volume(volume2 * 0.1)

pygame.display.set_caption('')
height, width = 810, 1440
size = width, height
screen = pygame.display.set_mode(size)

running = True

all_sprites = pygame.sprite.Group()  # Текущие спрайты

activeWindow = Menu()  # Текущее окно
activeWindow.set()

FPS = 30

clock = pygame.time.Clock()
client_handler = threading.Thread(  # Запуск параллельного потока
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
    screen.fill((0, 0, 0))
    all_sprites.draw(screen)
    all_sprites.update()
    activeWindow.draw()
    pygame.display.flip()
    clock.tick(FPS)
