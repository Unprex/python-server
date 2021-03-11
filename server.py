# -*- coding: utf-8 -*-

import select
import socket as sk
import logging

import common
import terminal

import commands.server

MAX_HOST = 10
MAX_LOOP_TIME = 0.1  # s
server_ip = ("", 23456)  # ("192.168.1.40", 23456)
running = False
hosts = {}

server_version = ("test", -1)
motd = "Hello World !"

propreties = {
    "version": {
        "name": server_version[0],
        "protocol": server_version[1]},
    "clients": {
        "max": MAX_HOST,
        "online": 0,
        "sample": []},
    "description": {
        "text": motd}
}


def commandInput(term, text):
    """ Called when the terminal receives a user input. """
    global running, hosts

    command = text.split(" ")
    assert len(command) > 0
    command[0] = command[0].strip().lower()

    logging.debug("Command: %s", " ".join(command))
    term.appendHistory(" ".join(command))

    if command[0] == "stop":  # Stops the server.
        running = False

    elif command[0] == "list":  # Lists the online clients.
        logging.info("%s clients online:", len(hosts))
        try:
            assert len(command) == 2
            state = int(command[1])
            i = 0
        except (AssertionError, ValueError):
            state = None
        for h in hosts.values():
            if state is None:
                logging.info("%s in state %s.", h.address, h.state)
            elif state == h.state:
                logging.info("%s.", h.address)
                i += 1
        if state is not None:
            logging.info("%s clients in state %s.", i, state)

    elif command[0] == "ping":   # Sends a ping to every online client.
        try:
            assert len(command) == 2
            ping_data = int(command[1])
        except (AssertionError, ValueError):
            ping_data = int(common.time.time() * 1000)
        logging.info("Sending ping: %s", ping_data)
        i = 0
        for h in hosts.values():
            if h.state == 0:
                h.ping_data = ping_data
                h.ping_time = common.time.time()
                h.pack(1, [("Long", h.ping_data)])  # Payload
                i += 1
        logging.info("%s/%s pings sent.", i, len(hosts))


class Client(common.Client):
    """ Handles client-server synchronization. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.server_propreties = propreties  # Create reference

        # Command handlers can be used to send command as client.
        self.initState(commands.server.state_setups, False, [0, 0])

    def connected(self):
        """ When the client connects """
        logging.info("%s connected.", self.address)

    def disconnected(self):
        """ When the client disconnects """
        logging.info("%s disconnected.", self.address)
        if self.address in propreties["clients"]["sample"]:
            propreties["clients"]["sample"].remove(self.address)
        propreties["clients"]["online"] -= 1
        self.socket.close()


def main():
    global running, hosts

    # Creating server.
    server = sk.socket(sk.AF_INET, sk.SOCK_STREAM)
    server.setblocking(0)
    server.bind(server_ip)
    server.listen(MAX_HOST + 2)

    inputs = [server]
    outputs = []

    running = True
    logging.info("Listening for connections...")

    # Loops when a socket is ready or every MAX_LOOP_TIME seconds.
    while inputs and running:
        readable, writable, exceptional = select.select(
            inputs, outputs, inputs, MAX_LOOP_TIME)

        # When a socket receives something.
        for s in readable:
            if s is server:  # If the socket is the server (new connection).
                client, address = s.accept()
                client.setblocking(0)
                inputs.append(client)
                hosts[client] = Client(client, address)
                hosts[client].start()
                propreties["clients"]["online"] += 1
                propreties["clients"]["sample"].append(address)
            else:
                data = None
                try:
                    # Socket can be closed when disconnecting with exception
                    if hosts[s].running:
                        data = s.recv(1024)
                except (ConnectionAbortedError,
                        ConnectionRefusedError,
                        ConnectionResetError):
                    logging.warning("Connection failed with %s.",
                                    s.getpeername())
                if data:  # If data is None / b'': the client disconnected.
                    hosts[s].data_queue.put(data)  # TODO: public method
                else:
                    inputs.remove(s)
                    if s in outputs:
                        outputs.remove(s)
                    hosts[s].stop()
                    del hosts[s]

        # When a socket is ready to send something.
        for s in writable:
            logging.debug("%s writable", s.getpeername())

        # When a socket encounters an exception.
        for s in exceptional:
            inputs.remove(s)
            if s in outputs:
                outputs.remove(s)
            logging.warning("Socket exceptional condition for %s.",
                            s.getpeername())
            hosts[s].stop()
            del hosts[s]

    # Iterates over the hosts to disconnect them.
    for s in list(hosts):
        logging.info("Disconnecting %s.", s.getpeername())
        hosts[s].stop()
        del hosts[s]

    server.close()


if __name__ == "__main__":
    # Setting up "graphics".
    term = terminal.Terminal(commandInput)
    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(levelname)-5s] (%(threadName)-10s) %(message)s',
        handlers=[terminal.TerminalHandler(term)])  # logging.StreamHandler()

    # Main program.
    try:
        main()
    except Exception:
        logging.exception("Exception in \"main\".")

    term.stop()
