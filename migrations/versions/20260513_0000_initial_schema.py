"""Initial schema — labor graph core entities.

Creates Person, Organization, Skill, Role, Project, Posting (raw + canonical),
CompensationRecord, HiringEvent, and RecruiterInteraction. Mirrors §0.1 of
the build plan.

Revision ID: 20260513_0000
Revises:
Create Date: 2026-05-13
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260513_0000"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    op.create_table(
        "person",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("primary_email", sa.String(320), nullable=True),
        sa.Column("primary_phone", sa.String(64), nullable=True),
        sa.Column("linkedin_url", sa.String(512), nullable=True),
        sa.Column("consent_for_storage", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_person_primary_email", "person", ["primary_email"],
        unique=True, postgresql_where=sa.text("primary_email IS NOT NULL"),
    )
    op.create_index(
        "ix_person_linkedin_url", "person", ["linkedin_url"],
        unique=True, postgresql_where=sa.text("linkedin_url IS NOT NULL"),
    )

    op.create_table(
        "organization",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("canonical_name", sa.String(255), nullable=False, unique=True),
        sa.Column("aliases", postgresql.ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("sector_tags", postgresql.ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("naics_code", sa.String(8), nullable=True),
        sa.Column("headcount_estimate", sa.Integer, nullable=True),
        sa.Column("union_status", sa.String(32), nullable=True),
        sa.Column("operating_regions", postgresql.ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("enr_rank", sa.Integer, nullable=True),
        sa.Column("is_recruiter_client", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("website", sa.String(512), nullable=True),
        sa.Column("careers_url", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_organization_naics_code", "organization", ["naics_code"])
    op.create_index("ix_organization_sector_tags", "organization", ["sector_tags"], postgresql_using="gin")
    op.create_index("ix_organization_aliases", "organization", ["aliases"], postgresql_using="gin")

    skill_category = postgresql.ENUM(
        "technical", "software", "certification", "equipment", "methodology", "safety",
        name="skill_category",
        create_type=False,
    )
    skill_category.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "skill",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("canonical_name", sa.String(255), nullable=False, unique=True),
        sa.Column("category", skill_category, nullable=False),
        sa.Column("description", sa.String(1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_skill_category", "skill", ["category"])

    op.create_table(
        "project",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("project_type", sa.String(64), nullable=False),
        sa.Column("owner_org_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("organization.id", ondelete="SET NULL"), nullable=True),
        sa.Column("epc_contractor_org_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("organization.id", ondelete="SET NULL"), nullable=True),
        sa.Column("region_code", sa.String(8), nullable=True),
        sa.Column("location_text", sa.String(255), nullable=True),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("capex_usd", sa.Numeric(18, 2), nullable=True),
        sa.Column("estimated_peak_headcount", sa.Integer, nullable=True),
        sa.Column("announced_on", sa.Date, nullable=True),
        sa.Column("construction_start_on", sa.Date, nullable=True),
        sa.Column("expected_completion_on", sa.Date, nullable=True),
        sa.Column("source", sa.String(128), nullable=True),
        sa.Column("source_url", sa.String(1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_project_region", "project", ["region_code"])
    op.create_index("ix_project_type", "project", ["project_type"])

    op.create_table(
        "role",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("person_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("person.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("organization.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("project.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title_raw", sa.String(255), nullable=False),
        sa.Column("occupation_code", sa.String(16), nullable=True),
        sa.Column("occupation_system", sa.String(16), nullable=True),
        sa.Column("industrial_overlay_code", sa.String(64), nullable=True),
        sa.Column("seniority", sa.String(32), nullable=True),
        sa.Column("skills", postgresql.ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("started_on", sa.Date, nullable=False),
        sa.Column("ended_on", sa.Date, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_role_person", "role", ["person_id"])
    op.create_index("ix_role_organization", "role", ["organization_id"])
    op.create_index("ix_role_occupation", "role", ["occupation_system", "occupation_code"])
    op.create_index("ix_role_skills", "role", ["skills"], postgresql_using="gin")

    op.create_table(
        "posting",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("organization.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("occupation_code", sa.String(16), nullable=True),
        sa.Column("occupation_system", sa.String(16), nullable=True),
        sa.Column("industrial_overlay_code", sa.String(64), nullable=True),
        sa.Column("seniority", sa.String(32), nullable=True),
        sa.Column("region_code", sa.String(8), nullable=True),
        sa.Column("location_text", sa.String(255), nullable=True),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("salary_low", sa.Numeric(12, 2), nullable=True),
        sa.Column("salary_high", sa.Numeric(12, 2), nullable=True),
        sa.Column("salary_currency", sa.String(3), nullable=True),
        sa.Column("salary_period", sa.String(16), nullable=True),
        sa.Column("skills", postgresql.ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("certifications", postgresql.ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("source_count", sa.Integer, nullable=False, server_default="1"),
        sa.Column("dedup_key", sa.String(128), nullable=False),
        sa.Column("confidence", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_posting_dedup_key", "posting", ["dedup_key"])
    op.create_index("ix_posting_active_lastseen", "posting", ["is_active", "last_seen_at"])
    op.create_index("ix_posting_occupation", "posting", ["occupation_system", "occupation_code"])
    op.create_index("ix_posting_region", "posting", ["region_code"])
    op.create_index("ix_posting_skills", "posting", ["skills"], postgresql_using="gin")

    op.create_table(
        "raw_posting",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(128), nullable=False),
        sa.Column("source_posting_id", sa.String(255), nullable=False),
        sa.Column("source_url", sa.String(1024), nullable=False),
        sa.Column("raw_title", sa.String(512), nullable=True),
        sa.Column("company_raw", sa.String(512), nullable=True),
        sa.Column("location_raw", sa.String(512), nullable=True),
        sa.Column("posted_date", sa.Date, nullable=True),
        sa.Column("salary_raw", sa.String(512), nullable=True),
        sa.Column("job_type", sa.String(64), nullable=True),
        sa.Column("description_text", sa.Text, nullable=True),
        sa.Column("html_hash", sa.String(64), nullable=False),
        sa.Column("s3_key", sa.String(512), nullable=True),
        sa.Column("extra", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("scraped_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("posting_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("posting.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("source", "source_posting_id", name="uq_raw_posting_source"),
    )
    op.create_index("ix_raw_posting_scraped_at", "raw_posting", ["scraped_at"])
    op.create_index("ix_raw_posting_html_hash", "raw_posting", ["html_hash"])

    op.create_table(
        "hiring_event",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("person_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("person.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("organization.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("role.id", ondelete="SET NULL"), nullable=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("project.id", ondelete="SET NULL"), nullable=True),
        sa.Column("placement_type", sa.String(32), nullable=False),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=True),
        sa.Column("early_departure_reason", sa.String(255), nullable=True),
        sa.Column("source_channel", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_hiring_event_person", "hiring_event", ["person_id"])
    op.create_index("ix_hiring_event_organization", "hiring_event", ["organization_id"])
    op.create_index("ix_hiring_event_start_date", "hiring_event", ["start_date"])

    comp_source_type = postgresql.ENUM(
        "placement_verified", "posted", "modeled", "self_reported", "third_party",
        name="comp_source_type",
        create_type=False,
    )
    comp_source_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "compensation_record",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("hiring_event_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("hiring_event.id", ondelete="CASCADE"), nullable=True),
        sa.Column("occupation_code", sa.String(16), nullable=True),
        sa.Column("occupation_system", sa.String(16), nullable=True),
        sa.Column("industrial_overlay_code", sa.String(64), nullable=True),
        sa.Column("seniority", sa.String(32), nullable=True),
        sa.Column("region_code", sa.String(8), nullable=True),
        sa.Column("sector", sa.String(64), nullable=True),
        sa.Column("amount_low", sa.Numeric(12, 2), nullable=True),
        sa.Column("amount_mid", sa.Numeric(12, 2), nullable=False),
        sa.Column("amount_high", sa.Numeric(12, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("period", sa.String(16), nullable=False, server_default="annual"),
        sa.Column("source_type", comp_source_type, nullable=False),
        sa.Column("confidence", sa.Numeric(3, 2), nullable=False, server_default="0.5"),
        sa.Column("observed_on", sa.Date, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_comp_occupation", "compensation_record", ["occupation_system", "occupation_code"])
    op.create_index("ix_comp_region", "compensation_record", ["region_code"])
    op.create_index("ix_comp_source_type", "compensation_record", ["source_type"])
    op.create_index("ix_comp_observed_on", "compensation_record", ["observed_on"])

    recruiter_event_type = postgresql.ENUM(
        "candidate_introduced", "client_interview_scheduled", "offer_extended",
        "placement_confirmed", "candidate_declined", "early_departure",
        "client_engaged", "candidate_outreach", "candidate_response",
        name="recruiter_event_type",
        create_type=False,
    )
    recruiter_event_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "recruiter_interaction",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", recruiter_event_type, nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("person_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("person.id", ondelete="CASCADE"), nullable=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("organization.id", ondelete="SET NULL"), nullable=True),
        sa.Column("recruiter", sa.String(128), nullable=True),
        sa.Column("notes", sa.String(2048), nullable=True),
        sa.Column("payload", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_recruiter_event_type", "recruiter_interaction", ["event_type"])
    op.create_index("ix_recruiter_occurred_at", "recruiter_interaction", ["occurred_at"])
    op.create_index("ix_recruiter_person", "recruiter_interaction", ["person_id"])
    op.create_index("ix_recruiter_organization", "recruiter_interaction", ["organization_id"])

    # Semantic dedup support: embedding column on posting (pgvector).
    op.execute("ALTER TABLE posting ADD COLUMN description_embedding vector(384)")
    op.execute(
        "CREATE INDEX ix_posting_embedding ON posting "
        "USING ivfflat (description_embedding vector_cosine_ops) WITH (lists = 100)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_posting_embedding")
    op.drop_table("recruiter_interaction")
    op.execute("DROP TYPE IF EXISTS recruiter_event_type")
    op.drop_table("compensation_record")
    op.execute("DROP TYPE IF EXISTS comp_source_type")
    op.drop_table("hiring_event")
    op.drop_table("raw_posting")
    op.drop_table("posting")
    op.drop_table("role")
    op.drop_table("project")
    op.drop_table("skill")
    op.execute("DROP TYPE IF EXISTS skill_category")
    op.drop_table("organization")
    op.drop_table("person")
