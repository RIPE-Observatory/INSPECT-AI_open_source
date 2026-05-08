from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.crud import reviewer as reviewer_crud
from core.db.models.reviewer import Reviewer
from core.db.session import get_db_session
from core.config import get_settings

from .auth import AuthenticatedUser, get_current_user


async def get_reviewer_record(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Reviewer:
    reviewer = await reviewer_crud.ensure_reviewer(db, current_user.clerk_user_id)
    if get_settings().DISABLE_AUTH and not reviewer.onboarding_complete:
        reviewer.given_name = "Demo"
        reviewer.family_name = "Reviewer"
        reviewer.username = "demo-reviewer"
        reviewer.email = "demo@example.invalid"
        reviewer.affiliation_institution = "Local reproducibility run"
        reviewer.role = "Reviewer"
        reviewer.onboarding_complete = True
        await db.flush()
    return reviewer


async def require_complete_reviewer(
    reviewer: Reviewer = Depends(get_reviewer_record),
) -> Reviewer:
    if not reviewer.onboarding_complete:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reviewer profile is incomplete.",
        )
    return reviewer
