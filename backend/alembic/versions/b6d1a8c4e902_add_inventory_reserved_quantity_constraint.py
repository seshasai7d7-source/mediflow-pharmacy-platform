"""add inventory reserved quantity invariant

Revision ID: b6d1a8c4e902
Revises: 9206661b5cf4
Create Date: 2026-11-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b6d1a8c4e902"
down_revision: Union[str, Sequence[str], None] = "9206661b5cf4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    violating_rows = connection.execute(
        sa.text(
            "SELECT COUNT(*) FROM inventory "
            "WHERE reserved_quantity > available_quantity"
        )
    ).scalar_one()

    if violating_rows:
        raise RuntimeError(
            "Cannot add ck_inventory_reserved_lte_available: "
            f"{violating_rows} inventory row(s) violate reserved_quantity "
            "<= available_quantity."
        )

    op.create_check_constraint(
        "ck_inventory_reserved_lte_available",
        "inventory",
        "reserved_quantity <= available_quantity",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_inventory_reserved_lte_available",
        "inventory",
        type_="check",
    )
