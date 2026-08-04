from fastapi import APIRouter, Body
from Controllers.categoryConfigController import CategoryConfigController

category_config_bp = APIRouter(prefix="/api/lbscore360/categories", tags=["Category Configuration"])

@category_config_bp.get("")
def get_categories():
    return CategoryConfigController.get_all()

@category_config_bp.post("")
def create_category(data: dict = Body(...)):
    return CategoryConfigController.create(data)

@category_config_bp.put("/{config_id}")
def update_category(config_id: str, data: dict = Body(...)):
    return CategoryConfigController.update(config_id, data)

@category_config_bp.delete("/{config_id}")
def delete_category(config_id: str):
    return CategoryConfigController.delete(config_id)

@category_config_bp.patch("/reorder")
def reorder_categories(orders_list: list = Body(...)):
    return CategoryConfigController.reorder(orders_list)
