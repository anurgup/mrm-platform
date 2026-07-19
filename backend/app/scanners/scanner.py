"""Base interface for shadow-AI asset discovery. Each source (MLflow,
SageMaker, GitHub, ...) implements Scanner as its own subclass — adding a
new source later means adding a new subclass, never touching the
orchestration in app/services/scanner.py."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class DiscoveredAsset:
    name: str
    source: str  # e.g. "mlflow", "sagemaker", "github", "api_gateway"
    environment: str  # e.g. "development", "staging", "production"
    owner: str | None = None  # if discoverable from source metadata
    description: str | None = None


class Scanner(ABC):
    """Base interface for asset discovery."""

    @abstractmethod
    async def scan(self) -> list[DiscoveredAsset]:
        """Discover assets from this source. Return an empty list if none
        found or if the source isn't configured — never raise for "no
        results," only for an actual failure to reach the source."""
