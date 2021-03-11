# -*- coding: utf-8 -*-

from .status import *


def setupDefault(client):
    """ Expected packets from client after connection. """

    # 0:0x00 Handshake
    client.waitForPacket(0, [
        "VarInt",  # Protocol Version
        ("String", 255),  # Server Address
        "Unsigned Short",  # Server Port
        "VarInt"  # Next State Enum
    ], handleHandshake, repeat=False)

    # 0:0x01 Pong
    client.waitForPacket(1, [
        "Long"  # Payload
    ], handlePong, str(client.address) + " sent back pong in %.2f ms",
        str(client.address) + "'s ping data has changed: %s")


def setupStatus(client):
    """ Expected packets from client after status request. """

    # 1:0x00 Request
    client.waitForPacket(0, [], lambda *args: None, repeat=False)

    # 1:0x01 Ping
    client.waitForPacket(1, [
        "Long"  # Payload
    ], handlePing, str(client.address) + " sent ping: %s.", repeat=False)


state_setups = [setupDefault, setupStatus]
