import uuid
from datetime import datetime

from sqlalchemy import JSON, UUID, Column, DateTime, String
from sqlalchemy.orm import declarative_base

from app.enums import OperationStatus

Base = declarative_base()


class Operation(Base):
    """Model for tracking long-running operations."""

    __tablename__ = "operations"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    system_id = Column(String(6), nullable=False)
    op_type = Column(String(100), nullable=False)
    status = Column(
        String(20), nullable=False, default=OperationStatus.ACCEPTED, index=True
    )
    accepted_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    parameters = Column(JSON, nullable=False)
    result = Column(JSON, nullable=True)

    def to_dict(self) -> dict:
        """Convert operation to dictionary for API responses."""
        return {
            "uuid": str(self.uuid),
            "system_id": self.system_id,
            "op_type": self.op_type,
            "status": self.status,
            "accepted_at": self.accepted_at.isoformat() if self.accepted_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "parameters": self.parameters,
            "result": self.result,
        }
