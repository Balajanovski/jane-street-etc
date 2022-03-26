#!/usr/bin/env python3
# ~~~~~==============   HOW TO RUN   ==============~~~~~
# 1) Configure things in CONFIGURATION section
# 2) Change permissions: chmod +x bot.py
# 3) Run in loop: while true; do ./bot.py --test prod-like; sleep 1; done

import argparse
from collections import deque

import time
import socket
import json

from book_keeping.bid_and_ask import BidAndAsk
from book_keeping.order import Order
from book_keeping.positions import Positions
from book_keeping.directive import Dir

from typing import List, Dict

# ~~~~~============== CONFIGURATION  ==============~~~~~
team_name = "BETTERTHANON"

# ~~~~~============== MAIN LOOP ==============~~~~~

# You should put your code here! We provide some starter code as an example,
# but feel free to change/remove/edit/update any of it as you'd like. If you
# have any questions about the starter code, or what to do next, please ask us!
#
# To help you get started, the sample code below tries to buy BOND for a low
# price, and it prints the current prices for VALE every second. The sample
# code is intended to be a working example, but it needs some improvement
# before it will start making good trades!

order_id = 0

def get_order_id():
    global order_id
    order_id += 1
    return order_id

def main():
    args = parse_arguments()

    exchange = ExchangeConnection(args=args)
    bid_ask_bookkeeper = BidAndAsk()
    positions = Positions()

    def get_arbitrage_vale(is_buy_vale: bool) -> Dict[str, List[Order]]:
        ret = {"buy": [], "sell": []}
        if not("VALE" in bid_ask_bookkeeper._asks and "VALBZ" in bid_ask_bookkeeper._asks and "VALE" in bid_ask_bookkeeper._bids and "VALBZ" in bid_ask_bookkeeper._bids):
            return ret

        sell_orders = list(sorted([i.price for i in bid_ask_bookkeeper._asks["VALE" if is_buy_vale else "VALBZ"]]))
        buy_orders = list(sorted([i.price for i in bid_ask_bookkeeper._bids["VALBZ" if is_buy_vale else "VALE"]], reverse=True))

        i = 0
        while i < len(sell_orders) and i < len(buy_orders) and sell_orders[i] >= buy_orders[i]:
            ret["buy"].append(sell_orders[i])
            ret["sell"].append(buy_orders[i])
            i += 1
        
        return ret

    # Store and print the "hello" message received from the exchange. This
    # contains useful information about your positions. Normally you start with
    # all positions at zero, but if you reconnect during a round, you might
    # have already bought/sold symbols and have non-zero positions.
    hello_message = exchange.read_message()
    print("First message from exchange:", hello_message)
    for symbol in hello_message["symbols"]:
        positions.update_position(
            instrument=symbol["symbol"],
            quantity=symbol["position"],
        )

    last_log_time = time.time()

    # Here is the main loop of the program. It will continue to read and
    # process messages in a loop until a "close" message is received. You
    # should write to code handle more types of messages (and not just print
    # the message). Feel free to modify any of the starter code below.
    #
    # Note: a common mistake people make is to call write_message() at least
    # once for every read_message() response.
    #
    # Every message sent to the exchange generates at least one response
    # message. Sending a message in response to every exchange message will
    # cause a feedback loop where your bot's messages will quickly be
    # rate-limited and ignored. Please, don't do that!
    while True:
        message = exchange.read_message()

        now = time.time()

        # Some of the message types below happen infrequently and contain
        # important information to help you understand what your bot is doing,
        # so they are printed in full. We recommend not always printing every
        # message because it can be a lot of information to read. Instead, let
        # your code handle the messages and just print the information
        # important for you!
        if message["type"] == "close":
            print("The round has ended")
            break
        elif message["type"] == "error":
            print(message)
        elif message["type"] == "reject":
            print(message)
        elif message["type"] == "fill":
            if message["dir"] == Dir.BUY:
                positions.add_position(message["symbol"], message["size"])
            else:
                positions.add_position(message["symbol"], -message["size"])
        elif message["type"] == "book":
            instrument = message["symbol"]

            bid_ask_bookkeeper.set_bids([
                Order(price=bid[0], quantity=bid[1])
                for bid in
                message["buy"]
            ], instrument)

            bid_ask_bookkeeper.set_asks([
                Order(price=ask[0], quantity=ask[1])
                for ask in
                message["sell"]
            ], instrument)
        elif message["type"] == "trade":
            bid_ask_bookkeeper.account_for_trade(message["symbol"], Order(price=message["price"], quantity=message["size"]))

        if now > last_log_time + 5:
            last_log_time = now
            bid_ask_bookkeeper.console_log()
            positions.console_log()
        
        res = get_arbitrage_vale(True)
        res2 = get_arbitrage_vale(False)

        if len(res["buy"]) > 0:
            for p in res["buy"]:
                exchange.send_add_message(order_id=get_order_id(), symbol="VALE", dir=dir.BUY, price=p, size=1)
            for p in res["sell"]:
                exchange.send_add_message(order_id=get_order_id(), symbol="VALBZ", dir=dir.SELL, price=p, size=1)
            exchange.send_convert_message(order_id=get_order_id(), symbol="VALE", dir=dir.SELL, size = len(res["buy"]))
        elif len(res2["buy"]) > 0:
            for p in res2["buy"]:
                exchange.send_add_message(order_id=get_order_id(), symbol="VALE", dir=dir.SELL, price=p, size=1)
            for p in res2["sell"]:
                exchange.send_add_message(order_id=get_order_id(), symbol="VALBZ", dir=dir.BUY, price=p, size=1)
            exchange.send_convert_message(order_id=get_order_id(), symbol="VALE", dir=dir.BUY, size = len(res2["buy"]))


