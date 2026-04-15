from Controllers.lbscore360Controller import LBscore360Controller
from fastapi import APIRouter,UploadFile,File,Depends
from fastapi.responses import StreamingResponse
from typing import List

lbscore360_bp=APIRouter(prefix="/api/lbscore360/excel")

@lbscore360_bp.post("/base",response_class=StreamingResponse)
async def get_by_excel_lbscore360_base_endpoint(
    files:List[UploadFile]=File(None),
    controller:LBscore360Controller=Depends()
):
    return await controller.start_lbscore360_excel_base_job(files)
