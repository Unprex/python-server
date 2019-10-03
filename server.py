# -*- coding: utf-8 -*-

import select
import socket as sk
import logging

import common
import terminal

MAX_HOST = 10
LOOP_TIME = 0.1  # s
serverIp = ("", 23456)  # ("192.168.1.40", 23456)
commands = {"stop": "stop",  # Stops the server.
            "list": "list",  # Lists the online clients.
            "ping": "ping"   # Sends a ping to every online client.
            }
running = False
hosts = {}


def handleInput(term, text):
    """ Called when the terminal receives a user input. """
    global running, hosts

    text = text.strip().lower()
    term.appendHistory(text)
    logging.debug("Command: %s.", text)

    if text == commands["stop"]:
        running = False

    elif text == commands["list"]:
        logging.info("%s clients online:", len(hosts))
        for h in hosts.values():
            logging.info("%s", h.address)

    elif text == commands["ping"]:
        for h in hosts.values():
            h.send(1, b"Test")


class Client(common.Client):
    """ Handles client-server synchronization (TODO). """

    def run(self):
        """ Executed when the thread starts. """
        try:
            logging.debug("Listening...")

            # Main loop.
            while True:
                data = self.dataQueue.get()

                self.taskCount += 1
                if data is None:
                    raise common.NoDataError("Packet")
                self.currentData += bytearray(data)
                self.recv()  # TODO : Check if all data is used.
                while self.taskCount > 0:
                    self.dataQueue.task_done()
                    self.taskCount -= 1

        except common.NoDataError:
            pass  # If the client disconnected without exceptions.
        except Exception:
            logging.exception("Exception in run.")
        while self.taskCount > 0:
            self.dataQueue.task_done()
            self.taskCount -= 1
        self.disconnected()
        self.socket.close()

    def connected(self):
        """ When the client connects """
        logging.info("%s connected.", self.address)

    def disconnected(self):
        """ When the client disconnects """
        logging.info("%s disconnected.", self.address)


def main():
    global running, hosts

    # Creating server.
    server = sk.socket(sk.AF_INET, sk.SOCK_STREAM)
    server.setblocking(0)
    server.bind(serverIp)
    server.listen(MAX_HOST + 2)

    inputs = [server]
    outputs = []

    running = True
    logging.info("Listening for connections...")

    # Loops when a socket is ready or every LOOP_TIME seconds.
    while inputs and running:
        readable, writable, exceptional = select.select(
            inputs, outputs, inputs, LOOP_TIME)

        # When a socket receives something.
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
                    hosts[s].dataQueue.put(None)  # TODO: assert data == None
                    del hosts[s]

        # When a socket is ready to send something.
        for s in writable:
            logging.debug("%s writable", s.getpeername())

        # When a socket encounters an exception.
        for s in exceptional:
            inputs.remove(s)
            if s in outputs:
                outputs.remove(s)
            logging.warning("%s disconnected (exception).", s.getpeername())
            hosts[s].dataQueue.put(None)
            del hosts[s]

    # Iterates over the hosts to disconnect them.
    for s in list(hosts):
        logging.info("Disconnecting %s.", s.getpeername())
        hosts[s].dataQueue.put(None)
        hosts[s].join()  # Wait for the thread to finish.
        del hosts[s]

    server.close()


if __name__ == "__main__":
    # Setting up "graphics".
    term = terminal.Terminal(handleInput)
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
