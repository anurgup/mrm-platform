from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, utcnow


class LLMConfiguration(Base):
    __tablename__ = "llm_configurations"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str]
    model: Mapped[str]
    temperature: Mapped[float] = mapped_column(default=0.0)
    max_tokens: Mapped[int] = mapped_column(default=1024)
    # This column stores a credential REFERENCE only — the NAME of an env var
    # (e.g. "OPENAI_API_KEY"), never a secret value. Never store an actual
    # API key/token in this table.
    api_credential_ref: Mapped[str]
    is_active: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
