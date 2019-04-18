# -*- coding: utf-8 -*-

import socket
import logging
import common
from terminal import Terminal, TerminalHandler
from threading import Thread


MAX_HOST = 10
serverIp = ("192.168.1.40", 23456)
running = False
hosts = []


def handle_input(term, text):
    global running, hosts

    text = text.strip().lower()
    logging.debug("Command: %s", text)

    if text == "stop":
        running = False
        for h in hosts:
            h.running = False
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(serverIp)
        term.stop()
    elif text == "list":
        for h in hosts:
            if h.running:
                try:
                    h._send(0, b"")
                except ConnectionResetError:
                    h.running = False
                    h.join()
        hosts = [t for t in hosts if t.is_alive()]
        logging.info("%s clients online:", len(hosts))
        for h in hosts:
            logging.info("%s: %s", h.address, h.running)
    elif text == "ping":
        for h in hosts:
            h._send(1, b"Test")


class Client(common.Client, Thread):
    def __init__(self, client, address):
        Thread.__init__(self)
        common.Client.__init__(self, client, address)
        self.running = running

    def run(self):
        try:
            logging.debug("Listening...")
            self._listen_loop()
        except Exception:
            logging.exception("Exception in run")

    def _connected(self):
        logging.info("%s connected.", self.address)

    def _disconnected(self):
        logging.info("%s disconnected.", self.address)


def main():
    global running, hosts
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    s.bind(("", serverIp[1]))

    s.listen(MAX_HOST + 2)

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
        h.socket.close()
        h.join()

    s.close()


if __name__ == "__main__":
    term = Terminal(handle_input)
    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(levelname)-5s] (%(threadName)-10s) %(message)s',
        handlers=[TerminalHandler(term)])  # logging.StreamHandler()

    main()
