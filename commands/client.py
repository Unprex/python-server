# -*- coding: utf-8 -*-

from .status import *


def setupDefault(client):
    """ Expected packets from server after connection. """

    # 0:0x00 Request
    client.waitForPacket(0, [], lambda *args: None)

    # 0:0x01 Ping
    client.waitForPacket(1, [
        "Long"  # Payload
    ], handlePing, "Received ping: %s.")


def setupStatus(client):
    """ Expected packets from server after status request. """

    # 1:0x00 Request
    client.pack(0, [])

    # 1:0x01 Ping
    logging.info("Sending ping: %s", client.ping_data)
    client.ping_time = time.time()
    client.pack(1, [("Long", client.ping_data)])  # Payload

    # 1:0x00 Response
    client.waitForPacket(0, [
        ("String", 32767)  # JSON Response
    ], handleResponse, repeat=False)

    # 1:0x01 Pong
    client.waitForPacket(1, [
        "Long"  # Payload
    ], handlePong, "Received pong in %.2f ms",
        "Ping data has changed: %s", repeat=False)


state_setups = [setupDefault, setupStatus]
