"""align order status constraint

Revision ID: 8b5dd306a320
Revises: 8a9957a4f338
Create Date: 2026-11-06 21:25:13.433783

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8b5dd306a320'
down_revision: Union[str, Sequence[str], None] = '8a9957a4f338'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_orders_status",
        "orders",
        type_="check",
    )

    op.create_check_constraint(
        "ck_orders_status",
        "orders",
        "status IN "
        "('pending_review', 'confirmed', 'preparing', "
        "'ready', 'dispatched', 'delivered', 'cancelled')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_orders_status",
        "orders",
        type_="check",
    )

    op.create_check_constraint(
        "ck_orders_status",
        "orders",
        "status IN "
        "('pending_review', 'approved', 'rejected', "
        "'confirmed', 'ready_for_pickup', 'dispatched', 'cancelled')",
    )