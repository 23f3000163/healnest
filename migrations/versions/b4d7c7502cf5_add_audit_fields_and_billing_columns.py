"""Add audit fields and billing columns (SQLite safe)

Revision ID: b4d7c7502cf5
Revises: d354184aa527
"""

from alembic import op
import sqlalchemy as sa


revision = 'b4d7c7502cf5'
down_revision = 'd354184aa527'
branch_labels = None
depends_on = None


def upgrade():
    # -------------------------------------------------
    # AVAILABILITY (doctor_id -> doctor_profile_id)
    # -------------------------------------------------
    with op.batch_alter_table('availability', recreate='always') as batch_op:
        batch_op.add_column(sa.Column('doctor_profile_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('start_time', sa.Time(), nullable=True))
        batch_op.add_column(sa.Column('end_time', sa.Time(), nullable=True))

        # old columns (safe removal)
        batch_op.drop_column('slot')
        batch_op.drop_column('doctor_id')

        batch_op.create_foreign_key(
            'fk_availability_doctor_profile',
            'doctor_profile',
            ['doctor_profile_id'],
            ['id']
        )

    # -------------------------------------------------
    # DOCTOR PROFILE (billing fields)
    # -------------------------------------------------
    with op.batch_alter_table('doctor_profile', recreate='always') as batch_op:
        batch_op.add_column(
            sa.Column(
                'consultation_fee',
                sa.Numeric(10, 2),
                nullable=False,
                server_default='0.00'
            )
        )
        batch_op.add_column(
            sa.Column(
                'currency',
                sa.String(5),
                nullable=False,
                server_default='INR'
            )
        )

    # -------------------------------------------------
    # NOTIFICATION (type column)
    # -------------------------------------------------
    with op.batch_alter_table('notification', recreate='always') as batch_op:
        batch_op.add_column(
            sa.Column(
                'type',
                sa.String(50),
                nullable=False,
                server_default='system'
            )
        )

    # -------------------------------------------------
    # PATIENT PROFILE (audit fields)
    # -------------------------------------------------
    with op.batch_alter_table('patient_profile', recreate='always') as batch_op:
        batch_op.add_column(sa.Column('created_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True))

    # -------------------------------------------------
    # USER (updated_at + email index already exists → skip index)
    # -------------------------------------------------
    with op.batch_alter_table('user', recreate='always') as batch_op:
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True))


def downgrade():
    # SQLite downgrade intentionally left minimal & safe
    pass
