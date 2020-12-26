import pygame
import os
import sys


def reset():
    pass


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


class Ship(pygame.sprite.Sprite):
    def __init__(self, *group, size):
        super().__init__(*group)
        self.image = load_image("sprites/ship-" + str(size) + ".png")
        self.rect = self.image.get_rect()
        all_sprites.add(self)


pygame.init()
all_sprites = pygame.sprite.Group()
ships = pygame.sprite.Group()

pygame.display.set_caption('Морской бой')
infoObject = pygame.display.Info()
screen = pygame.display.set_mode((infoObject.current_w, infoObject.current_h))
FPS = 30

fon = pygame.transform.scale(load_image('sprites/game_bg.png'), (infoObject.current_w, infoObject.current_h))
screen.blit(fon, (0, 0))
pygame.display.flip()

clock = pygame.time.Clock()
running = True

myField = Gamefield()
opponentField = Gamefield()


myField.rect = myField.rect.move(100, 200)
opponentField.rect = opponentField.rect.move(600, 200)
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
#    all_sprites.draw(screen)
#    all_sprites.update()
    clock.tick(FPS)
