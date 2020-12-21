# -*- coding: utf-8 -*-
import pygame
from socket import *
import random
import threading
import sys

host = '26.220.153.222'
port = 777
addr = (host, port)
button_play = pygame.image.load('sprites/start_button.png')
button_exit = pygame.image.load('sprites/exit.png')
background = pygame.image.load('sprites/background.png')
settings = pygame.image.load('sprites/nastroiki.png')
udp_socket = socket(AF_INET, SOCK_DGRAM)
data = [0, '0']

class Board:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.board = [[0] * width for i in range(height)]
        self.board2 = [[0] * width for i in range(height)]
        self.left = 50
        self.top = 100
        self.cell_size = 50
        self.q = 2
        for i in range(10):
            q = random.randint(0, 9)
            w = random.randint(0, 9)
            self.board2[q][w] = 1

    def set_view(self, left, top, cell_size):
        self.left = left
        self.top = top
        self.cell_size = cell_size

    def get_cell(self, mouse_pos):
        x, y = mouse_pos
        x -= self.left
        y -= self.top
        r = (x // self.cell_size, y // self.cell_size)
        if r[0] > self.width - 1 or r[1] > self.height or r[0] < 0 or r[1] < 0:
            return None
        return r

    def get_click(self, mouse_pos):
        if 60 > mouse_pos[0] > 10 and 60 > mouse_pos[1] > 10:
            udp_socket.sendto('отключаюсь'.encode(), addr)
            exit()
        cell = self.get_cell(mouse_pos)
        if cell != None:
            self.on_click(cell)

    def render(self, screen):
        for i in range(self.width):
            for j in range(self.height):
                pygame.draw.rect(screen, (255, 255, 255), (self.left + self.cell_size * i,
                                                           self.top + self.cell_size * j, self.cell_size,
                                                           self.cell_size), 1)
                pygame.draw.rect(screen, (255, 255, 255), (self.left + self.cell_size * i + 700,
                                                           self.top + self.cell_size * j, self.cell_size,
                                                           self.cell_size), 1)

    def on_click(self, cell_coords):
        pass
        # if self.board[cell_coords[0]][cell_coords[1]] == 0:
        #     pygame.draw.rect(screen, pygame.Color('green'), (self.left + self.cell_size * cell_coords[0] + 1 + 700,
        #                                                      self.top + self.cell_size * cell_coords[1] + 1,
        #                                                      self.cell_size - 2,
        #                                                      self.cell_size - 2), 0)


class Menu:
    def __init__(self):
        pass

    def check_click(self, mouse_pos):
        global running, m
        if 60 > mouse_pos[0] > 10 and 60 > mouse_pos[1] > 10:
            running = False
        elif width // 4 + 400 > mouse_pos[0] > width // 4 and height // 4 + 150 > mouse_pos[1] > height // 4:
            m = 1
            screen.blit(background, (0, 0))
            screen.blit(settings, (width - 60, 10))
            screen.blit(button_exit, (10, 10))
            udp_socket.sendto('присоединился'.encode(), addr)
            board.render(screen)


def cikle():
    while True:
        try:
            sms = udp_socket.recvfrom(1024)
            if sms[0].decode() == '':
                continue
            if sms[0] == 'Вы 1'.encode():
                data[0] = 1
            elif sms[0].decode() == 'Вы 2':
                data[0] = 2
            elif sms[0].decode() == 'Вы наблюдатель':
                data[0] = 3
            else:
                data[1] = sms[0].decode()
            print(data)
        except OSError:
            continue


pygame.init()
pygame.display.set_caption('')
height, width = pygame.display.Info().current_h, pygame.display.Info().current_w
size = width, height
screen = pygame.display.set_mode(size)
pygame.display.set_mode((1920, 1080))
m = 0
running = True
board = Board(10, 10)
menu = Menu()
button_exit = pygame.transform.scale(button_exit, (50, 50))
settings = pygame.transform.scale(settings, (50, 50))
screen.blit(background, (0, 0))
screen.blit(settings, (width - 60, 10))
screen.blit(button_exit, (10, 10))
screen.blit(button_play, (width // 4, height // 4))
s = 0
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
        if event.type == pygame.MOUSEBUTTONDOWN:
            if m == 1:
                board.get_click(event.pos)
            elif m == 0:
                menu.check_click(event.pos)
    pygame.display.flip()
    clock.tick(60)
