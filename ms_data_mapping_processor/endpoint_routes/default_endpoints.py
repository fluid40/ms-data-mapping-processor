from fastapi import APIRouter

router = APIRouter()


@router.get(
    "/",
    tags=["Root"],
    response_model=dict,
    responses={"400": {"model": dict}},
    name="getRoot",
    description="Get root message for microservice REST API",
    summary="Get the root message",
)
async def get_root():
    """Get root message for microservice REST API."""
    return {"message": "Welcome to the Fluid4.0 runtime REST API backend. Go to /docs for API documentation."}
