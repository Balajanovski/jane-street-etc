from dataclasses import dataclass


@dataclass
class Order:
    price: int
    quantity: int
