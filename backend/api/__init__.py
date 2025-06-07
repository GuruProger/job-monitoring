from fastapi import APIRouter

from .hh_research.router import router as hh_router


router = APIRouter()

router.include_router(
    hh_router,
)