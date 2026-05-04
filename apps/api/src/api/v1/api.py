from fastapi import APIRouter

from .endpoints import jobs, reviewers, test

api_router = APIRouter()
api_router.include_router(jobs.router, tags=["jobs"])
api_router.include_router(reviewers.router, tags=["reviewers"])
api_router.include_router(test.router, tags=["test"])
