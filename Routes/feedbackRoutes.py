from Controllers.feedbackController import FeedbackController
from fastapi import APIRouter  ,UploadFile, File,Depends
from typing import List

feedback_bp=APIRouter(prefix="/api/feedback/excel")

@feedback_bp.post("/getByExcel")
async def get_by_excel_feedback_data_endpoint(
    files: List[UploadFile] = File(None),
    controller:FeedbackController= Depends()
):
    return await controller.get_feedback_data_excel(files)