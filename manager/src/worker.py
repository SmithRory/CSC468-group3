from dataclasses import dataclass

@dataclass
class Worker:
    container_id: str
    commands: list # List of the command numbers currently running in worker
    route_key: str

@dataclass
class UserIds:
    user_id: str
    assigned_worker: str
    last_seen: float
