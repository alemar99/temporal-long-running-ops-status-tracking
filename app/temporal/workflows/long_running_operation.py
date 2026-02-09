"""Long-running operation workflow."""

from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow

from app.temporal.utils import track_operation_status

with workflow.unsafe.imports_passed_through():
    from app.temporal.activities import (
        simulate_work,
        SimulateWorkInput,
    )


@dataclass
class WorkflowInput:
    timeout: int


@workflow.defn(name="LongRunningOperationWorkflow")
class LongRunningOperationWorkflow:
    @track_operation_status
    @workflow.run
    async def run(self, input: WorkflowInput) -> None:
        duration = input.timeout

        await workflow.execute_activity(
            simulate_work,
            SimulateWorkInput(duration=duration, task_name="task1"),
            start_to_close_timeout=timedelta(seconds=duration + 10),
        )
