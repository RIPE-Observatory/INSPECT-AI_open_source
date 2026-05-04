from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.crud import reviewer as reviewer_crud
from core.db.models.reviewer import Reviewer
from core.db.session import get_db_session
from core.schemas.reviewer import ReviewerProfileResponse, ReviewerProfileUpdate
from core.middleware.rate_limit import limiter

from api.dependencies.auth import AuthenticatedUser, get_current_user
from api.dependencies.reviewer import get_reviewer_record

router = APIRouter()


@router.get("/reviewers/me", response_model=ReviewerProfileResponse)
@limiter.limit("20/minute")
async def get_reviewer_me(
    request: Request,
    reviewer: Reviewer = Depends(get_reviewer_record),
    db: AsyncSession = Depends(get_db_session),
) -> ReviewerProfileResponse:
    await db.commit()
    await db.refresh(reviewer)
    return ReviewerProfileResponse.model_validate(reviewer)


@router.put("/reviewers/me", response_model=ReviewerProfileResponse)
@limiter.limit("20/minute")
async def update_reviewer_me(
    request: Request,
    payload: ReviewerProfileUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ReviewerProfileResponse:
    reviewer = await reviewer_crud.update_reviewer_profile(
        db, current_user.clerk_user_id, payload
    )
    await db.commit()
    await db.refresh(reviewer)
    return ReviewerProfileResponse.model_validate(reviewer)
