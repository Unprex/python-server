# Python Server

Communication between two scripts via sockets.

## Usage

It uses the [Curses](https://docs.python.org/3/library/curses.html) module for the UI.

To install curses it on a UNIX system:
```bash
pip install curses
```

To install curses it on a Windows system:
[https://pypi.org/project/windows-curses/](https://pypi.org/project/windows-curses/)
```bash
pip install windows-curses
```

You then have to set the `("IP", port)` of the server in *server.py* (line 11) and in *client.py* (line 8)

You can then run the *server.py* or *client.py* with python 3 (doesn't work in IDLE).

## Commands

### Client

- **stop** - Stops the client.
- **ping** - Sends a ping to the server.

### Server

- **stop** - Stops the server
- **list** - Lists the online clients.
- **ping** - Sends a ping to every client.
