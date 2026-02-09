import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

from temporalio import activity
from temporalio.client import WorkflowExecutionStatus

from app.constants import OPERATION_UUID_ATTR_NAME
from app.database import get_db
from app.enums import OperationStatus
from app.models import Operation
from app.temporal.client import get_temporal_client


@dataclass
class UpdateStatusInput:
    operation_uuid: str
    status: OperationStatus
    result: Optional[Dict] = None
    error: Optional[str] = None


@dataclass
class SimulateWorkInput:
    duration: int
    task_name: str


@activity.defn(name="update_operation_status")
async def update_operation_status(input: UpdateStatusInput) -> None:
    activity.logger.info(
        f"Updating operation {input.operation_uuid} to status {input.status}"
    )

    with get_db() as db:
        operation = (
            db.query(Operation).filter(Operation.uuid == input.operation_uuid).first()
        )

        if not operation:
            raise ValueError(f"Operation {input.operation_uuid} not found")

        operation.status = OperationStatus(input.status)

        if input.status == OperationStatus.RUNNING:
            operation.started_at = datetime.utcnow()
        elif input.status in [OperationStatus.COMPLETED, OperationStatus.FAILED]:
            operation.finished_at = datetime.utcnow()

        if input.result:
            operation.result = input.result
        elif input.error:
            operation.result = {"error": input.error}

        db.commit()

    activity.logger.info(f"Successfully updated operation {input.operation_uuid}")


@activity.defn(name="simulate_work")
async def simulate_work(input: SimulateWorkInput) -> None:
    activity.logger.info(
        f"Starting {input.task_name}, will sleep {input.duration} seconds"
    )
    await asyncio.sleep(input.duration)
    activity.logger.info(f"Completed {input.task_name}")


@dataclass
class GetRunningOperationsOutput:
    operations_uuids: set[str]


@activity.defn(name="get_running_operations")
async def get_running_operations() -> GetRunningOperationsOutput:
    with get_db() as db:
        operations = (
            db.query(Operation)
            .filter(Operation.status == OperationStatus.RUNNING)
            .all()
        )

        result = {str(op.uuid) for op in operations}

    activity.logger.info(f"Found {len(result)} RUNNING operations")
    return GetRunningOperationsOutput(operations_uuids=result)


@dataclass
class ReconcileOperationInput:
    operations_uuids: set[str]


@dataclass
class ReconcileOperationOutput:
    reconciled: int


@activity.defn(name="reconcile_operation_status")
async def reconcile_operation_status(
    input: ReconcileOperationInput,
) -> ReconcileOperationOutput:
    if not input.operations_uuids:
        activity.logger.info("No operations to reconcile")
        return ReconcileOperationOutput(reconciled=0)

    activity.logger.info(f"Reconciling {len(input.operations_uuids)} operations")

    client = await get_temporal_client()

    reconciled_count = 0

    running_workflow_uuids = set()
    async for workflow in client.list_workflows("ExecutionStatus = 'Running'"):
        uuid = workflow.search_attributes.get(OPERATION_UUID_ATTR_NAME)
        if not uuid:
            continue

        uuid = str(uuid[0])
        running_workflow_uuids.add(uuid)

    activity.logger.info(f"Found {len(running_workflow_uuids)} workflows still running")

    # Query only the workflows that are NOT running
    workflows_to_check = input.operations_uuids - running_workflow_uuids
    activity.logger.info(f"Querying {len(workflows_to_check)} non-running workflows")

    for op_uuid in workflows_to_check:
        try:
            workflow_status = None
            async for workflow in client.list_workflows(
                f"{OPERATION_UUID_ATTR_NAME} = '{op_uuid}'", page_size=1
            ):
                workflow_status = workflow.status

            if workflow_status is None:
                activity.logger.warning(
                    f"Operation with UUID {op_uuid} not found in workflows."
                )
                continue

            # Map Temporal status to OperationStatus
            new_status = None
            if workflow_status == WorkflowExecutionStatus.COMPLETED:
                new_status = OperationStatus.COMPLETED
            elif workflow_status in [
                WorkflowExecutionStatus.FAILED,
                WorkflowExecutionStatus.CANCELED,
                WorkflowExecutionStatus.TERMINATED,
                WorkflowExecutionStatus.TIMED_OUT,
            ]:
                new_status = OperationStatus.FAILED

            if new_status:
                with get_db() as db:
                    operation = (
                        db.query(Operation).filter(Operation.uuid == op_uuid).first()
                    )

                    if not operation:
                        activity.logger.warning(f"Operation {op_uuid} not found")
                        continue

                    old_status = operation.status
                    operation.status = new_status

                    if new_status in [
                        OperationStatus.COMPLETED,
                        OperationStatus.FAILED,
                    ]:
                        operation.finished_at = datetime.utcnow()

                    db.commit()
                    reconciled_count += 1

                    activity.logger.info(
                        f"Reconciled operation {op_uuid}: {old_status} -> {new_status}"
                    )

        except Exception as e:
            activity.logger.error(f"Error reconciling operation {op_uuid}: {e}")
            continue

    return ReconcileOperationOutput(reconciled=reconciled_count)
