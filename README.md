# Temporal Long-Running Operations POC

This POC demonstrates a pattern for tracking Temporal workflow execution status in a PostgreSQL database. The database serves as the source of truth for operation status, eliminating the need to query Temporal APIs during normal operation.

## Architecture

- PostgreSQL: Stores operation records and status
- Temporal: Executes workflows and maintains workflow state
- FastAPI: Provides REST API for operation management
- SQLAlchemy: ORM for database access and schema migrations

## Implementation Overview

### Status Tracking Mechanism

Operations are stored in PostgreSQL with the following status lifecycle:
- **ACCEPTED**: Operation created, workflow not yet started
- **RUNNING**: Workflow execution in progress
- **COMPLETED**: Workflow execution finished successfully
- **FAILED**: Workflow execution failed or was terminated

### Database Update Pattern

Workflow status updates are implemented using a decorator pattern (`@track_operation_status`) that wraps workflow execution. The decorator invokes the `update_operation_status` activity at specific points:

1. Before workflow execution begins: ACCEPTED -> RUNNING
2. After successful completion: RUNNING -> COMPLETED
3. On workflow failure: RUNNING -> FAILED

The `update_operation_status` activity performs direct database writes via SQLAlchemy. API endpoints query PostgreSQL directly for operation status without calling Temporal APIs.

### Reconciliation Workflow

A scheduled reconciliation workflow is executed every minute to address the limitation that workflows cannot handle termination signals. When a workflow is terminated externally (e.g. via Temporal UI/API or when the ID reuse policy `TERMINATE_IF_RUNNING` is used), the workflow code does not execute cleanup logic, leaving the database status as RUNNING indefinitely.

The reconciliation process:

1. Queries the database for all operations in RUNNING status
2. Lists all workflows with `ExecutionStatus = 'Running'` from Temporal
3. Identifies operations where the database shows RUNNING but Temporal shows the workflow is no longer running
4. Updates the database status to COMPLETED or FAILED based on the actual Temporal workflow status

### Custom Search Attribute Usage

Operations are indexed in Temporal using a custom search attribute `OperationUUID` of type Keyword. This attribute stores the operation's UUID and enables efficient querying of workflows by operation identifier.

The custom search attribute is used instead of workflow run IDs because, as documented in the Temporal documentation (https://docs.temporal.io/workflow-execution/workflowid-runid#run-id), run IDs are implementation details that may change between workflow retries and are not suitable to be used for any logical choices. Furthermore, the db table is completely decoupled from the Temporal workflow in this way.

