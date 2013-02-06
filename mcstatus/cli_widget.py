#!/usr/bin/env python

import sys
import socket
from argparse import ArgumentParser

from widget import main as widget_main

def main():
    parser = ArgumentParser(description="Widgets for Minecraft multiplayer server",
                            epilog="Exit status: 0 if the server can be reached, otherwise nonzero."
                           )
    parser.add_argument("host", help="target hostname")
    parser.add_argument("-p", "--port", type=int, default=25565,
                        help='UDP port of server\'s "query" service [25565]')

    options = parser.parse_args()

    widget_main(options.host, options.port)
    sys.exit(0)


if __name__=="__main__":
    main()
