# -*- coding: utf-8 -*-

import logging
import queue
import time

from threading import Thread
from struct import pack, unpack


def twosComp(value, bits):
    """ Compute the 2's complement of int value. """
    if (value & (1 << (bits - 1))) != 0:
        value = value - (1 << bits)
    return value


def writeBoolean(bool):
    return b'\x01' if bool else b'\x00'


def writeInt(value, size):
    byte = bytearray()
    for _ in range(size):
        byte.append(value & 0xFF)
        value >>= 8
    byte.reverse()
    return byte


def writeFloat(value, size):
    assert size in [4, 8]
    form = 'f' if size == 4 else 'd'
    return pack('>' + form, value)


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


def writeString(value):
    byte = writeVarInt(len(value), 1)
    byte.extend(value.encode("utf-8"))
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
        self.state = None

        self.ping_data = int(time.time() * 1000)
        self.ping_time = None

        self.current_data = bytearray()
        self.data_queue = queue.Queue()
        self.task_count = 0

        self.resetPackets()

        # Set functions to pack and unpack all data types
        self.data_type_handle = {
            "Boolean": (writeBoolean,
                        self.readBoolean),
            "Byte": (lambda x: writeInt(x, 1),
                     lambda: self.readInt(1, True)),
            "Unsigned Byte": (lambda x: writeInt(x, 1),
                              lambda: self.readInt(1, False)),
            "Short": (lambda x: writeInt(x, 2),
                      lambda: self.readInt(2, True)),
            "Unsigned Short": (lambda x: writeInt(x, 2),
                               lambda: self.readInt(2, False)),
            "Int": (lambda x: writeInt(x, 4),
                    lambda: self.readInt(4, True)),
            "Long": (lambda x: writeInt(x, 8),
                     lambda: self.readInt(8, True)),
            "UUID": (lambda x: writeInt(x, 16),
                     lambda: self.readInt(16, False)),
            "Float": (lambda x: writeFloat(x, 4),
                      lambda: self.readFloat(4)),
            "Double": (lambda x: writeFloat(x, 4),
                       lambda: self.readFloat(8)),
            "VarInt": (lambda x: writeVarInt(x, 1),
                       lambda: self.readVarInt(1)),
            "VarLong": (lambda x: writeVarInt(x, 2),
                        lambda: self.readVarInt(2)),
            # Needs special unpack function
            "String": (lambda x: writeString(x), None),
            "Byte Array": (lambda x: x, None)
        }

        self.connected()

    def run(self):
        """ Executed when the thread starts. """
        try:
            self.running = True
            data = self.data_queue.get()
            self.task_count += 1

            # Main loop.
            while self.running:
                if not data:
                    raise NoDataError("Packet")

                self.current_data += bytearray(data)
                self.recv()

                while self.task_count > 0:
                    self.data_queue.task_done()
                    self.task_count -= 1

                data = self.data_queue.get()
                self.task_count += 1
        except Exception:
            logging.exception("Exception in run.")
            self.running = False

        while self.task_count > 0:
            self.data_queue.task_done()
            self.task_count -= 1

        self.disconnected()

    def send(self, packet_id, data):
        data = writeVarInt(packet_id, 1) + data
        send = bytes(writeVarInt(len(data), 1) + data)
        logging.debug("Sending %s.", send)

        self.socket.send(send)  # TODO: Handle potential errors.

    def pack(self, packet_id, packet_data):
        """ Packs data to be sent """
        byte = bytearray()
        byte.extend(writeVarInt(packet_id, 1))
        for t, param in packet_data:
            try:
                byte.extend(self.data_type_handle[t][0](param))
            except KeyError:
                raise RuntimeError("Unexpected type: " + str(t))

        logging.debug("Sending packet  0x%02X (%03d) of size %s.",
                      packet_id, packet_id, len(byte))

        send = bytes(writeVarInt(len(byte), 1) + byte)

        self.socket.send(send)

    def recv(self):
        # Read packet info and data.
        left, _ = self.readVarInt(1)  # Length
        if left <= 0:
            logging.warning("Received packet of length %s.", left)
            while len(self.current_data) > 0 and self.current_data[0] == 0:
                # Removing b"\x00" bytes (assuming erroneous data).
                self.current_data.pop(0)
            return
        packet_id, length = self.readVarInt(1)

        logging.debug("Received packet %s of size %s.", packet_id, left)
        left -= length
        assert left >= 0

        self.waitForData(left, "Byte")

        # Check if the packet was expected
        if packet_id in self.packet_wait:
            # Call function with unpacked data
            packet_data, packet_funct, repeat = self.packet_wait[packet_id]
            if not repeat:  # No longer expecting packet
                del self.packet_wait[packet_id]
            packet_funct(self, self.unpack(left, packet_data))
        else:
            self.waitForData(left, "Byte")
            byte = self.current_data[:left]
            self.current_data = self.current_data[left:]

            if len(byte) > 30:
                logging.debug("Data: %s...", byte.hex()[:30])
            else:
                logging.debug("Data: %s.", byte.hex())
        if len(self.packet_wait) <= 0:
            # If no more expected data
            if self.state:
                # Return to fallback state
                self.setState(self.state_fallbacks[self.state])
            else:
                # Stop client
                self.running = False
                self.data_queue.put(None)

    def unpack(self, left, expected_data):
        """ Unpacks data to be used """
        result = []

        for n, t in enumerate(expected_data):
            if isinstance(t, tuple):
                if t[0] == "String":
                    data, length = self.readString(t[1])
                elif t[0] == "Byte Array":
                    param = t[1]  # Determines the size of the Byte Array

                    # Fixed size (ex: param=256).
                    if not isinstance(param, str):
                        length = param
                    # Size determined by the last data (ex: param="lastVarInt")
                    elif len(param) > 4 and param.startswith("last"):
                        if n > 0 and expected_data[n - 1] == param[4:]:
                            length = result[n - 1]
                        else:
                            raise RuntimeError("Last type doesn't match")
                    # Until the end of the packet (param="left").
                    elif param == "left":
                        length = left
                    else:
                        raise RuntimeError("Unexpected parameter: "
                                           + str(param))

                    self.waitForData(length,
                                     "Byte Array of length %s" % length)
                    data = self.current_data[:length]
                    self.current_data = self.current_data[length:]
                else:
                    raise RuntimeError("Unexpected type received: " + str(t))
            else:
                data, length = self.data_type_handle[t][1]()

            left -= length
            if left < 0:
                raise RuntimeError("Received more than expected (%s)." % -left)
            result.append(data)

        assert left == 0  # Assert all data is used

        return result

    def initState(self, setups, handlers, fallbacks, default=0):
        if handlers:
            assert len(setups) == len(handlers)
        assert len(setups) == len(fallbacks)
        self.state_setups = setups
        self.state_handlers = handlers
        self.state_fallbacks = fallbacks
        self.setState(default)

    def setState(self, state):
        self.state = state
        self.resetPackets()
        if self.state_handlers:
            self.commandHandle = self.state_handlers[state]
        self.state_setups[state](self)

    def waitForPacket(self, packet_id, packet_data, packet_funct,
                      *args, repeat=True):
        """ Runs the function associated to the reception of a packet. """
        assert packet_id not in self.packet_wait
        self.packet_wait[packet_id] = (
            packet_data, lambda c, d: packet_funct(c, d, *args), repeat)

    def resetPackets(self):
        self.packet_wait = {}

    def waitForData(self, size, where):
        """ Wait for enough data to be received. """
        while len(self.current_data) < size:
            data = self.data_queue.get()
            self.task_count += 1
            if not data:
                raise NoDataError(where)
            self.current_data += bytearray(data)

    def readBoolean(self):
        self.waitForData(1, "Boolean")
        data = True if self.current_data.pop(0) == b'\x01' else False
        return data, 1

    def readInt(self, size, signed):
        """ Returns a Int value and its size from the current_data. """
        self.waitForData(size, "Int")
        byte = self.current_data[:size]
        self.current_data = self.current_data[size:]
        return int.from_bytes(byte, "big", signed=signed), size

    def readFloat(self, size):
        """ Returns a Float value and its size from the current_data. """
        assert size in [4, 8]
        form = 'f' if size == 4 else 'd'
        self.waitForData(size, "Float")
        byte = self.current_data[:size]
        self.current_data = self.current_data[size:]
        return unpack('>' + form, byte)[0], size

    def readVarInt(self, size):
        """ Returns a VarInt value and its size from the current_data. """
        value, i = 0, 0
        while True:
            self.waitForData(1, "VarInt")
            byte = self.current_data.pop(0)
            value |= (byte & 0x7F) << 7 * i
            i += 1
            if not byte & 0x80:
                break
        if i > 5 * size:
            raise RuntimeError("VarInt longer than expected.")
        return twosComp(value, 32 * size), i

    def readString(self, max_length):
        """ Returns a String value and its size from the current_data. """
        length, vlength = self.readVarInt(1)
        if length > max_length:
            raise RuntimeError("String longer than expected")
        self.waitForData(length, "String")
        string = self.current_data[:length].decode("utf-8")
        self.current_data = self.current_data[length:]
        return string, length + vlength

    def stop(self):
        self.running = False
        self.data_queue.put(None)
        self.join()

    def connected(self):
        logging.debug("Connected: %s", self.address)

    def disconnected(self):
        logging.debug("Disconnected: %s", self.address)
