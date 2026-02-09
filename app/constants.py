import os
from temporalio.common import SearchAttributeKey

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://temporal_user:temporal_pass@localhost:5432/temporal_ops",
)


# Temporal
TEMPORAL_HOST = os.getenv("TEMPORAL_HOST", "localhost:7233")
TEMPORAL_NAMESPACE = os.getenv("TEMPORAL_NAMESPACE", "default")
TEMPORAL_TASK_QUEUE = os.getenv("TEMPORAL_TASK_QUEUE", "long-running-ops")

# Defined in scripts/init-temporal.sh
OPERATION_UUID_ATTR_NAME = "OperationUUID"
OPERATION_UUID_SEARCH_ATTR = SearchAttributeKey.for_keyword(OPERATION_UUID_ATTR_NAME)
