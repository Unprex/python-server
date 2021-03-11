# Python Server

Communication between two python scripts via sockets.

## Usage

You then have to set the `("IP", port)` of the server in *client.py* (line 14) and in *server.py* (line 14).

It uses the [Curses](https://docs.python.org/3/library/curses.html) module for the UI (See [Terminal](#terminal)).

You can then run the *server.py* or *client.py* with python 3 (doesn't work in IDLE with curses).

The client/server can be used without installing the curses module by changing
the logging handler at the end of *client.py* and *server.py* and replacing
references to the `term` object in the same files:

>In *client.py*:
>
>- (line 32) In the `Client` class, `commandInput(self, term, text)`, `term.appendHistory`.
>- (line 62) In the `main(term)` function, `term.callback`.
>
>In *server.py*:
>
>- (line 43) In the `commandInput(term, text)` function, `term.appendHistory`.

An alternative method of calling the `commandInput` functions must then be used.

## Default states

Inspired by <https://wiki.vg/Protocol>

Default server commands:

- **stop** - Stops the server.
- **list [state]** - Lists the clients connected and their state.
    - Set **state** option to filter by state.
- **ping [payload (Long)]** - Sends a ping to every client in state 0.
    - Set **payload** option to send a custom signed 64-bit integer.

### State 0 (default)

The ***Client*** waits for:

- User command:
    - **exit** - Stops the client.
    - **ping [payload (Long)]** - Sends a ping to the server (changes state to 1).
        - Set **payload** option to send a custom signed 64-bit integer.

- **packet 0x00** - Request from the server.
    - Empty packet. No actions required.

- **packet 0x01** - Ping from the server.
    - Sends same data back to the server.

        Field Name | Field Type
        ---------- | ----------
        Payload    | Long

The ***Server*** waits for:

- **packet 0x00** - Handshake from the client.
    - Changes the state of the server-side client.

        Field Name       | Field Type
        ---------------- | --------------
        Protocol Version | VarInt
        Server Address   | String (255)
        Server Port      | Unsigned Short
        Next State       | VarInt Enum

- **packet 0x01** - Pong from the client.
    - Should be the same as sent by the server.

        Field Name | Field Type
        ---------- | ----------
        Payload    | Long

### State 1 (status)

The ***Client*** waits for:

- User command:
    - **exit** - Stops the client.
    - **stop** - Stops the status request (changes state to 0).

- **packet 0x00** - Response from the server.
    - JSON string containing informations about the server.

        Field Name    | Field Type
        ------------- | --------------
        JSON Response | String (32767)

- **packet 0x01** - Pong from the server.
    - Should be the same as sent by the client.

        Field Name | Field Type
        ---------- | ----------
        Payload    | Long

The ***Server*** waits for:

- **packet 0x00** - Request from the client.
    - Empty packet. Requests the server properties.

- **packet 0x01** - Ping from the client.
    - Epoch time in ms by default. Sends same data back to the client.

        Field Name | Field Type
        ---------- | ----------
        Payload    | Long


## Terminal

Simple curses terminal emulation.
Can be used independently of the client/server.

`MAX_HISTORY_SIZE` (line 7) can be used to set the command history size.

To install curses it on a UNIX system:
```bash
pip install curses
```

To install curses it on a Windows system:
[https://pypi.org/project/windows-curses/](https://pypi.org/project/windows-curses/)
```bash
pip install windows-curses
```
