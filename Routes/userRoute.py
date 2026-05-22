from Controllers.userController import UserController
from fastapi import APIRouter
from fastapi.requests import Request

user_controller = UserController()

user_bp = APIRouter(prefix="/api/user")

@user_bp.post("/create")
async def create_user(request: Request):
    data = await request.json()
    return user_controller.create_user(data)

@user_bp.get("/all")
async def get_all_users():
    return user_controller.get_all_users()

@user_bp.get("/getOne")
async def get_user(user_id: str):
    return user_controller.get_user_by_id(user_id)


