from fastapi import APIRouter

from app.mneme.utils.response import success_response

router = APIRouter(prefix="/support", tags=["support"])


@router.get("/documentation")
def get_documentation_status():
    return success_response(
        data={
            "status": "planned",
            "message": "Documentation workspace is reserved for a future release.",
        }
    )


@router.get("/contact")
def get_support_status():
    return success_response(
        data={
            "status": "planned",
            "message": "Support contact workflow is reserved for a future release.",
        }
    )
