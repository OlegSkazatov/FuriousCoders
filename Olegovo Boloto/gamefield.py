import pygame
import os
import sys

from socket import *

udp_socket = socket(AF_INET, SOCK_DGRAM)
host = '26.220.153.222'
port = 777
addr = (host, port)
# udp_socket.sendto('присоединился;OlayBalalay'.encode(), addr)


def sendCoords(size, orientation, x, y):
    udp_socket.sendto('shipSet;{};{};{};{}'.format(str(size), str(orientation), str(x), str(y)).encode(), addr)


def resetShips():
    for ship in ships.sprites():
        ship.reset()


def load_image(name, colorkey=None):
    fullname = os.path.join(name)
    if not os.path.isfile(fullname):
        print(f"Файл с изображением '{fullname}' не найден")
        sys.exit()
    image = pygame.image.load(fullname)
    return image


class Gamefield(pygame.sprite.Sprite):
    def __init__(self, *group):
        super().__init__(*group)
        self.image = load_image("sprites/game_field.png")
        self.rect = self.image.get_rect()
        all_sprites.add(self)

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


class Ship(pygame.sprite.Sprite):
    def __init__(self, *group, size, x, y):
        super().__init__(*group)
        self.image = load_image("sprites/ship-" + str(size) + ".png")
        self.rect = self.image.get_rect()
        self.size = size
        self.rect.x = x
        self.rect.y = y
        self.i = None
        self.j = None
        self.defX = self.rect.x
        self.defY = self.rect.y
        self.size = size
        all_sprites.add(self)
        self.vertical = False
        self.isSet = False

    def get_coords(self):
        return self.rect.x, self.rect.y

    def reset(self):
        self.isSet = False
        self.i = None
        self.j = None
        self.rect.x = self.defX
        self.rect.y = self.defY
        if self.vertical:
            self.rotate()

    def set_cell(self, i, j):
        self.i = i
        self.j = j
        self.rect.x = myField.rect.x + 40 + 40 * i
        self.rect.y = myField.rect.y + 40 + 40 * j

    def rotate(self):
        self.vertical = not self.vertical
        x, y = self.rect.x, self.rect.y
        self.image = pygame.transform.rotate(self.image, 90)
        self.rect = self.image.get_rect()
        self.rect.x, self.rect.y = x, y


class AcceptButton(pygame.sprite.Sprite):
    def __init__(self, group):
        super().__init__(group)
        self.image = load_image("sprites/buttonAccept.png")
        self.rect = self.image.get_rect()
        all_sprites.add(self)

    def press(self):
        for ship in ships.sprites():
            if not ship.isSet:
                return
        packet = "shipPositions;"
        for ship in ships.sprites():
            packet += "|".join([str(ship.size), str(ship.vertical), str(ship.i), str(ship.j)])
            packet += "$"
        udp_socket.sendto(packet.encode(), addr)


class ResetButton(pygame.sprite.Sprite):
    def __init__(self, group):
        super().__init__(group)
        self.image = load_image("sprites/reset.png")
        self.rect = self.image.get_rect()
        all_sprites.add(self)

    def press(self):
        resetShips()


pygame.init()
all_sprites = pygame.sprite.Group()
ships = pygame.sprite.Group()
buttons = pygame.sprite.Group()

pygame.display.set_caption('Морской бой')
infoObject = pygame.display.Info()
screen = pygame.display.set_mode((infoObject.current_w, infoObject.current_h))
FPS = 30

fon = pygame.sprite.Sprite(all_sprites)
fonIm = load_image("sprites/game_bg.png")
fon.image = fonIm
fon.rect = fon.image.get_rect()

pygame.display.flip()

clock = pygame.time.Clock()
running = True

# Своё поле и поле оппонента
myField = Gamefield()
opponentField = Gamefield()

# Корабли

ship_4 = Ship(ships, size=4, x=1400, y=40)
ship_3_1 = Ship(ships, size=3, x=1400, y=120)
ship_3_2 = Ship(ships, size=3, x=1600, y=120)
ship_2_1 = Ship(ships, size=2, x=1400, y=200)
ship_2_2 = Ship(ships, size=2, x=1520, y=200)
ship_2_3 = Ship(ships, size=2, x=1640, y=200)
ship_1_1 = Ship(ships, size=1, x=1400, y=280)
ship_1_2 = Ship(ships, size=1, x=1480, y=280)
ship_1_3 = Ship(ships, size=1, x=1560, y=280)
ship_1_4 = Ship(ships, size=1, x=1640, y=280)

# Кнопки

resetButton = ResetButton(buttons)
resetButton.rect = resetButton.rect.move(1400, 400)
acceptButton = AcceptButton(buttons)
acceptButton.rect = acceptButton.rect.move(1560, 400)

ship_on_cursor = None
ships_set = False

myField.rect = myField.rect.move(40, 39)
opponentField.rect = opponentField.rect.move(800, 39)
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            if pygame.mouse.get_pressed()[0]:
                for ship in ships.sprites():
                    if ship.rect.collidepoint(pygame.mouse.get_pos()):
                        ship_on_cursor = ship
                for button in buttons.sprites():
                    if button.rect.collidepoint(pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1]):
                        button.press()
            if pygame.mouse.get_pressed()[2]:
                for ship in ships.sprites():
                    if ship.rect.collidepoint(pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1]) and ship.isSet:
                        ship.rotate()
        if event.type == pygame.MOUSEMOTION:
            if ship_on_cursor is not None:
                ship_on_cursor.rect = ship_on_cursor.rect.move(pygame.mouse.get_rel())
        if event.type == pygame.MOUSEBUTTONUP:
            if ship_on_cursor is not None:
                if not pygame.mouse.get_pressed()[0]:
                    x, y = ship_on_cursor.get_coords()
                    if myField.getClosest(x, y) is None:
                        ship_on_cursor.reset()
                    else:
                        ship_on_cursor.set_cell(myField.getClosest(x, y)[0], myField.getClosest(x, y)[1])
                        ship_on_cursor.isSet = True

                    ship_on_cursor = None
    screen.fill((0, 0, 0))
    pygame.mouse.get_rel()
    all_sprites.draw(screen)
    all_sprites.update()
    pygame.display.flip()
    clock.tick(FPS)
