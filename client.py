# -*- coding: utf-8 -*-

import select
import socket as sk
import logging

import common
import terminal

import commands.client
import commands.command

MAX_LOOP_TIME = 0.1  # s
server_ip = ("localhost", 23456)


class Client(common.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.initState(commands.client.state_setups,
                       commands.command.state_handlers, [0, 0])

    def commandInput(self, term, text):
        """ Called by the terminal when user input. """
        try:
            command = text.split(" ")
            assert len(command) > 0
            command[0] = command[0].strip().lower()

            logging.debug("Command: %s", " ".join(command))
            term.appendHistory(" ".join(command))

            if command[0] == "exit":  # Stops the client, always active.
                self.stop()
            else:
                self.commandHandle(self, command)
        except Exception:
            logging.exception("Exception in handleInput.")

    def connected(self):
        logging.info("Connected to %s.", self.address)

    def disconnected(self):
        logging.info("Disconnected from %s.", self.address)


def main(term):
    socket = sk.socket(sk.AF_INET, sk.SOCK_STREAM)

    logging.info("Connecting to server...")
    try:
        socket.connect(server_ip)
    except (ConnectionAbortedError,
            ConnectionRefusedError,
            ConnectionResetError):
        logging.error("Connection failed.")
    else:
        client = Client(socket, server_ip)
        try:
            client.start()
            term.callback = client.commandInput

            outputs = []

            # Loops when the socket is ready or every MAX_LOOP_TIME seconds.
            while client.is_alive():
                readable, writable, exceptional = select.select(
                    [socket], outputs, [socket], MAX_LOOP_TIME)

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
                        client.data_queue.put(data)  # TODO: public method
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

    def commandInput(term, text):
        """ Handles terminal input before the client creation. """
        text = text.strip().lower()
        term.appendHistory(text)
        logging.warning("Unhandled Command: %s", text)

    term = terminal.Terminal(commandInput)

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
