from datetime import timedelta
from typing import Final

from temporalio.client import (
    Client,
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleIntervalSpec,
    ScheduleSpec,
    ScheduleUpdate,
    ScheduleUpdateInput,
)

from app.constants import TEMPORAL_TASK_QUEUE
from app.temporal.workflows.reconciliation import (
    ReconciliationWorkflow,
)


# Schedule ID constants
RECONCILIATION_SCHEDULE_ID = "reconciliation-schedule"


# Define all schedules
SCHEDULES: Final[dict[str, Schedule]] = {
    RECONCILIATION_SCHEDULE_ID: Schedule(
        action=ScheduleActionStartWorkflow(
            ReconciliationWorkflow.run,
            id=f"reconciliation-{RECONCILIATION_SCHEDULE_ID}",
            task_queue=TEMPORAL_TASK_QUEUE,
        ),
        spec=ScheduleSpec(intervals=[ScheduleIntervalSpec(every=timedelta(minutes=1))]),
    )
}


async def update_schedule(input: ScheduleUpdateInput) -> ScheduleUpdate:
    """
    Update callback for Temporal schedule.

    This function is called by Temporal when updating a schedule.
    It ensures the schedule matches the latest definition.

    Args:
        input: The current schedule description from Temporal

    Returns:
        ScheduleUpdate with the new schedule definition
    """
    schedule_description = input.description
    schedule_definition = SCHEDULES.get(schedule_description.id)
    assert schedule_definition is not None, (
        "Tried to update a not defined Temporal schedule."
    )

    # Update the schedule with the last definition
    schedule_description.schedule = schedule_definition

    return ScheduleUpdate(schedule=input.description.schedule)


async def setup_schedules(client: Client) -> None:
    """
    Setup Temporal schedules.

    The schedules that must be registered in Temporal are defined in the `SCHEDULES`
    variable. This function will:
        - delete all the schedules that are registered but not defined (i.e. the
        ones we have defined in the past, but we later removed)
        - register all the new schedules (never registered)
        - update the already registered schedules

    Args:
        client: Connected Temporal client
    """
    expected_schedules = set(SCHEDULES.keys())
    registered_schedules: set[str] = set()

    async for schedule in await client.list_schedules():
        registered_schedules.add(schedule.id)

    schedules_to_delete = registered_schedules - expected_schedules
    for schedule in schedules_to_delete:
        handle = client.get_schedule_handle(schedule)
        await handle.delete()
        print(f"Deleted schedule: {schedule}")

    schedules_to_add = expected_schedules - registered_schedules
    for schedule in schedules_to_add:
        await client.create_schedule(schedule, SCHEDULES[schedule])
        print(f"Created schedule: {schedule}")

    schedules_to_update = registered_schedules - schedules_to_delete
    for schedule in schedules_to_update:
        handle = client.get_schedule_handle(schedule)
        await handle.update(update_schedule)
        print(f"Updated schedule: {schedule}")
