# -*- coding: utf-8 -*-

import socket
import logging
from terminal import Terminal
from threading import Thread


class TerminalHandler(logging.StreamHandler):
    def __init__(self, terminal):
        logging.StreamHandler.__init__(self)
        self.terminal = terminal
        self.terminal.start()

    def emit(self, record):
        msg = self.format(record)
        self.terminal.display(msg)


MAX_HOST = 10

serverIp = ("192.168.1.40", 23456)

running = True


def handle_input(term, text):
    global running

    text = text.strip().lower()
    logging.debug("Command: %s", text)

    if text == "stop":
        running = False
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(serverIp)
        term.stop()


term = Terminal(handle_input)
logging.basicConfig(level=logging.DEBUG,
                    format='[%(levelname)-5s] (%(threadName)-10s) %(message)s',
                    handlers=[TerminalHandler(term)])  # StreamHandler()


class Client(Thread):
    def __init__(self, client, address):
        Thread.__init__(self)

        logging.debug("%s connected.", address)
        self.client = client
        self.address = address

    def run(self):
        pass


s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

s.bind(("", serverIp[1]))

s.listen(MAX_HOST + 2)

hosts = []


logging.debug("Listening for connections...")

while True:
    client, address = s.accept()
    if not running:
        break
    t = Client(client, address)
    hosts.append(t)
    t.start()
    hosts = [t for t in hosts if t.is_alive()]

for h in hosts:
    h.join()

s.close()
