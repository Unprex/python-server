import socket
import logging
from terminal import Terminal, TerminalHandler
from threading import Event


serverIp = ("localhost", 23456)

event = Event()
input_text = ""


def handle_input(term, text):
    global event, input_text

    text = text.strip().lower()
    logging.debug("Command: %s", text)

    input_text = text
    event.set()
    event.clear()


class Client:
    def __init__(self, socket, address, term, event):
        logging.debug("Connected to %s", address)
        self.socket = socket
        self.address = address
        self.term = term
        self.event = event

    def run(self):
        global input_text

        while True:
            self.event.wait()
            if input_text == "stop":
                break
            elif input_text == "ping":
                ping = b"Test"
                logging.debug("Sending %s", ping)
                self.socket.send(ping)


def main(term, event):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    logging.debug("Connecting to server...")
    s.connect(serverIp)

    t = Client(s, serverIp, term, event)
    t.run()  # t.start() if Thread

    term.stop()
    s.close()


if __name__ == "__main__":
    term = Terminal(handle_input)
    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(levelname)-5s] (%(threadName)-10s) %(message)s',
        handlers=[TerminalHandler(term)])  # logging.StreamHandler()

    main(term, event)
