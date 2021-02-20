# -*- coding: utf-8 -*-

import logging
import queue

from threading import Thread


def twosComp(value, bits):
    """ Compute the 2's complement of int value. """
    if (value & (1 << (bits - 1))) != 0:
        value = value - (1 << bits)
    return value


def writeVarInt(value, size):
    """ Returns the VarInt representation of value. """
    byte = bytearray()
    while True:
        temp = value & 0x7F
        value >>= 7
        value &= int('1' * (32 * size - 7), 2)
        if value != 0:
            temp |= 0x80
        byte.append(temp)
        if value == 0:
            break
    return byte


class NoDataError(Exception):
    """ When the client doesn't receive any data. """

    def __init__(self, where):
        self.where = where

    def __str__(self):
        return "No data received (" + str(self.where) + ")."


class Client(Thread):
    def __init__(self, socket, address):
        Thread.__init__(self)
        self.socket = socket
        self.address = address

        self.running = False

        self.currentData = bytearray()
        self.dataQueue = queue.Queue()
        self.taskCount = 0

        self.connected()

    def run(self):
        """ Executed when the thread starts. """
        try:
            logging.debug("Listening...")
            self.running = True
            data = self.dataQueue.get()

            # Main loop.
            while self.running:
                self.taskCount += 1
                if data is None:
                    raise NoDataError("Packet")

                self.currentData += bytearray(data)
                self.recv()  # TODO : Check if all data is used.
                while self.taskCount > 0:
                    self.dataQueue.task_done()
                    self.taskCount -= 1

                data = self.dataQueue.get()
        except NoDataError:  # If the server disconnects.
            logging.warning("No data received.")
        except Exception:
            logging.exception("Exception in run.")

        while self.taskCount > 0:
            self.dataQueue.task_done()
            self.taskCount -= 1

        self.disconnected()

    def send(self, packetId, data):
        data = writeVarInt(packetId, 1) + data
        send = bytes(writeVarInt(len(data), 1) + data)
        logging.debug("Sending %s.", send)

        self.socket.send(send)  # TODO: Handle potential errors.

    def recv(self):
        # Read packet info and data.
        left, _ = self.readVarInt(1)  # Length
        if left <= 0:
            logging.warning("Received packet of length %s.", left)
            while len(self.currentData) > 0 and self.currentData[0] == 0:
                # Removing b"\x00" bytes (assuming erroneous data).
                self.currentData.pop(0)
            return
        packetId, length = self.readVarInt(1)

        logging.debug("Received packet %s of size %s.", packetId, left)
        left -= length
        assert left >= 0

        self.waitForData(left, "Byte")

        byte = self.currentData[:left]
        self.currentData = self.currentData[left:]

        logging.debug("Data: %s.", bytes(byte))

    def waitForData(self, size, where):
        """ Wait for enough data to be received. """
        while len(self.currentData) < size:
            data = self.dataQueue.get()
            self.taskCount += 1
            if data is None:
                raise NoDataError(where)
            self.currentData += bytearray(data)

    def readVarInt(self, size):
        """ Returns a VarInt value and its size from the currentData. """
        value, i = 0, 0
        while True:
            self.waitForData(1, "VarInt")
            byte = self.currentData.pop(0)
            value |= (byte & 0x7F) << 7 * i
            i += 1
            if not byte & 0x80:
                break
        if i > 5 * size:
            raise RuntimeError("VarInt longer than expected.")
        return twosComp(value, 32 * size), i

    def stop(self):
        self.running = False
        self.dataQueue.put(None)
        self.join()

    def connected(self):
        logging.debug("Connected: %s", self.address)

    def disconnected(self):
        logging.debug("Disconnected: %s", self.address)
