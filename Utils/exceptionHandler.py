from fastapi.responses import JSONResponse
from Utils.apiException import ApiException
from fastapi.requests import Request

async def exception_handler(request: Request, exc: ApiException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.message}
    )

async def default_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"message": str(exc)}
    )