from app.scanners.mock_scanners import (
    MockAzureMLScanner,
    MockGitHubScanner,
    MockMLflowScanner,
    MockSageMakerScanner,
)
from app.scanners.scanner import DiscoveredAsset, Scanner

__all__ = [
    "DiscoveredAsset",
    "MockAzureMLScanner",
    "MockGitHubScanner",
    "MockMLflowScanner",
    "MockSageMakerScanner",
    "Scanner",
    "get_configured_scanners",
]


def get_configured_scanners() -> list[Scanner]:
    """Return the list of scanners to run. In production this would check
    env vars / config to determine which sources are enabled and configured
    with credentials. For MVP, return all mocks unconditionally."""
    return [
        MockMLflowScanner(),
        MockSageMakerScanner(),
        MockGitHubScanner(),
        MockAzureMLScanner(),
    ]
