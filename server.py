import logging
import socket
from threading import Thread

logging.basicConfig(level=logging.DEBUG,
                    format='[%(levelname)-5s] (%(threadName)-10s) %(message)s')

MAX_HOST = 10

serverIp = ("192.168.1.40", 23456)


class Client(Thread):
    def __init__(self, client, address):
        Thread.__init__(self)

        logging.debug("%s connected.", address)
        self.client = client
        self.address = address

    def run(self):
        pass

socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

socket.bind(("", serverIp[1]))

socket.listen(MAX_HOST + 2)

logging.debug("Listening for connections...")
hosts = []
n = 1
while n > 0:
    client, address = socket.accept()
    t = Client(client, address)
    hosts.append(t)
    t.start()
    hosts = [t for t in hosts if t.is_alive()]
    n -= 1

for h in hosts:
    h.join()
socket.close()
