from dataclasses import dataclass
import threading

@dataclass
class ThreadCommunication:
    buffer: list
    length: int
    mutex: threading.Lock