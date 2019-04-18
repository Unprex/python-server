import logging


def twosComp(value, bits):
    """compute the 2's complement of int value"""
    if (value & (1 << (bits - 1))) != 0:
        value = value - (1 << bits)
    return value


def writeVarInt(value, size):
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


class Client:
    def __init__(self, socket, address):
        self.socket = socket
        self.address = address
        self._connected()

    def _send(self, packetId, data):
        data = bytearray(packetId) + data
        send = bytes(writeVarInt(len(data), 1) + data)
        logging.debug("Sending %s", send)
        try:
            self.socket.send(send)
        except (ConnectionAbortedError,
                ConnectionRefusedError,
                ConnectionResetError):
            self._disconnected()
            self.running = False
            return b""

    def _recv(self, size):
        if not self.running:
            return b""
        try:
            logging.debug("1")
            byte = self.socket.recv(size)
            logging.debug("2")
            while len(byte) == 0:
                byte = self.socket.recv(size)
                if not self.running:
                    return b""
        except (ConnectionAbortedError,
                ConnectionRefusedError,
                ConnectionResetError):
            self._disconnected()
            self.running = False
            return b""
        logging.debug("Received: %s", byte)
        return byte

    def _listen_loop(self):
        try:
            while self.running:
                left, _ = self._readVarInt(1)  # Length
                packetId, length = self._readVarInt(1)
                if not self.running:
                    return
                logging.debug("Received packet %s of size %s", packetId, left)
                left -= length
                assert left >= 0
                logging.debug("Data: %s", self._recv(left))
        except Exception:
            logging.exception("Exception in _listen_loop")

    def _readVarInt(self, size):
        value, i = 0, 0
        while True:
            byte = self._recv(1)
            if not self.running:
                return 0, 0
            byte = ord(byte)
            value |= (byte & 0x7F) << 7 * i
            if not byte & 0x80:
                break
            i += 1
        if i > 5 * size:
            raise RuntimeError("VarInt longer than expected")
        return twosComp(value, 32 * size), i

    def _connected(self):
        logging.debug("Connected: %s", self.address)

    def _disconnected(self):
        logging.debug("Disconnected: %s", self.address)
