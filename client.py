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
    def __init__(self, socket, address, term, inputQueue):
        self.term = term
        self.inputQueue = inputQueue

        common.Client.__init__(self, socket, address)

    def run(self):
        """ Executed when the thread starts. """
        try:
            # Main loop.
            while True:
                # Loops continuously TODO: select Queue

                # User input loop.
                try:
                    inputText = self.inputQueue.get_nowait()
                except queue.Empty:
                    pass  # If there isn't any user input.
                else:
                    # TODO: Process input text
                    if inputText == commands["stop"]:
                        self.inputQueue.task_done()
                        break
                    elif inputText == commands["ping"]:
                        self.send(1, b"Test")

                    self.inputQueue.task_done()

                # Data receiving loop.
                try:
                    data = self.dataQueue.get_nowait()
                except queue.Empty:
                    pass  # If there isn't any packet received.
                else:
                    self.taskCount += 1
                    if data is None:
                        raise common.NoDataError("Packet")
                    self.currentData += bytearray(data)
                    self.recv()  # TODO : Check if all data is used.
                    while self.taskCount > 0:
                        self.dataQueue.task_done()
                        self.taskCount -= 1

        except common.NoDataError:  # If the server disconnects.
            logging.warning("No data received.")
        except Exception:
            logging.exception("Exception in run.")

        while self.taskCount > 0:
            self.dataQueue.task_done()
            self.taskCount -= 1

        self.disconnected()

    def connected(self):
        logging.info("Connected to %s.", self.address)

    def disconnected(self):
        logging.info("Disconnected from %s.", self.address)


def main(term, inputQueue):
    socket = sk.socket(sk.AF_INET, sk.SOCK_STREAM)

    logging.info("Connecting to server...")
    try:
        socket.connect(serverIp)
    except (ConnectionAbortedError,
            ConnectionRefusedError,
            ConnectionResetError):
        logging.error("Connection failed.")
    else:
        client = Client(socket, serverIp, term, inputQueue)
        client.start()

        outputs = []

        # Loops when the socket is ready or every LOOP_TIME seconds.
        while client.isAlive():
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
                if data:  # If data is None: the server disconnected.
                    client.dataQueue.put(data)
                    # if s not in outputs:  # To send data.
                    #     outputs.append(s)
                else:
                    client.dataQueue.put(None)
                    if s in outputs:
                        outputs.remove(s)

            # When ready to send something.
            for s in writable:
                logging.debug("Writable.")

            # When encountering an exception.
            for s in exceptional:
                client.dataQueue.put(None)
                if s in outputs:
                    outputs.remove(s)
                logging.warning("Socket exception.")

    socket.close()


if __name__ == "__main__":
    # Setting up "graphics".

    inputQueue = queue.Queue()

    def handleInput(term, text):
        """ Called by the terminal, forwards user input to client. """
        text = text.strip().lower()
        term.appendHistory(text)
        logging.debug("Command: %s", text)
        inputQueue.put(text)

    term = terminal.Terminal(handleInput)

    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(levelname)-5s] (%(threadName)-10s) %(message)s',
        handlers=[terminal.TerminalHandler(term)])  # logging.StreamHandler()

    # Main program.
    try:
        main(term, inputQueue)
    except Exception:
        logging.exception("Exception in \"main\".")

    term.stop()
