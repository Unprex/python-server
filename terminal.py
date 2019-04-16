# -*- coding: utf-8 -*-

import curses
from threading import Thread


class Terminal(Thread):
    def __init__(self, ):
        Thread.__init__(self)
        self.running = False

        self.prompt_text = ">"
        self.lines_start = 1
        self.prompt_x = len(self.prompt_text)

    def run(self):
        self.running = True
        curses.wrapper(self.main_loop)

    def main_loop(self, stdscr):
        k = 0
        input_text = ""
        input_x = self.prompt_x + len(self.input_text)
        cursor_x = self.prompt_x
        lines = []
        insert = True

        stdscr.keypad(False)  # TODO: Fix Numeric Keypad

        stdscr.clear()
        stdscr.refresh()

        while self.running:
            stdscr.clear()
            height, width = stdscr.getmaxyx()

            if k == curses.KEY_RIGHT:
                cursor_x += 1
            elif k == curses.KEY_LEFT:
                cursor_x -= 1
            elif k == curses.KEY_ENTER or k == 10 or k == 13:
                lines.append(input_text)
                while len(lines) > height - self.lines_start - 1:
                    lines.pop(0)
                input_text = ""
            elif k == curses.KEY_BACKSPACE or k == 8:
                if cursor_x > self.prompt_x:
                    pos = cursor_x - self.prompt_x
                    input_text = input_text[:pos - 1] + input_text[pos:]
                    cursor_x -= 1
            elif k == curses.KEY_DC or k == 127:
                if cursor_x >= self.prompt_x:
                    pos = cursor_x - self.prompt_x
                    input_text = input_text[:pos] + input_text[pos + 1:]
            elif k == curses.KEY_HOME:
                cursor_x = self.prompt_x
            elif k == curses.KEY_END:
                cursor_x = input_x
            elif k == curses.KEY_IC:
                insert = not insert
            elif k == curses.KEY_EIC:
                insert = False
            else:
                char = chr(k)
                char_text = curses.keyname(k).decode("ascii")
                if len(char_text) > 1 and char_text[0] == "^":
                    pass
                elif len(char_text) > 1 and char_text[0:4] == "ALT_":
                    pass
                elif char.isprintable():
                    pos = cursor_x - self.prompt_x
                    if insert:
                        input_text = input_text[:pos] + char + input_text[pos:]
                    else:
                        input_text = input_text[:pos] + \
                            char + input_text[pos + len(char):]
                    cursor_x += len(char)

            stdscr.move(height - 1, cursor_x)
            stdscr.refresh()
            k = stdscr.getch()
