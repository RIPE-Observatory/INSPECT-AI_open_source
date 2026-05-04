from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.models.reviewer import Reviewer
from core.schemas.reviewer import ReviewerProfileUpdate


async def get_reviewer_by_clerk_user_id(
    db: AsyncSession, clerk_user_id: str
) -> Optional[Reviewer]:
    stmt = select(Reviewer).where(Reviewer.clerk_user_id == clerk_user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def ensure_reviewer(
    db: AsyncSession, clerk_user_id: str
) -> Reviewer:
    reviewer = await get_reviewer_by_clerk_user_id(db, clerk_user_id)
    if reviewer:
        return reviewer

    reviewer = Reviewer(clerk_user_id=clerk_user_id, onboarding_complete=False)
    db.add(reviewer)
    await db.flush()
    return reviewer


async def update_reviewer_profile(
    db: AsyncSession,
    clerk_user_id: str,
    payload: ReviewerProfileUpdate,
) -> Reviewer:
    reviewer = await ensure_reviewer(db, clerk_user_id)

    reviewer.given_name = payload.given_name
    reviewer.family_name = payload.family_name
    reviewer.username = payload.username
    reviewer.email = payload.email
    reviewer.affiliation_institution = payload.affiliation_institution
    reviewer.affiliation_department = payload.affiliation_department
    reviewer.role = payload.role
    reviewer.country = payload.country
    reviewer.orcid = payload.orcid
    reviewer.onboarding_complete = payload.onboarding_complete

    if payload.kg_visibility is not None and payload.kg_visibility != reviewer.kg_visibility:
        reviewer.kg_visibility = payload.kg_visibility
        reviewer.kg_visibility_updated_at = datetime.now(timezone.utc)

    reviewer.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return reviewer
