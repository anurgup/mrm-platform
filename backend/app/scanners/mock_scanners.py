"""Mock scanners — hardcoded synthetic assets so the discovery pattern is
demoable without real credentials. Real MLflow/SageMaker/GitHub/AzureML
integrations are a later, customer-specific story; these establish the
shape every real scanner will follow."""

from app.scanners.scanner import DiscoveredAsset, Scanner


class MockMLflowScanner(Scanner):
    async def scan(self) -> list[DiscoveredAsset]:
        return [
            DiscoveredAsset(
                name="credit-risk-model-v5", source="mlflow", environment="production",
                owner="Unknown", description="MLflow experiment run discovered via registry scan.",
            ),
            DiscoveredAsset(
                name="churn-prediction-exp", source="mlflow", environment="staging",
                owner="Unknown", description="MLflow experiment run discovered via registry scan.",
            ),
        ]


class MockSageMakerScanner(Scanner):
    async def scan(self) -> list[DiscoveredAsset]:
        return [
            DiscoveredAsset(
                name="fraud-detection-endpoint", source="sagemaker", environment="production",
                owner="Unknown", description="Deployed SageMaker endpoint discovered via account scan.",
            ),
        ]


class MockGitHubScanner(Scanner):
    async def scan(self) -> list[DiscoveredAsset]:
        return [
            DiscoveredAsset(
                name="lending-ml-models", source="github", environment="staging",
                owner="Unknown", description="Repository containing model training/inference code.",
            ),
        ]


class MockAzureMLScanner(Scanner):
    async def scan(self) -> list[DiscoveredAsset]:
        return []
