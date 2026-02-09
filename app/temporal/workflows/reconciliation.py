"""Reconciliation workflow for syncing operation status with Temporal."""

from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from app.temporal.activities import (
        get_running_operations,
        reconcile_operation_status,
        ReconcileOperationInput,
    )


@dataclass
class ReconciliationWorkflowOutput:
    total_checked: int
    reconciled: int


@workflow.defn(name="ReconciliationWorkflow")
class ReconciliationWorkflow:
    """
    Workflow for reconciling operation status between database and Temporal.

    This workflow:
    1. Fetches all operations with status "RUNNING" from the database
    2. Queries Temporal for the actual status of each workflow
    3. Updates the database if there's a mismatch
    """

    @workflow.run
    async def run(self) -> ReconciliationWorkflowOutput:
        workflow.logger.info("Starting reconciliation workflow")

        # Step 1: Get all operations with RUNNING status
        running_ops = await workflow.execute_activity(
            get_running_operations,
            start_to_close_timeout=timedelta(seconds=30),
        )

        workflow.logger.info(
            f"Found {len(running_ops.operations_uuids)} operations in RUNNING state"
        )

        if not running_ops.operations_uuids:
            return ReconciliationWorkflowOutput(
                total_checked=0,
                reconciled=0,
            )

        # Step 2: Reconcile all operations in a single activity call
        result = await workflow.execute_activity(
            reconcile_operation_status,
            ReconcileOperationInput(operations_uuids=running_ops.operations_uuids),
            start_to_close_timeout=timedelta(seconds=60),
        )

        workflow.logger.info(f"Reconciliation complete: {result.reconciled} updated")
        return ReconciliationWorkflowOutput(
            total_checked=len(running_ops.operations_uuids),
            reconciled=result.reconciled,
        )
