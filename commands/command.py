# -*- coding: utf-8 -*-

import time
import logging


def commandDefault(client, command):
    """ Handles default client commands (state 0). """
    if command[0] == "ping":  # Sends a ping to the server.
        # 0:0x00 Handshake
        client.pack(0, [
            ("VarInt", -1),  # Protocol Version
            ("String", client.address[0]),  # Server Address (255)
            ("Unsigned Short", client.address[1]),  # Server Port
            ("VarInt", 1)  # Next State Enum (ping)
        ])

        try:
            assert len(command) == 2
            client.ping_data = int(command[1])
        except (AssertionError, ValueError):
            client.ping_data = int(time.time() * 1000)

        client.setState(1)


def commandStatus(client, command):
    """ Handles client commands in state 1. """
    if command[0] == "stop":  # Exit state 1.
        logging.warning("Exiting status request state.")

        client.setState(0)


state_handlers = [commandDefault, commandStatus]
