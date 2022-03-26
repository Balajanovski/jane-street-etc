from typing import List, Dict
from book_keeping.order import Order
import json
import dataclasses


class BidAndAsk:
    def __init__(self):
        self._bids: Dict[str, List[Order]] = {}
        self._asks: Dict[str, List[Order]] = {}

    def set_bids(self, bids: List[Order], instrument: str):
        self._bids[instrument] = bids

    def set_asks(self, asks: List[Order], instrument: str):
        self._asks[instrument] = asks

    def get_bids(self, instrument: str) -> List[Order]:
        return self._bids[instrument]

    def get_asks(self, instrument: str) -> List[Order]:
        return self._asks[instrument]

    def account_for_trade(self, instrument: str, order: Order):
        if len(self._bids[instrument]) == 0 or self._bids[instrument][-1].price < order.price:
            target = self._asks
        else:
            target = self._bids
        for i in range(len(target[instrument])):
            existing_order = target[instrument][i]
            if existing_order.price == order.price:
                existing_order.quantity -= order.quantity
                if existing_order.quantity == 0:
                    target[instrument].pop(i)
                break

    def console_log(self):
        print("Bids\n------")
        print(json.dumps(self._dictify(self._bids), indent=4, sort_keys=True))

        print("\nAsks\n------")
        print(json.dumps(self._dictify(self._asks), indent=4, sort_keys=True))

    @staticmethod
    def _dictify(all_orders):
        return {
            instrument: [dataclasses.asdict(order) for order in orders]
            for instrument, orders in
            all_orders.items()
        }
