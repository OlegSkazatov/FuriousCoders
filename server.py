# -*- coding: utf-8 -*-
# Модуль socketserver для сетевого программирования
from socketserver import *

# данные сервера
host = 'localhost'
port = 777
addr = (host, port)
user_1 = [0, 'ждём остальных']
user_2 = [0, 'ждём остальных']
spectator = ['']
spectators = []


class MyUDPHandler(DatagramRequestHandler):

    def handle(self):
        sms = self.request[0]
        socket = self.request[1]
        if sms.decode().split()[0] == 'стрельнул':
            print(1111)

        elif sms.decode().split()[0] == 'отключаюсь':
            if self.client_address in user_1:
                user_1[0] = 0
            elif self.client_address in user_2:
                user_2[0] = 0
            else:
                spectators.pop(self.client_address)

        elif sms.decode().split()[0] == 'присоединился':
            print(1)
            if user_1[0] == 0:
                socket.sendto('Вы 1'.encode(), self.client_address)
                user_1[0] = self.client_address
            elif user_2[0] == 0:
                socket.sendto('Вы 2'.encode(), self.client_address)
                user_2[0] = self.client_address
            else:
                socket.sendto('Вы наблюдатель'.encode(), self.client_address)
                spectators.append(self.client_address)

        print('client send: ', sms.decode())

        try:
            socket.sendto(user_1[1].encode(), user_1[0])
        except TypeError:
            print('ждёмс')


if __name__ == "__main__":
    server = UDPServer(addr, MyUDPHandler)
    print('starting server...')
    server.serve_forever()
