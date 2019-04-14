import logging
import socket

logging.basicConfig(level=logging.DEBUG,
                    format='[%(levelname)-5s] (%(threadName)-10s) %(message)s')


class Client:
    def __init__(self, client, address):
        logging.debug("%s connected.", address)
        self.client = client
        self.address = address

    def run(self):
        pass

serverIp = ("localhost", 23456)

socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

logging.debug("Connecting to server...")
socket.connect(serverIp)

t = Client(socket, serverIp)
t.run()
socket.close()
