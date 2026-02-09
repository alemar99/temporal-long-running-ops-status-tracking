import uuid as uuid_lib
from datetime import datetime
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from temporalio.common import (
    SearchAttributePair,
    TypedSearchAttributes,
)

from app.constants import OPERATION_UUID_SEARCH_ATTR, TEMPORAL_TASK_QUEUE
from app.database import SessionLocal
from app.enums import OperationStatus, OperationType
from app.models import Operation
from app.temporal.client import get_temporal_client
from app.temporal.schedules import setup_schedules
from app.temporal.workflows.long_running_operation import (
    LongRunningOperationWorkflow,
    WorkflowInput,
)

app = FastAPI(
    title="Long-Running Operations API",
    description="API for managing and tracking long-running operations with Temporal",
    version="1.0.0",
)


class MachineOperationParams(BaseModel):
    timeout: int


class OperationResponse(BaseModel):
    uuid: str
    workflow_run_id: Optional[str] = None
    system_id: str
    op_type: str
    status: str
    accepted_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    parameters: dict
    result: Optional[dict] = None


class CreatedOperationResponse(BaseModel):
    uuid: str


@app.on_event("startup")
async def startup_event():
    try:
        client = await get_temporal_client()
        await setup_schedules(client)

    except Exception as e:
        print(f"Could not connect to Temporal: {e}")


def get_db():
    """Duplicate of `get_db` in app/database.py because FastAPI doesn't like `@contextmanager`
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

@app.get("/")
async def root():
    return { "status": "healthy" }


@app.post(
    "/machines/{machine_id}", response_model=CreatedOperationResponse, status_code=201
)
async def do_operation_on_machine(
    machine_id: str,
    parameters: MachineOperationParams,
    op: OperationType = Query(..., description="Type of operation to perform"),
    db: Session = Depends(get_db),
) -> CreatedOperationResponse:
    """
    Start a new long-running operation on a specific machine.

    Creates a new operation record in the database and starts a Temporal workflow.
    Returns the operation UUID for tracking.

    Args:
        machine_id: The ID of the machine to perform the operation on
        op: The type of operation to perform (query parameter)
        parameters: The operation details including timeout
    """
    op_uuid = uuid_lib.uuid4()

    db_operation = Operation(
        uuid=op_uuid,
        system_id=machine_id,
        op_type=op,
        status=OperationStatus.ACCEPTED,
        accepted_at=datetime.utcnow(),
        parameters={"timeout": parameters.timeout},
    )

    db.add(db_operation)

    try:
        client = await get_temporal_client()

        workflow_id = f"{machine_id}-{op}-{op_uuid}"
        workflow_input = WorkflowInput(timeout=parameters.timeout)

        await client.start_workflow(
            LongRunningOperationWorkflow.run,
            workflow_input,
            id=workflow_id,
            task_queue=TEMPORAL_TASK_QUEUE,
            search_attributes=TypedSearchAttributes(
                [
                    SearchAttributePair(OPERATION_UUID_SEARCH_ATTR, str(op_uuid)),
                ]
            ),
        )

    except Exception as e:
        db.delete(db_operation)
        print(f"Error starting workflow: {e}")

    return CreatedOperationResponse(uuid=str(db_operation.uuid))


@app.get("/operations/{operation_uuid}", response_model=OperationResponse)
async def get_operation(
    operation_uuid: str, db: Session = Depends(get_db)
) -> OperationResponse:
    try:
        op_uuid = uuid_lib.UUID(operation_uuid)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    operation = db.query(Operation).filter(Operation.uuid == op_uuid).first()

    if not operation:
        raise HTTPException(status_code=404, detail="Operation not found")

    return OperationResponse(**operation.to_dict())


@app.get("/operations", response_model=List[OperationResponse])
async def list_operations(
    status: Optional[OperationStatus] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> List[OperationResponse]:
    query = db.query(Operation)

    if status:
        query = query.filter(Operation.status == status)

    operations = query.order_by(Operation.accepted_at.desc()).limit(limit).all()

    return [OperationResponse(**op.to_dict()) for op in operations]
