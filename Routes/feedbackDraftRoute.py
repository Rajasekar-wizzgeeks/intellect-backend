from fastapi import APIRouter
from Controllers.feedbackDraftController import FeedbackDraftController
from fastapi.requests import Request

feedback_draft_router = APIRouter(prefix="/api/user/feedback-draft", tags=["Feedback Draft"])
controller = FeedbackDraftController()

@feedback_draft_router.post("/create")
async def create_feedback_draft(request: Request):
    user = request.scope["user"]
    data = await request.json()
    return controller.create_feedback_draft(user, data)

@feedback_draft_router.get("/get")
async def get_feedback_draft(request: Request):
    user = request.scope["user"]
    return controller.get_feedback_draft(user)

@feedback_draft_router.get("/getOne")
async def get_feedback_draft_by_id(feedback_draft_id: str, request: Request):
    user = request.scope["user"]
    return controller.get_feedback_draft_by_id(user,feedback_draft_id)

@feedback_draft_router.put("/update")
async def update_feedback_draft(request: Request):
    user = request.scope["user"]
    data = await request.json()
    feedback_draft_id = data.get("feedback_draft_id")
    feedback_data = data.get("feedback_data")
    report_type = data.get("report_type")
    return controller.update_feedback_draft(user, feedback_draft_id, feedback_data, report_type)


@feedback_draft_router.post("/giveAccess")
async def give_access(request: Request):
    data = await request.json()
    feedback_draft_id = data.get("feedback_draft_id")
    editors = data.get("editors", [])
    viewers = data.get("viewers", [])
    user = request.scope["user"]
    return controller.give_access(user, feedback_draft_id, editors, viewers)

