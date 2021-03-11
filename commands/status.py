# -*- coding: utf-8 -*-

import json
import time
import logging


def handleHandshake(client, data):
    """ Handshake request from client. """
    logging.debug("%s connected from %s:%s.",
                  client.address, data[1], data[2])

    logging.debug("%s client protocol: %s.",
                  client.address, data[0])

    state = data[3]
    if state == 1:
        client.setState(state)

        # 1:0x00 Response
        client.pack(0, [("String", json.dumps(client.server_propreties))])
    else:
        logging.warning("Unexpected next state: %s.", state)


def handleResponse(client, data):
    """ Data received from server after status request. """

    # 1:0x00 Response
    data = json.loads(data[0])

    serverVersionName = data["version"]["name"]
    serverVersion = data["version"]["protocol"]
    logging.info("Server in version %s (protocol %s).",
                 serverVersionName, serverVersion)

    serverDesc = data["description"]
    logging.info("Motd %s", serverDesc)

    serverOnlinePlayers = data["clients"]["online"]
    serverMaxPlayers = data["clients"]["max"]
    logging.info("%s / %s clients online.",
                 serverOnlinePlayers, serverMaxPlayers)

    if "sample" in data["clients"]:
        serverSample = data["clients"]["sample"]
        logging.info("Sample of online clients: %s", serverSample)

    if "favicon" in data:
        serverFavicon = data["favicon"]
        logging.info("Favicon: %s...", serverFavicon[:30])


def handlePing(client, data, message):
    """ Data received after ping. """

    # 0x01 Ping
    logging.info(message, data[0])
    # Pong
    client.pack(1, [("Long", data[0])])  # Payload


def handlePong(client, data, message, warning):
    """ Data received after pong. """

    # 0x01 Pong
    logging.info(message, (time.time() - client.ping_time) * 1000)

    # Verify ping data unchanged
    if client.ping_data != data[0]:
        logging.warning(warning, data[0])
