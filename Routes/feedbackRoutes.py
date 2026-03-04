from Controllers.feedbackController import FeedbackController
from fastapi import APIRouter  ,UploadFile, File,Depends

feedback_bp=APIRouter(prefix="/api/feedback/excel")

@feedback_bp.post("/getByExcel")
async def get_by_excel_feedback_data_endpoint(
    file: UploadFile | None = File(None),
    controller:FeedbackController= Depends()
):
    return await controller.get_feedback_data_excel(file)
