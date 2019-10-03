# -*- coding: utf-8 -*-

import select
import socket as sk
import logging
import queue

from threading import Thread

# import common
from terminal import Terminal, TerminalHandler

commands = {"stop": "stop", "ping": "ping"}


def twosComp(value, bits):
    """ Compute the 2's complement of int value. """
    if (value & (1 << (bits - 1))) != 0:
        value = value - (1 << bits)
    return value


LOOP_TIME = 0.1  # s
serverIp = ("localhost", 23456)


class NoDataError(Exception):
    """ When the client doesn't receive any data. """

    def __init__(self, where):
        self.where = where

    def __str__(self):
        return "No data received (" + str(self.where) + ")."


class Client(Thread):  # (common.Client):
    def __init__(self, socket, address, term, inputQueue):
        Thread.__init__(self)
        self.socket = socket
        self.address = address
        self.currentData = bytearray()
        self.dataQueue = queue.Queue()
        self.taskCount = 0

        self.term = term
        self.inputQueue = inputQueue
        # self.listen_loop = Thread(target=self._listen_loop)
        # common.Client.__init__(self, socket, address)
        self._connected()

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
                        self.socket.send(b"\x05\x01Test")

                    self.inputQueue.task_done()

                # Data receiving loop.
                try:
                    data = self.dataQueue.get_nowait()
                except queue.Empty:
                    pass  # If there isn't any packet received.
                else:
                    self.taskCount += 1
                    if data is None:
                        raise NoDataError("Packet")
                    self.currentData += bytearray(data)
                    self._recv()  # TODO : Check if all data is used.
                    while self.taskCount > 0:
                        self.dataQueue.task_done()
                        self.taskCount -= 1

        except NoDataError:  # If the server disconnects.
            logging.warning("No data received.")
        except Exception:
            logging.exception("Exception in run.")
        while self.taskCount > 0:
            self.dataQueue.task_done()
            self.taskCount -= 1
        self._disconnected()

    def _connected(self):
        logging.info("Connected to %s.", self.address)

    def _disconnected(self):
        logging.info("Disconnected from %s.", self.address)

    def _recv(self):
        # Read packet info and data.
        left, _ = self._readVarInt(1)  # Length
        if left <= 0:
            logging.warning("Received packet of length %s.", left)
            while len(self.currentData) > 0 and self.currentData[0] == 0:
                # Removing b"\x00" bytes (assuming erroneous data).
                self.currentData.pop(0)
            return
        packetId, length = self._readVarInt(1)

        logging.debug("Received packet %s of size %s.", packetId, left)
        left -= length
        assert left >= 0

        while len(self.currentData) < left:
            data = self.dataQueue.get()
            self.taskCount += 1
            if data is None:
                raise NoDataError("Byte")
            self.currentData += bytearray(data)

        byte = self.currentData[:left]
        self.currentData = self.currentData[left:]

        logging.debug("Data: %s.", bytes(byte))

    def _readVarInt(self, size):
        """ Returns a VarInt value and its size from the currentData. """
        value, i = 0, 0
        while True:
            while len(self.currentData) == 0:
                data = self.dataQueue.get()
                self.taskCount += 1
                if data is None:
                    raise NoDataError("VarInt")
                self.currentData += bytearray(data)

            byte = self.currentData.pop(0)
            value |= (byte & 0x7F) << 7 * i
            i += 1
            if not byte & 0x80:
                break
        if i > 5 * size:
            raise RuntimeError("VarInt longer than expected.")
        return twosComp(value, 32 * size), i


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
        logging.debug("Command: %s", text)
        inputQueue.put(text)

    term = Terminal(handleInput)

    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(levelname)-5s] (%(threadName)-10s) %(message)s',
        handlers=[TerminalHandler(term)])  # logging.StreamHandler()

    # Main program.
    try:
        main(term, inputQueue)
    except Exception:
        logging.exception("Exception in \"main\".")

    term.stop()
