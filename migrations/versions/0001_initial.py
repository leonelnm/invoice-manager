"""initial schema"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("users", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("username", sa.String(100), nullable=False, unique=True), sa.Column("password_hash", sa.String(255), nullable=False), sa.Column("display_name", sa.String(150), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False), sa.Column("is_admin", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()))
    op.create_table("source_systems", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("code", sa.String(50), nullable=False, unique=True), sa.Column("name", sa.String(100), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False))
    op.create_table("invoice_sequences", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("series", sa.String(30), nullable=False), sa.Column("fiscal_year", sa.Integer()), sa.Column("last_number", sa.Integer(), nullable=False), sa.UniqueConstraint("series", "fiscal_year", name="uq_sequence"))
    op.create_table("invoices", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("sequence_id", sa.Integer(), sa.ForeignKey("invoice_sequences.id"), nullable=False), sa.Column("sequence_number", sa.Integer(), nullable=False), sa.Column("invoice_number", sa.String(80), nullable=False, unique=True), sa.Column("source_system_id", sa.Integer(), sa.ForeignKey("source_systems.id"), nullable=False), sa.Column("report_id", sa.String(150), nullable=False), sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False), sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False), sa.UniqueConstraint("sequence_id", "sequence_number", name="uq_sequence_number"), sa.UniqueConstraint("source_system_id", "report_id", name="uq_source_report"))
    op.create_index("ix_invoice_report", "invoices", ["report_id"])
    op.create_index("ix_invoice_source_date", "invoices", ["source_system_id", "created_at"])
    op.create_table("idempotency_requests", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("idempotency_key", sa.String(100), nullable=False, unique=True), sa.Column("request_fingerprint", sa.String(64), nullable=False), sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=False), sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False), sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False))


def downgrade() -> None:
    op.drop_table("idempotency_requests")
    op.drop_table("invoices")
    op.drop_table("invoice_sequences")
    op.drop_table("source_systems")
    op.drop_table("users")
