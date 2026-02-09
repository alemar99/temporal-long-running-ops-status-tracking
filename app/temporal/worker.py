import asyncio
import logging
import signal
import sys

from temporalio.client import Client
from temporalio.worker import Worker

from app.constants import TEMPORAL_HOST, TEMPORAL_NAMESPACE, TEMPORAL_TASK_QUEUE
from app.temporal.activities import (
    get_running_operations,
    reconcile_operation_status,
    simulate_work,
    update_operation_status,
)
from app.temporal.workflows.long_running_operation import LongRunningOperationWorkflow
from app.temporal.workflows.reconciliation import ReconciliationWorkflow

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logging.getLogger("temporalio").setLevel(logging.INFO)


async def main():
    print(f"Connecting to Temporal at {TEMPORAL_HOST}")
    print(f"Namespace: {TEMPORAL_NAMESPACE}")
    print(f"Task Queue: {TEMPORAL_TASK_QUEUE}")

    client = await Client.connect(TEMPORAL_HOST, namespace=TEMPORAL_NAMESPACE)

    print("Connected to Temporal server")

    worker = Worker(
        client,
        task_queue=TEMPORAL_TASK_QUEUE,
        workflows=[LongRunningOperationWorkflow, ReconciliationWorkflow],
        activities=[
            update_operation_status,
            simulate_work,
            get_running_operations,
            reconcile_operation_status,
        ],
    )

    print(f"Worker RUNNING on task queue: {TEMPORAL_TASK_QUEUE}")

    await worker.run()


def handle_shutdown(signum, frame):
    print("\nShutdown signal received, stopping worker...")
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    asyncio.run(main())
