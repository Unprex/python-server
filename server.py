# -*- coding: utf-8 -*-

import socket
import logging
from terminal import Terminal, TerminalHandler
from threading import Thread


MAX_HOST = 10
serverIp = ("192.168.1.40", 23456)
running = False


def handle_input(term, text):
    global running

    text = text.strip().lower()
    logging.debug("Command: %s", text)

    if text == "stop":
        running = False
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(serverIp)
        term.stop()


class Client(Thread):
    def __init__(self, client, address):
        Thread.__init__(self)

        logging.debug("%s connected.", address)
        self.client = client
        self.address = address

    def run(self):
        logging.debug("Listening...")
        while running:
            self._recv(4)
        self.client.close()

    def _recv(self, size):
        byte = self.client.recv(size)
        while len(byte) == 0 and running:
            byte = self.client.recv(size)
        if running:
            logging.debug("Received: %s", byte)
            return byte


def main():
    global running
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    s.bind(("", serverIp[1]))

    s.listen(MAX_HOST + 2)

    hosts = []
    running = True

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


if __name__ == "__main__":
    term = Terminal(handle_input)
    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(levelname)-5s] (%(threadName)-10s) %(message)s',
        handlers=[TerminalHandler(term)])  # logging.StreamHandler()

    main()
