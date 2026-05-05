# Matching Engines — Jelle Pelgrims

**Source:** https://jellepelgrims.com/posts/matching_engines
**Used in:** Ch 1 (Exchanges, order types, and the limit order book)

## Overview

A matching engine operates on a limit order book to match buyers and sellers, resulting in trades. It determines price movement, as "the price at which the last trade was executed usually determines the exchange rate for whatever security is being traded."

## Limit Order Books

All incoming orders go to the matching engine, which attempts to match them against passive orders in the limit order book (LOB). The book contains unmatched limit orders divided into a bid side (ascending order) and ask side (descending order).

Key characteristics:
- **Bid**: Highest price for executing a sell order
- **Ask**: Lowest price for executing a buy order
- **Spread**: Difference between lowest ask and highest bid
- **Midpoint**: Price halfway between ask and bid ((ask+bid)/2)

Example LOB:
```
               LIMIT ORDER BOOK
          BID SIDE            ASK SIDE
     QUANTITY    PRICE   PRICE    QUANTITY
    [131.00  -  102.54 | 103.23  -   48.00]
    [32.00   -  101.87 | 103.98  -   84.00]
    [293.00  -  101.48 | 104.17  -   38.00]
    [65.00   -  101.10 | 104.75  -  127.00]
```

Bid = 102.54, ask = 103.23, spread = 0.69, midpoint = 102.885.

## Matching Algorithms

The most common algorithm is **Price/Time Priority**: orders are filled primarily based on price; at tied price levels the oldest order fills first.

### Worked Example

Starting with the LOB above, two limit buys arrive: 24 @ $102.55 and 14 @ $102.55. They don't cross, so they post:

```
          BID SIDE            ASK SIDE
     QUANTITY    PRICE   PRICE    QUANTITY
    [24.00   -  102.55 | 103.23  -   48.00]
    [14.00   -  102.55 | 103.98  -   84.00]
    [131.00  -  102.54 | 104.17  -   38.00]
    [32.00   -  101.87 | 104.75  -  127.00]
```

Then a limit sell for 40 @ $102.55 arrives. It crosses, fills the first two bids at 102.55 (38 total), then the remaining 2 shares post on the ask side:

```
          BID SIDE            ASK SIDE
     QUANTITY    PRICE   PRICE    QUANTITY
    [131.00  -  102.54 | 102.55  -    2.00]
    [32.00   -  101.87 | 103.23  -   48.00]
    [293.00  -  101.48 | 103.98  -   84.00]
    [65.00   -  101.10 | 104.17  -   38.00]
```

Note: Market orders are limit orders with limit price set to ∞ (buy) or 0 (sell).

## Python Implementation

### Order and Trade classes

```python
class Order:
    def __init__(self, order_type, side, price, quantity):
        self.type = order_type
        self.side = side.lower()
        self.price = price
        self.quantity = quantity

class Trade:
    def __init__(self, price, quantity):
        self.price = price
        self.quantity = quantity
```

### OrderBook class

```python
import sortedcontainers

class OrderBook:
    def __init__(self, bids=[], asks=[]):
        self.bids = sortedcontainers.SortedList(bids, key=lambda order: -order.price)
        self.asks = sortedcontainers.SortedList(asks, key=lambda order:  order.price)

    def __len__(self):
        return len(self.bids) + len(self.asks)

    def add(self, order):
        if order.direction == 'buy':
            self.bids.insert(self.bids.bisect_right(order), order)
        elif order.direction == 'sell':
            self.asks.insert(self.asks.bisect_right(order), order)

    def remove(self, order):
        if order.direction == 'buy':
            self.bids.remove(order)
        elif order.direction == 'sell':
            self.asks.remove(order)
```

### MatchingEngine class

```python
from threading import Thread
from collections import deque

class MatchingEngine:
    def __init__(self, threaded=False):
        self.queue = deque()
        self.orderbook = OrderBook()
        self.trades = deque()
        self.threaded = threaded
        if self.threaded:
            self.thread = Thread(target=self.run)
            self.thread.start()

    def process(self, order):
        if self.threaded:
            self.queue.append(order)
        else:
            self.match(order)

    def get_trades(self):
        return list(self.trades)

    def match(self, order):
        if order.side == 'buy' and order.price >= self.orderbook.best_ask():
            filled = 0
            consumed_asks = []
            for i in range(len(self.orderbook.asks)):
                ask = self.orderbook.asks[i]
                if ask.price > order.price:
                    break
                elif filled == order.quantity:
                    break
                if filled + ask.quantity <= order.quantity:
                    filled += ask.quantity
                    self.trades.append(Trade(ask.price, ask.quantity))
                    consumed_asks.append(ask)
                else:
                    volume = order.quantity - filled
                    filled += volume
                    self.trades.append(Trade(ask.price, volume))
                    ask.quantity -= volume
            if filled < order.quantity:
                self.orderbook.add(Order("limit", "buy", order.price, order.quantity - filled))
            for ask in consumed_asks:
                self.orderbook.remove(ask)

        elif order.side == 'sell' and order.price <= self.orderbook.best_bid():
            filled = 0
            consumed_bids = []
            for i in range(len(self.orderbook.bids)):
                bid = self.orderbook.bids[i]
                if bid.price < order.price:
                    break
                if filled == order.quantity:
                    break
                if filled + bid.quantity <= order.quantity:
                    filled += bid.quantity
                    self.trades.append(Trade(bid.price, bid.quantity))
                    consumed_bids.append(bid)
                else:
                    volume = order.quantity - filled
                    filled += volume
                    self.trades.append(Trade(bid.price, volume))
                    bid.quantity -= volume
            if filled < order.quantity:
                self.orderbook.add(Order("limit", "sell", order.price, order.quantity - filled))
            for bid in consumed_bids:
                self.orderbook.remove(bid)
        else:
            self.orderbook.add(order)

    def run(self):
        while True:
            if len(self.queue) > 0:
                order = self.queue.popleft()
                self.match(order)
```

Orders are processed via `process()`; resulting trades retrieved via `get_trades()`. The engine can optionally run in a separate thread for asynchronous processing.
