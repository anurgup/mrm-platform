from enum import Enum
from typing import Any

from sqlalchemy import Enum as SAEnum
from sqlalchemy.types import TypeEngine


def sa_enum(enum_cls: type[Enum]) -> TypeEngine[Any]:
    """A generic (non-dialect-specific) enum column: VARCHAR + CHECK constraint
    on every backend, stored as the enum's string VALUE, not its Python name."""
    return SAEnum(enum_cls, values_callable=lambda cls: [e.value for e in cls], native_enum=False)


class BusinessFunction(str, Enum):
    LOAN_UNDERWRITING = "Loan Underwriting"
    FRAUD_DETECTION = "Fraud Detection"
    COLLECTIONS = "Collections"
    CUSTOMER_SERVICE = "Customer Service"
    DOCUMENT_PROCESSING = "Document Processing"
    RISK_ANALYTICS = "Risk Analytics"


class ModelType(str, Enum):
    MACHINE_LEARNING = "Machine Learning"
    DEEP_LEARNING = "Deep Learning"
    GENERATIVE_AI = "Generative AI"
    RULE_BASED_ENGINE = "Rule Based Engine"
    THIRD_PARTY_AI_API = "Third Party AI API"


class DeploymentStage(str, Enum):
    DEVELOPMENT = "Development"
    TESTING = "Testing"
    PRODUCTION = "Production"
    RETIRED = "Retired"


class DataClassification(str, Enum):
    PUBLIC = "Public"
    INTERNAL = "Internal"
    CONFIDENTIAL = "Confidential"
    RESTRICTED = "Restricted"


class VendorDependency(str, Enum):
    INTERNAL = "Internal"
    EXTERNAL_VENDOR = "External Vendor"


class RiskCategory(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Severity(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class FindingStatus(str, Enum):
    OPEN = "OPEN"
    IN_REMEDIATION = "IN_REMEDIATION"
    CLOSED = "CLOSED"


class GuardrailStage(str, Enum):
    INPUT = "INPUT"
    PROCESSING = "PROCESSING"
    OUTPUT = "OUTPUT"


class GuardrailAction(str, Enum):
    ALLOW = "ALLOW"
    MASK = "MASK"
    WARNING = "WARNING"
    BLOCK = "BLOCK"


class GuidanceType(str, Enum):
    BINDING = "BINDING"
    EMERGING = "EMERGING"


class AssetStatus(str, Enum):
    NOT_REGISTERED = "NOT_REGISTERED"
    REGISTERED = "REGISTERED"


class ReportType(str, Enum):
    JSON = "JSON"
    PDF = "PDF"
