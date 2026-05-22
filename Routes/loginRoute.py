from Controllers.loginController import LoginController
from fastapi import APIRouter
from fastapi.requests import Request

login_controller = LoginController()

login_bp = APIRouter(prefix="/api/user")

@login_bp.post("/login")
async def login(request: Request):
    data = await request.json()
    return login_controller.login(data)