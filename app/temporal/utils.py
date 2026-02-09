import functools
from datetime import timedelta
from typing import Any, Callable

from temporalio import workflow

from app.constants import OPERATION_UUID_ATTR_NAME
from app.enums import OperationStatus

with workflow.unsafe.imports_passed_through():
    from app.temporal.activities import (
        UpdateStatusInput,
        update_operation_status,
    )


def track_operation_status(func: Callable) -> Callable:
    """
    Decorator for workflow run methods that automatically tracks operation status in the database.

    This decorator:
    1. Updates status to RUNNING before executing the workflow logic
    2. Updates status to COMPLETED with results on success
    3. Updates status to FAILED with error message on failure
    """

    @functools.wraps(func)
    async def wrapper(self, input: Any) -> Any:
        info = workflow.info()
        uuid = info.search_attributes.get(OPERATION_UUID_ATTR_NAME)
        if not uuid:
            raise RuntimeError(
                f"Status tracking has been enabled for workflow {info.workflow_type}"
                f" but the Search Attribute {OPERATION_UUID_ATTR_NAME} has not been set."
            )

        # the search attribute is always a list
        operation_uuid = str(uuid[0])

        try:
            workflow.logger.info(f"Starting workflow for operation {operation_uuid}")
            await workflow.execute_activity(
                update_operation_status,
                UpdateStatusInput(
                    operation_uuid=operation_uuid, status=OperationStatus.RUNNING
                ),
                start_to_close_timeout=timedelta(seconds=30),
            )

            result = await func(self, input)

            workflow.logger.info(f"Completed workflow for operation {operation_uuid}")
            await workflow.execute_activity(
                update_operation_status,
                UpdateStatusInput(
                    operation_uuid=operation_uuid,
                    status=OperationStatus.COMPLETED,
                    result=result,
                ),
                start_to_close_timeout=timedelta(seconds=30),
            )

            return result

        except Exception as e:
            workflow.logger.error(
                f"Workflow failed for operation {operation_uuid}: {e}"
            )

            error_message = str(e)
            await workflow.execute_activity(
                update_operation_status,
                UpdateStatusInput(
                    operation_uuid=operation_uuid,
                    status=OperationStatus.FAILED,
                    error=error_message,
                ),
                start_to_close_timeout=timedelta(seconds=30),
            )

            # Re-raise to let the workflow handle it
            raise

    return wrapper
