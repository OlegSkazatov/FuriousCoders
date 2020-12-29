import pygame
import os
import sys


def resetShips():
    ship_4.rect.x, ship_4.rect.y = 1400, 40
    ship_3_1.rect.x, ship_3_1.rect.y = 1400, 120
    ship_3_2.rect.x, ship_3_2.rect.y = 1600, 120
    ship_2_1.rect.x, ship_2_1.rect.y = 1400, 200
    ship_2_2.rect.x, ship_2_2.rect.y = 1520, 200
    ship_2_3.rect.x, ship_2_3.rect.y = 1640, 200
    ship_1_1.rect.x, ship_1_1.rect.y = 1400, 280
    ship_1_2.rect.x, ship_1_2.rect.y = 1480, 280
    ship_1_3.rect.x, ship_1_3.rect.y = 1560, 280
    ship_1_4.rect.x, ship_1_4.rect.y = 1640, 280


def resetShip(ship):
    ship.rect.x, ship.rect.y = ship.defX, ship.defY


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
    def __init__(self, *group, size):
        super().__init__(*group)
        self.image = load_image("sprites/ship-" + str(size) + ".png")
        self.rect = self.image.get_rect()
        self.defX = self.rect.x
        self.defY = self.rect.y
        self.size = size
        all_sprites.add(self)
        self.vertical = False
        self.isSet = False


pygame.init()
all_sprites = pygame.sprite.Group()
ships = pygame.sprite.Group()

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

ship_4 = Ship(ships, size=4)
ship_4.rect = ship_4.rect.move(1400, 40)
ship_3_1 = Ship(ships, size=3)
ship_3_1.rect = ship_3_1.rect.move(1400, 120)
ship_3_2 = Ship(ships, size=3)
ship_3_2.rect = ship_3_2.rect.move(1600, 120)
ship_2_1 = Ship(ships, size=2)
ship_2_1.rect = ship_2_1.rect.move(1400, 200)
ship_2_2 = Ship(ships, size=2)
ship_2_2.rect = ship_2_2.rect.move(1520, 200)
ship_2_3 = Ship(ships, size=2)
ship_2_3.rect = ship_2_3.rect.move(1640, 200)
ship_1_1 = Ship(ships, size=1)
ship_1_1.rect = ship_1_1.rect.move(1400, 280)
ship_1_2 = Ship(ships, size=1)
ship_1_2.rect = ship_1_2.rect.move(1480, 280)
ship_1_3 = Ship(ships, size=1)
ship_1_3.rect = ship_1_3.rect.move(1560, 280)
ship_1_4 = Ship(ships, size=1)
ship_1_4.rect = ship_1_4.rect.move(1640, 280)

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
        if event.type == pygame.MOUSEMOTION:
            if ship_on_cursor is not None:
                ship_on_cursor.rect = ship_on_cursor.rect.move(pygame.mouse.get_rel())
        if event.type == pygame.MOUSEBUTTONUP:
            if ship_on_cursor is not None:
                if not pygame.mouse.get_pressed()[0]:
                    ship_on_cursor = None
    screen.fill((0, 0, 0))
    if ship_on_cursor is not None:
        pygame.mouse.get_rel()
    all_sprites.draw(screen)
    all_sprites.update()
    pygame.display.flip()
    clock.tick(FPS)
