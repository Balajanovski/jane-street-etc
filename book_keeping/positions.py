import json


class Positions:
    def __init__(self):
        self._positions = {}
        self._max_positions = {
            "BOND": 100,
            "VALBZ": 10,
            "VALE": 10,
            "GS": 100,
            "MS": 100,
            "WFC": 100,
            "XFL": 100,
            "CASH": 1e18,
        }

    def update_position(self, instrument: str, quantity: int):
        self._positions[instrument] = quantity

    def add_position(self, instrument: str, quantity: int):
        if instrument not in self._positions:
            self._positions[instrument] = 0
        self._positions[instrument] += quantity

    def get_position(self, instrument: str) -> int:
        return self._positions[instrument]
    
    def get_remaining_positions(self, instrument: str, is_buying: bool) -> int:
        if instrument not in self._positions:
            return 0
        
        res = self._max_positions[instrument] - self._positions[instrument]
        if not is_buying:
            res = -res
        
        return res

    def console_log(self):
        print("Positions\n------")
        print(json.dumps(self._positions, indent=4, sort_keys=True))
