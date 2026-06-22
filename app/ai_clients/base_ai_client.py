from abc import ABC, abstractmethod
from typing import Any


class AIClient(ABC):
    @abstractmethod
    async def analyze_incident(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        raise NotImplementedError
