from dataclasses import dataclass
import time

''' This is a temporary replacement for Reddis cache
for use in the 1 user workload test only. Going forward
Reddis will be implemented and replace this file.
'''

@dataclass
class Quote:
    stock_name: str
    value: float
    timestamp: float

cache = {} # {stock_name: Quote}
UPDATE_FREQ = 4 # Values are outdated after 4 seconds