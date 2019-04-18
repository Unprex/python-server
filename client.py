import socket
import logging
import common
from terminal import Terminal, TerminalHandler
from threading import Thread, Event


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


class Client(common.Client):
    def __init__(self, socket, address, term, event):
        common.Client.__init__(self, socket, address)
        self.term = term
        self.event = event
        self.listen_loop = Thread(target=self._listen_loop)
        self.running = False

    def run(self):
        global input_text

        self.running = True
        try:
            self.listen_loop.start()

            while True:
                self.event.wait()
                if input_text == "stop":
                    self.running = False
                    break
                elif input_text == "ping":
                    self._send(1, b"Test")
        except Exception:
            logging.exception("Exception in run")
        logging.info("Disconnected from %s, %s", self.address, self.running)
        self.socket.shutdown(socket.SHUT_WR)  # TODO: end recv without server
        self.listen_loop.join()

    def _connected(self):
        logging.info("Connected to %s", self.address)

    def _disconnected(self):
        logging.error("Disconnected from %s", self.address)


def main(term, event):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    logging.debug("Connecting to server...")
    try:
        s.connect(serverIp)
    except (ConnectionAbortedError,
            ConnectionRefusedError,
            ConnectionResetError):
        logging.error("Connection failed")
    else:
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
