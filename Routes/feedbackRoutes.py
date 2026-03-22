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

@feedback_bp.post("/continue/{job_id}")
async def get_by_excel_feedback_continue_endpoint(
    job_id: str,
    controller: FeedbackController = Depends()
):
    return await controller.run_continue_doing_by_job(job_id)

@feedback_bp.post("/stop/{job_id}")
async def get_by_excel_feedback_stop_endpoint(
    job_id: str,
    controller: FeedbackController = Depends()
):
    return await controller.run_stop_doing_by_job(job_id)