from fastapi import APIRouter, UploadFile, File, Depends
from fastapi.responses import StreamingResponse
from typing import List
from Controllers.FeedbackSummaryController import FeedbackSummaryController

feedback_summary_bp = APIRouter(prefix="/api/feedback/summary")

@feedback_summary_bp.post("/base", response_class=StreamingResponse)
async def get_by_excel_feedback_base_endpoint(
    files: List[UploadFile] = File(None),
    controller: FeedbackSummaryController = Depends()
):
    return await controller.start_feedback_excel_base_job(files)

