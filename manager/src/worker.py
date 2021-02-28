from dataclasses import dataclass

@dataclass
class Worker:
    container_id: str
    commands: list # List of the command numbers currently running in worker
    route_key: str

    def __repr__(self) -> str:
        if len(self.commands) <= 10:
            return f"Worker(container_id={self.container_id}, commands={self.commands}, route_key={self.route_key}"
        return f"Worker(container_id={self.container_id}, len(commands)={len(self.commands)}, route_key={self.route_key}"

@dataclass
class UserIds:
    user_id: str
    assigned_worker: str
    last_seen: float

    def __repr__(self) -> str:
        return f"UserIds(user_id={self.user_id}, assigned_worker={self.assigned_worker}, last_seen={self.last_seen}"