# ~~~~~============== PROVIDED CODE ==============~~~~~

# You probably don't need to edit anything below this line, but feel free to
# ask if you have any questinos about what it is doing or how it works. If you
# do need to change anything below this line, please feel free to


class ExchangeConnection:
    def __init__(self, args):
        self.message_timestamps = deque(maxlen=500)
        self.exchange_hostname = args.exchange_hostname
        self.port = args.port
        self.exchange_socket = self._connect(add_socket_timeout=args.add_socket_timeout)

        self._write_message({"type": "hello", "team": team_name.upper()})

    def read_message(self):
        """Read a single message from the exchange"""
        message = json.loads(self.exchange_socket.readline())
        if "dir" in message:
            message["dir"] = Dir(message["dir"])
        return message

    def send_add_message(
        self, order_id: int, symbol: str, dir: Dir, price: int, size: int
    ):
        """Add a new order"""
        self._write_message(
            {
                "type": "add",
                "order_id": order_id,
                "symbol": symbol,
                "dir": dir,
                "price": price,
                "size": size,
            }
        )

    def send_convert_message(self, order_id: int, symbol: str, dir: Dir, size: int):
        """Convert between related symbols"""
        self._write_message(
            {
                "type": "convert",
                "order_id": order_id,
                "symbol": symbol,
                "dir": dir,
                "size": size,
            }
        )

    def send_cancel_message(self, order_id: int):
        """Cancel an existing order"""
        self._write_message({"type": "cancel", "order_id": order_id})

    def _connect(self, add_socket_timeout):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        if add_socket_timeout:
            # Automatically raise an exception if no data has been recieved for
            # multiple seconds. This should not be enabled on an "empty" test
            # exchange.
            s.settimeout(5)
        s.connect((self.exchange_hostname, self.port))
        return s.makefile("rw", 1)

    def _write_message(self, message):
        json.dump(message, self.exchange_socket)
        self.exchange_socket.write("\n")

        now = time.time()
        self.message_timestamps.append(now)
        if len(
            self.message_timestamps
        ) == self.message_timestamps.maxlen and self.message_timestamps[0] > (now - 1):
            print(
                "WARNING: You are sending messages too frequently. The exchange will start ignoring your messages. Make sure you are not sending a message in response to every exchange message."
            )


def parse_arguments():
    test_exchange_port_offsets = {"prod-like": 0, "slower": 1, "empty": 2}

    parser = argparse.ArgumentParser(description="Trade on an ETC exchange!")
    exchange_address_group = parser.add_mutually_exclusive_group(required=True)
    exchange_address_group.add_argument(
        "--production", action="store_true", help="Connect to the production exchange."
    )
    exchange_address_group.add_argument(
        "--test",
        type=str,
        choices=test_exchange_port_offsets.keys(),
        help="Connect to a test exchange.",
    )

    # Connect to a specific host. This is only intended to be used for debugging.
    exchange_address_group.add_argument(
        "--specific-address", type=str, metavar="HOST:PORT", help=argparse.SUPPRESS
    )

    args = parser.parse_args()
    args.add_socket_timeout = True

    if args.production:
        args.exchange_hostname = "production"
        args.port = 25000
    elif args.test:
        args.exchange_hostname = "test-exch-" + team_name
        args.port = 25000 + test_exchange_port_offsets[args.test]
        if args.test == "empty":
            args.add_socket_timeout = False
    elif args.specific_address:
        args.exchange_hostname, port = args.specific_address.split(":")
        args.port = int(port)

    return args


if __name__ == "__main__":
    # Check that [team_name] has been updated.
    assert (
        team_name != "REPLACEME"
    ), "Please put your team name in the variable [team_name]."

    main()
