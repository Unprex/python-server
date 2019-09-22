# -*- coding: utf-8 -*-

import select
import socket as sk
import logging
import queue
# import common
from terminal import Terminal, TerminalHandler
from threading import Thread


def twosComp(value, bits):
    """compute the 2's complement of int value"""
    if (value & (1 << (bits - 1))) != 0:
        value = value - (1 << bits)
    return value


MAX_HOST = 10
LOOP_TIME = 0.1  # s
serverIp = ("", 23456)  # ("192.168.1.40", 23456)
running = False
hosts = {}


def handle_input(term, text):
    """ Called when the terminal receives a user input. """
    global running, hosts

    text = text.strip().lower()
    logging.debug("Command: %s.", text)

    if text == "stop":  # Stops the server.
        running = False
        for h in hosts.values():
            h.running = False
    elif text == "list":  # Lists the online clients.
        logging.info("%s clients online:", len(hosts))
        for h in hosts.values():
            logging.info("%s", h.address)
    elif text == "ping":  # Sends a ping to every online client.
        for h in hosts.values():
            h.socket.send(b"\x05\x01Test")


class NoDataError(Exception):
    """ When the client doesn't recieve any data. """

    def __init__(self, where):
        self.where = where

    def __str__(self):
        return "No data received (" + str(self.where) + ")"


class Client(Thread):  # (common.Client, Thread):
    """ Handles client-server synchronisation (TODO) """

    def __init__(self, socket, address):
        self.socket = socket
        self.address = address
        Thread.__init__(self)
        # common.Client.__init__(self, socket, address)
        self.currentData = bytearray()
        self.dataQueue = queue.Queue()
        self.taskCount = 0
        self._connected()

    def run(self):
        """ Executed when the thread starts. """
        try:
            logging.debug("Listening...")
            while True:
                data = self.dataQueue.get()

                self.taskCount += 1
                if data is None:
                    raise NoDataError("Packet")
                self.currentData += bytearray(data)
                self._recv()  # TODO : Check if all data is used.
                while self.taskCount > 0:
                    self.dataQueue.task_done()
                    self.taskCount -= 1
        except NoDataError:
            pass  # If the client disconnected without exceptions.
        except Exception:
            logging.exception("Exception in run")
        while self.taskCount > 0:
            self.dataQueue.task_done()
            self.taskCount -= 1
        self._disconnected()
        self.socket.close()

    def _recv(self):
        # Read packet info and data
        left, _ = self._readVarInt(1)  # Length
        if left <= 0:
            logging.warning("Received packet of length %s.", left)
            while len(self.currentData) > 0 and self.currentData[0] == 0:
                # Removing b"\x00" bytes (assuming erroneous data)
                self.currentData.pop(0)
            return
        packetId, length = self._readVarInt(1)

        logging.debug("Received packet %s of size %s.", packetId, left)
        left -= length
        assert left >= 0

        while len(self.currentData) < left:  # Wait for enouth data.
            data = self.dataQueue.get()
            self.taskCount += 1
            if data is None:
                raise NoDataError("Byte")
            self.currentData += bytearray(data)

        byte = self.currentData[:left]
        self.currentData = self.currentData[left:]

        logging.debug("Data: %s.", bytes(byte))

    def _connected(self):
        """ When the client connects """
        logging.info("%s connected.", self.address)

    def _disconnected(self):
        """ When the client disconnects """
        logging.info("%s disconnected.", self.address)

    def _readVarInt(self, size):
        """ Returns a VarInt value and its size from the currentData. """
        value, i = 0, 0
        while True:
            while len(self.currentData) == 0:  # Wait for enouth data.
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
            raise RuntimeError("VarInt longer than expected")
        return twosComp(value, 32 * size), i


def main():
    global running, hosts

    running = True

    # Creating server.
    server = sk.socket(sk.AF_INET, sk.SOCK_STREAM)
    server.setblocking(0)
    server.bind(serverIp)
    server.listen(MAX_HOST + 2)

    inputs = [server]
    outputs = []

    logging.info("Listening for connections...")

    # Loops when a socket is ready or every LOOP_TIME seconds.
    while inputs and running:
        readable, writable, exceptional = select.select(
            inputs, outputs, inputs, LOOP_TIME)

        # When a socket recives something.
        for s in readable:
            if s is server:  # If the socket is the server (new connection).
                client, address = s.accept()
                client.setblocking(0)
                inputs.append(client)
                hosts[client] = Client(client, address)
                hosts[client].start()
            else:
                try:
                    data = s.recv(1024)
                except (ConnectionAbortedError,
                        ConnectionRefusedError,
                        ConnectionResetError):
                    logging.warning("Connection failed.")
                    data = None
                if data:  # If data is None: the client disconnected.
                    hosts[s].dataQueue.put(data)
                    # if s not in outputs:  # To send data.
                    #     outputs.append(s)
                else:
                    inputs.remove(s)
                    if s in outputs:
                        outputs.remove(s)
                    hosts[s].dataQueue.put(None)  # assert data == None
                    del hosts[s]

        # When a socket is ready to send something.
        for s in writable:
            logging.debug("%s writable", s.getpeername())

        # When a socket encounters an exception.
        for s in exceptional:
            inputs.remove(s)
            if s in outputs:
                outputs.remove(s)
            logging.info("%s disconnected (exception).", s.getpeername())
            hosts[s].dataQueue.put(None)
            del hosts[s]

    # Iterates over the hosts to disconnect them.
    for s in list(hosts):
        logging.info("Disconnecting %s", s.getpeername())
        hosts[s].dataQueue.put(None)
        hosts[s].join()  # Wait for the thread to finish.
        del hosts[s]

    server.close()


if __name__ == "__main__":
    # Setting up "graphics".
    term = Terminal(handle_input)
    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(levelname)-5s] (%(threadName)-10s) %(message)s',
        handlers=[TerminalHandler(term)])  # logging.StreamHandler()

    # Main program.
    try:
        main()
    except Exception:
        logging.exception("Exception in \"main\"")

    term.stop()
