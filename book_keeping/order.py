from dataclasses import dataclass


@dataclass
class Order:
    price: float
    quantity: float
