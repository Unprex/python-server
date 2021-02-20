# -*- coding: utf-8 -*-

import select
import socket as sk
import logging
import queue

import common
import terminal

LOOP_TIME = 0.1  # s
serverIp = ("localhost", 23456)
commands = {"stop": "stop",  # Stops the client.
            "ping": "ping"   # Sends a ping to the server.
            }


class Client(common.Client):
    def handleInput(self, term, text):
        """ Called by the terminal when user input. """
        text = text.strip().lower()
        term.appendHistory(text)
        logging.debug("Command: %s", text)

        # TODO: Process input text
        if text == commands["ping"]:
            self.send(1, b"Test")
        elif text == commands["stop"]:
            self.stop()

    def connected(self):
        logging.info("Connected to %s.", self.address)

    def disconnected(self):
        logging.info("Disconnected from %s.", self.address)


def main(term):
    socket = sk.socket(sk.AF_INET, sk.SOCK_STREAM)

    logging.info("Connecting to server...")
    try:
        socket.connect(serverIp)
    except (ConnectionAbortedError,
            ConnectionRefusedError,
            ConnectionResetError):
        logging.error("Connection failed.")
    else:
        client = Client(socket, serverIp)
        try:
            client.start()
            term.callback = client.handleInput

            outputs = []

            # Loops when the socket is ready or every LOOP_TIME seconds.
            while client.is_alive():
                readable, writable, exceptional = select.select(
                    [socket], outputs, [socket], LOOP_TIME)

                # When receiving something.
                for s in readable:
                    try:
                        data = s.recv(1024)
                    except (ConnectionAbortedError,
                            ConnectionRefusedError,
                            ConnectionResetError):
                        logging.warning("Connection failed.")
                        data = None
                    if data:  # If data is None / b'': the server disconnected.
                        client.dataQueue.put(data)
                    else:
                        client.stop()
                        if s in outputs:
                            outputs.remove(s)

                # When ready to send something.
                for s in writable:
                    logging.debug("Writable.")

                # When encountering an exception.
                for s in exceptional:
                    client.stop()
                    if s in outputs:
                        outputs.remove(s)
                    logging.warning("Socket exception.")
        except Exception:
            client.stop()
            raise

    socket.close()


if __name__ == "__main__":
    # Setting up "graphics".

    inputQueue = queue.Queue()

    def handleInput(term, text):
        """ Handles terminal input before the client creation. """
        text = text.strip().lower()
        term.appendHistory(text)
        logging.warning("Unhandled Command: %s", text)

    term = terminal.Terminal(handleInput)

    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(levelname)-5s] (%(threadName)-10s) %(message)s',
        handlers=[terminal.TerminalHandler(term)])  # logging.StreamHandler()

    # Main program.
    try:
        main(term)
    except Exception:
        logging.exception("Exception in \"main\".")

    term.stop()
