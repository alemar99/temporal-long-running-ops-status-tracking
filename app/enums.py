import enum

class OperationType(enum.StrEnum):
    DEPLOY = "DEPLOY"
    COMMISSION = "COMMISSION"
    RELEASE = "RELEASE"


class OperationStatus(enum.StrEnum):
    ACCEPTED = "ACCEPTED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"

