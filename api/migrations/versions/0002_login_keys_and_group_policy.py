"""Norma loginlarini bir ko'rinishga keltirish va `none` guruh darajasini yopish.

Revision ID: 0002
Revises: 0001
"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    none_groups = conn.execute(
        sa.text("select count(*) from printer_groups where policy = 'none'")
    ).scalar()
    if none_groups:
        raise RuntimeError(
            f"{none_groups} ta 'Chiqarmaydi' guruhi bor: a'zolarini bloklab, guruhni o'chiring"
        )
    op.create_check_constraint(
        "ck_printer_groups_policy", "printer_groups", "policy in ('all', 'allowed')"
    )

    # Xuddi shu davrga normal ko'rinishdagi qator bo'lsa, u tegmaydi.
    op.execute(
        r"""
        update employee_quotas q
        set login = lower(regexp_replace(q.login, '^.*\\', ''))
        where q.login <> lower(regexp_replace(q.login, '^.*\\', ''))
          and not exists (
            select 1 from employee_quotas k
            where k.login = lower(regexp_replace(q.login, '^.*\\', ''))
              and k.period_type = q.period_type
              and k.year = q.year
              and k.period_no = q.period_no
          )
        """
    )


def downgrade() -> None:
    op.drop_constraint("ck_printer_groups_policy", "printer_groups", type_="check")
