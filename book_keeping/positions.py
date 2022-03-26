import json


class Positions:
    def __init__(self):
        self._positions = {}

    def update_position(self, instrument: str, quantity: int):
        self._positions[instrument] = quantity

    def add_position(self, instrument: str, quantity: int):
        if instrument not in self._positions:
            self._positions[instrument] = 0
        self._positions[instrument] += quantity

    def get_position(self, instrument: str) -> int:
        return self._positions[instrument]

    def console_log(self):
        print("Positions\n------")
        print(json.dumps(self._positions, indent=4, sort_keys=True))
