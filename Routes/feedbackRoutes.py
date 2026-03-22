from Controllers.feedbackController import FeedbackController
from fastapi import APIRouter  ,UploadFile, File,Depends
from typing import List

feedback_bp=APIRouter(prefix="/api/feedback/excel")

@feedback_bp.post("/base")
async def get_by_excel_feedback_base_endpoint(
    files: List[UploadFile] = File(None),
    controller: FeedbackController = Depends()
):
    return await controller.start_feedback_excel_base_job(files)

@feedback_bp.post("/continue")
async def get_by_excel_feedback_continue_endpoint(
    files: List[UploadFile] = File(None),
    controller: FeedbackController = Depends()
):
    return await controller.extract_continue_doing_from_excel(files)

@feedback_bp.post("/stop")
async def get_by_excel_feedback_stop_endpoint(
    files: List[UploadFile] = File(None),
    controller: FeedbackController = Depends()
):
    return await controller.extract_stop_doing_from_excel(files)