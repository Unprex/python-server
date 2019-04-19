# -*- coding: utf-8 -*-

import curses
from threading import Thread


class Terminal(Thread):
    def __init__(self, callback=lambda *args: None, press=lambda *args: None):
        Thread.__init__(self)
        self.callback = callback
        self.press = press
        self.running = False

        self.prompt_text = ">"
        self.prompt_x = len(self.prompt_text)

        self.lines = []
        self.height = 0
        self.width = 0
        self.cursor_x = 0
        self.cursor_y = 0
        self.insert = True

    def run(self):
        self.running = True
        curses.wrapper(self.main_loop)

    def stop(self):
        self.running = False
        # self.stdscr.nodelay(True)
        self.display("Press any key to exit...")

    def display(self, msg):
        # Displays the message msg in the terminal
        for line in str(msg).split("\n"):
            line = line.replace("\r", "")
            if self.width > 0:
                for i in range(0, len(line), self.width):
                    self.lines.append(line[i:i + self.width])
            else:
                self.lines.append(line)
        while len(self.lines) > self.height - 1 and self.height > 0:
            self.lines.pop(0)
        self._draw()

    def main_loop(self, stdscr):
        self.stdscr = stdscr
        k = 0
        self.input_text = ""
        input_x = self.prompt_x + len(self.input_text)
        cursor_x = self.prompt_x

        stdscr.keypad(True)  # TODO: Fix Numeric Keypad

        stdscr.clear()
        stdscr.refresh()

        while self.running:
            self.height, self.width = stdscr.getmaxyx()

            if k == curses.KEY_RIGHT:
                cursor_x += 1
            elif k == curses.KEY_LEFT:
                cursor_x -= 1
            elif k == curses.KEY_ENTER or k == 10 or k == 13:
                self.callback(self, self.input_text)
                self.input_text = ""
            elif k == curses.KEY_BACKSPACE or k == 8:
                if cursor_x > self.prompt_x:
                    pos = cursor_x - self.prompt_x
                    self.input_text = self.input_text[:pos - 1] + \
                        self.input_text[pos:]
                    cursor_x -= 1
            elif k == curses.KEY_DC or k == 127:
                if cursor_x >= self.prompt_x:
                    pos = cursor_x - self.prompt_x
                    self.input_text = self.input_text[:pos] + \
                        self.input_text[pos + 1:]
            elif k == curses.KEY_HOME:
                cursor_x = self.prompt_x
            elif k == curses.KEY_END:
                cursor_x = input_x
            elif k == curses.KEY_IC:
                self.insert = not self.insert
            elif k == curses.KEY_EIC:
                self.insert = False
            else:
                char = chr(k)
                char_text = curses.keyname(k).decode("ascii")
                if len(char_text) > 1 and char_text[0] == "^":
                    self.press(self, char_text)
                elif len(char_text) > 1 and char_text[0:4] == "ALT_":
                    self.press(self, char_text)
                elif char.isprintable() and input_x < self.width - 1:
                        # TODO: Enable longer length
                    pos = cursor_x - self.prompt_x
                    if self.insert:
                        self.input_text = self.input_text[:pos] + \
                            char + self.input_text[pos:]
                    else:
                        self.input_text = self.input_text[:pos] + \
                            char + self.input_text[pos + len(char):]
                    cursor_x += len(char)

            input_x = self.prompt_x + len(self.input_text)
            cursor_x = max(self.prompt_x, cursor_x)
            cursor_x = min(self.width - 1, input_x, cursor_x)

            self.cursor_x = cursor_x
            self.cursor_y = self.height - 1
            self.draw()
            if self.running:
                k = stdscr.getch()

    def draw(self):
        self.stdscr.clear()
        self.height, self.width = self.stdscr.getmaxyx()

        for i, l in enumerate(self.lines):
            self.stdscr.addstr(i, 0, l)

        self.stdscr.addstr(self.height - 1, 0,
                           self.prompt_text + self.input_text)
        self.stdscr.move(self.cursor_y, self.cursor_x)
        self.stdscr.refresh()


if __name__ == "__main__":
    def callback(term, text):
        if text.strip().lower() == "stop":
            term.stop()
        term.display(text)

    term = Terminal(callback)
    term.start()
    term.join()
