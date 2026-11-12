"""add performance composite indexes

Revision ID: a1b2c3d4e5f6
Revises: f9fbec9d6222
Create Date: 2026-11-12 20:38:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f9fbec9d6222'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Composite index for public job browsing and pagination
    op.create_index(
        'idx_jobs_status_created_at',
        'jobs',
        ['status', sa.text('created_at DESC')],
        unique=False,
        if_not_exists=True
    )
    # 2. Composite index for recruiter company job queries
    op.create_index(
        'idx_jobs_company_status',
        'jobs',
        ['company_id', 'status'],
        unique=False,
        if_not_exists=True
    )
    # 3. Composite index for recruiter application pipeline filtering
    op.create_index(
        'idx_applications_job_status',
        'applications',
        ['job_id', 'status'],
        unique=False,
        if_not_exists=True
    )
    # 4. Index for candidate ranking score ordering
    op.create_index(
        'idx_match_scores_overall',
        'application_match_scores',
        [sa.text('overall_score DESC')],
        unique=False,
        if_not_exists=True
    )


def downgrade() -> None:
    op.drop_index('idx_match_scores_overall', table_name='application_match_scores')
    op.drop_index('idx_applications_job_status', table_name='applications')
    op.drop_index('idx_jobs_company_status', table_name='jobs')
    op.drop_index('idx_jobs_status_created_at', table_name='jobs')

