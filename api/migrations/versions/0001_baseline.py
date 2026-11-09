"""Boshlang'ich sxema: 2026-11-09 dagi ishlab turgan baza bilan bir xil.

Mavjud bazada bu migratsiya bajarilmaydi, `alembic stamp 0001` bilan belgilanadi.
Yangi bo'sh baza esa shu faylning o'zidan quriladi.

Revision ID: 0001
Revises:
"""

from alembic import op
import sqlalchemy as sa


revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('agent_quota_state',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('computer', sa.String(length=255), nullable=False),
    sa.Column('login', sa.String(length=255), nullable=False),
    sa.Column('raw_user', sa.String(length=255), nullable=True),
    sa.Column('period_key', sa.String(length=32), nullable=False),
    sa.Column('pages_used_here', sa.BigInteger(), nullable=False),
    sa.Column('pages_used_reported', sa.BigInteger(), nullable=False),
    sa.Column('applied_limit', sa.Integer(), nullable=True),
    sa.Column('served_limit', sa.Integer(), nullable=True),
    sa.Column('served_used', sa.BigInteger(), nullable=True),
    sa.Column('reported_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('computer', 'login', 'period_key', name='uq_agent_quota_state_computer_login_period')
    )
    op.create_index('ix_agent_quota_state_login', 'agent_quota_state', ['login'], unique=False)
    op.create_index('ix_agent_quota_state_period_key', 'agent_quota_state', ['period_key'], unique=False)
    op.create_index('ix_agent_quota_state_reported_at', 'agent_quota_state', ['reported_at'], unique=False)
    op.create_table('agent_status',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('computer', sa.String(length=255), nullable=False),
    sa.Column('username', sa.String(length=255), nullable=True),
    sa.Column('version', sa.String(length=50), nullable=True),
    sa.Column('working', sa.Boolean(), nullable=False),
    sa.Column('detail', sa.Text(), nullable=True),
    sa.Column('boot_time_utc', sa.DateTime(timezone=True), nullable=True),
    sa.Column('uptime_seconds', sa.BigInteger(), nullable=True),
    sa.Column('agent_uptime_seconds', sa.BigInteger(), nullable=True),
    sa.Column('reported_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('computer')
    )
    op.create_index('ix_agent_status_reported_at', 'agent_status', ['reported_at'], unique=False)
    op.create_index('ix_agent_status_working', 'agent_status', ['working'], unique=False)
    op.create_table('employee_quotas',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('login', sa.String(length=255), nullable=False),
    sa.Column('period_type', sa.String(length=10), nullable=False),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('period_no', sa.Integer(), nullable=False),
    sa.Column('allocated_pages', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('login', 'period_type', 'year', 'period_no', name='uq_employee_quotas_period')
    )
    op.create_index('ix_employee_quotas_login', 'employee_quotas', ['login'], unique=False)
    op.create_index('ix_employee_quotas_period', 'employee_quotas', ['period_type', 'year', 'period_no'], unique=False)
    op.create_table('employees',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('login', sa.String(length=255), nullable=False),
    sa.Column('full_name', sa.String(length=255), nullable=True),
    sa.Column('department', sa.String(length=255), nullable=True),
    sa.Column('position', sa.String(length=255), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('synced_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('login')
    )
    op.create_index('ix_employees_department', 'employees', ['department'], unique=False)
    op.create_index('ix_employees_is_active', 'employees', ['is_active'], unique=False)
    op.create_table('print_jobs',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('computer', sa.String(length=255), nullable=False),
    sa.Column('user_name', sa.String(length=255), nullable=False),
    sa.Column('document', sa.Text(), nullable=False),
    sa.Column('printer', sa.String(length=255), nullable=False),
    sa.Column('printer_ip', sa.String(length=255), nullable=True),
    sa.Column('pages', sa.Integer(), nullable=False),
    sa.Column('document_pages', sa.Integer(), server_default='0', nullable=False),
    sa.Column('duplex', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('printed_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('success', sa.Boolean(), nullable=False),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('printer_mac', sa.String(length=64), nullable=True),
    sa.Column('job_id', sa.String(length=64), nullable=True),
    sa.Column('dedup_key', sa.String(length=64), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('dedup_key')
    )
    op.create_index('ix_print_jobs_computer_printed_at', 'print_jobs', ['computer', 'printed_at'], unique=False)
    op.create_index('ix_print_jobs_printed_at', 'print_jobs', ['printed_at'], unique=False)
    op.create_index('ix_print_jobs_printer', 'print_jobs', ['printer'], unique=False)
    op.create_index('ix_print_jobs_user_name', 'print_jobs', ['user_name'], unique=False)
    op.create_table('print_user_overrides',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('login', sa.String(length=255), nullable=False),
    sa.Column('blocked', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('blocked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('blocked_by', sa.String(length=255), nullable=True),
    sa.Column('blocked_reason', sa.Text(), nullable=True),
    sa.Column('charge_to_login', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('login')
    )
    op.create_index('ix_print_user_overrides_blocked', 'print_user_overrides', ['blocked'], unique=False)
    op.create_index('ix_print_user_overrides_charge_to', 'print_user_overrides', ['charge_to_login'], unique=False)
    op.create_table('printer_access_settings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('restrict_default', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('printer_aliases',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('device_id', sa.BigInteger(), nullable=False),
    sa.Column('kind', sa.String(length=8), nullable=False),
    sa.Column('value', sa.String(length=255), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('kind', 'value', name='uq_printer_aliases_kind_value')
    )
    op.create_index(op.f('ix_printer_aliases_device_id'), 'printer_aliases', ['device_id'], unique=False)
    op.create_table('printer_devices',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=True),
    sa.Column('last_driver_name', sa.String(length=255), nullable=True),
    sa.Column('last_ip', sa.String(length=64), nullable=True),
    sa.Column('first_seen', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_printer_devices_last_seen', 'printer_devices', ['last_seen'], unique=False)
    op.create_table('printer_group_members',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('group_id', sa.BigInteger(), nullable=False),
    sa.Column('login', sa.String(length=255), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('login', name='uq_printer_group_members_login')
    )
    op.create_index(op.f('ix_printer_group_members_group_id'), 'printer_group_members', ['group_id'], unique=False)
    op.create_table('printer_group_printers',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('group_id', sa.BigInteger(), nullable=False),
    sa.Column('device_id', sa.BigInteger(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('group_id', 'device_id', name='uq_printer_group_printers')
    )
    op.create_index(op.f('ix_printer_group_printers_device_id'), 'printer_group_printers', ['device_id'], unique=False)
    op.create_index(op.f('ix_printer_group_printers_group_id'), 'printer_group_printers', ['group_id'], unique=False)
    op.create_table('printer_groups',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('policy', sa.String(length=16), server_default='all', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name', name='uq_printer_groups_name')
    )
    op.create_table('printers',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('mac', sa.String(length=64), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=True),
    sa.Column('last_ip', sa.String(length=64), nullable=True),
    sa.Column('last_driver_name', sa.String(length=255), nullable=True),
    sa.Column('first_seen', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('mac')
    )
    op.create_table('public_printers',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('device_id', sa.BigInteger(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('device_id')
    )


def downgrade() -> None:
    op.drop_table('public_printers')
    op.drop_table('printers')
    op.drop_table('printer_groups')
    op.drop_index(op.f('ix_printer_group_printers_group_id'), table_name='printer_group_printers')
    op.drop_index(op.f('ix_printer_group_printers_device_id'), table_name='printer_group_printers')
    op.drop_table('printer_group_printers')
    op.drop_index(op.f('ix_printer_group_members_group_id'), table_name='printer_group_members')
    op.drop_table('printer_group_members')
    op.drop_index('ix_printer_devices_last_seen', table_name='printer_devices')
    op.drop_table('printer_devices')
    op.drop_index(op.f('ix_printer_aliases_device_id'), table_name='printer_aliases')
    op.drop_table('printer_aliases')
    op.drop_table('printer_access_settings')
    op.drop_index('ix_print_user_overrides_charge_to', table_name='print_user_overrides')
    op.drop_index('ix_print_user_overrides_blocked', table_name='print_user_overrides')
    op.drop_table('print_user_overrides')
    op.drop_index('ix_print_jobs_user_name', table_name='print_jobs')
    op.drop_index('ix_print_jobs_printer', table_name='print_jobs')
    op.drop_index('ix_print_jobs_printed_at', table_name='print_jobs')
    op.drop_index('ix_print_jobs_computer_printed_at', table_name='print_jobs')
    op.drop_table('print_jobs')
    op.drop_index('ix_employees_is_active', table_name='employees')
    op.drop_index('ix_employees_department', table_name='employees')
    op.drop_table('employees')
    op.drop_index('ix_employee_quotas_period', table_name='employee_quotas')
    op.drop_index('ix_employee_quotas_login', table_name='employee_quotas')
    op.drop_table('employee_quotas')
    op.drop_index('ix_agent_status_working', table_name='agent_status')
    op.drop_index('ix_agent_status_reported_at', table_name='agent_status')
    op.drop_table('agent_status')
    op.drop_index('ix_agent_quota_state_reported_at', table_name='agent_quota_state')
    op.drop_index('ix_agent_quota_state_period_key', table_name='agent_quota_state')
    op.drop_index('ix_agent_quota_state_login', table_name='agent_quota_state')
    op.drop_table('agent_quota_state')
