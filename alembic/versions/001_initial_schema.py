"""Initial schema with operations table

Revision ID: 001
Revises: 
Create Date: 2026-02-05 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'operations',
        sa.Column('uuid', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('system_id', sa.String(6), nullable=False),
        sa.Column('op_type', sa.String(100), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('accepted_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('parameters', postgresql.JSON(), nullable=False),
        sa.Column('result', postgresql.JSON(), nullable=True),
    )
    
    op.create_index('ix_operations_status', 'operations', ['status'])


def downgrade() -> None:
    op.drop_index('ix_operations_status')
    op.drop_table('operations')
