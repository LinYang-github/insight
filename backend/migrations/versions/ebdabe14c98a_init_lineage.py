"""Add lineage fields

Revision ID: ebdabe14c98a
Revises: 
Create Date: 2026-01-10

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'ebdabe14c98a'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Manually adding columns to existing table
    with op.batch_alter_table('dataset', schema=None) as batch_op:
        batch_op.add_column(sa.Column('parent_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('action_type', sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column('action_log', sa.Text(), nullable=True))
        batch_op.create_foreign_key('fk_dataset_parent', 'dataset', ['parent_id'], ['id'])

def downgrade():
    with op.batch_alter_table('dataset', schema=None) as batch_op:
        batch_op.drop_constraint('fk_dataset_parent', type_='foreignkey')
        batch_op.drop_column('action_log')
        batch_op.drop_column('action_type')
        batch_op.drop_column('parent_id')
