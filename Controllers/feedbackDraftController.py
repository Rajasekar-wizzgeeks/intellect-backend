from Models.feedbackDraft import FeedbackDraft
from Utils.apiException import ApiException
from Models.userModel import User
from bson import ObjectId

class FeedbackDraftController:
    def __init__(self):
        self.feedback_draft_model = FeedbackDraft
        self.user_model = User
    
    def create_feedback_draft(self, user, data):
        try:
            user_id = user.get("user_id","")
            feedback_data = data.get("feedback_data")
            report_type = data.get("report_type")
            excel_name = data.get("excel_name")
            excel_name = excel_name.strip().lower().replace(" ", "_") if excel_name else ""
            existing_draft = self.feedback_draft_model.objects(excel_name=excel_name, report_type=report_type).first()
    
            if existing_draft:
                owner_id = existing_draft.user_id.id
    
                if str(owner_id) != user_id:
                    if ObjectId(user_id) not in existing_draft.editors:
                        raise ApiException(403, "You are not authorized to edit this feedback draft")
                existing_draft.feedback_data = feedback_data
                existing_draft.save()
                return {
                    "message": "Feedback draft updated successfully",
                    "id": str(existing_draft.id)
                }
            
            feedback_draft = self.feedback_draft_model(
                user_id=user_id,
                feedback_data=feedback_data,
                report_type=report_type,
                excel_name=excel_name
            )
            feedback_draft.save()
            return {
                "message": "Feedback draft created successfully",
                "id": str(feedback_draft.id)
            }
        except ApiException:
            raise
        except Exception as e:
            raise ApiException(500, "Error creating feedback draft "+ str(e))

    def create_multi_feedback_draft(self, user, data):
        try:
            user_id = user.get("user_id", "")

            # Accept either a list of drafts or a single draft object
            drafts = data if isinstance(data, list) else [data]

            saved_ids = []
            for item in drafts:
                feedback_data = item.get("feedback_data")
                report_type = item.get("report_type")
                excel_name = item.get("excel_name", "")
                excel_name = excel_name.strip().lower().replace(" ", "_") if excel_name else ""

                # Check if a draft already exists for this user + excel_name + report_type
                existing = self.feedback_draft_model.objects(
                    user_id=user_id,
                    excel_name=excel_name,
                    report_type=report_type
                ).first()

                if existing:
                    existing.feedback_data = feedback_data
                    existing.save()
                    saved_ids.append(str(existing.id))
                else:
                    feedback_draft = self.feedback_draft_model(
                        user_id=user_id,
                        feedback_data=feedback_data,
                        report_type=report_type,
                        excel_name=excel_name
                    )
                    feedback_draft.save()
                    saved_ids.append(str(feedback_draft.id))

            return {
                "message": f"{len(saved_ids)} feedback draft(s) saved successfully",
                "ids": saved_ids
            }
        except Exception as e:
            raise ApiException(500, "Error saving feedback drafts " + str(e))
    
    def get_feedback_draft(self,user):
        try:
            user_id = user.get("user_id")
            feedback_drafts = self.feedback_draft_model.objects(user_id=user_id)
            if feedback_drafts:
                return [{
                    "id": str(feedback.id),
                    "excel_name": feedback.excel_name,
                    "reporttype": feedback.report_type,
                    "created_at": feedback.created_at.isoformat() if feedback.created_at else None,
                    "updated_at": feedback.updated_at.isoformat() if feedback.updated_at else None
                } for feedback in feedback_drafts]
            else:
                return {
                    "message": "No feedback draft found for this user"
                }
        except Exception as e:
            raise ApiException(500, "Error getting feedback draft"+ str(e))

    def get_feedback_draft_by_id(self,user, feedback_draft_id):
        try:
            user_id = user.get("user_id")
            feedback_draft = self.feedback_draft_model.objects(id=feedback_draft_id).first()
            owner_id = feedback_draft.user_id.id
            access_type = "owner"
            if not feedback_draft:
                raise ApiException(404, "Feedback draft not found")
            if str(owner_id) != user_id:
                if ObjectId(user_id) not in feedback_draft.editors and ObjectId(user_id) not in feedback_draft.viewers:
                    raise ApiException(403, "You are not authorized to access this feedback draft")
                elif ObjectId(user_id) in feedback_draft.editors:
                    access_type = "editor"
                elif ObjectId(user_id) in feedback_draft.viewers:
                    access_type = "viewer"
            if ObjectId(user_id) in feedback_draft.editors:
                feedback_draft.is_edited = True
                feedback_draft.save()
            if feedback_draft:
                result = feedback_draft.to_dict()
                result["access_type"] = access_type
                return result
            else:
                return {
                    "message": "No feedback draft found for this id"
                }
        except ApiException:
            raise
        except Exception as e:
            raise ApiException(500, "Error getting feedback draft"+ str(e))
    
    def update_feedback_draft(self, user, feedback_draft_id, feedback_data, report_type):
        try:
            feedback_draft = self.feedback_draft_model.objects(id=feedback_draft_id).first()
            user_id = user.get("user_id","")
            if not feedback_draft:
                raise ApiException(404, "Feedback draft not found")
            if str(feedback_draft.user_id.id) != user_id:
                if ObjectId(user_id) not in feedback_draft.editors:
                    raise ApiException(403, "You are not authorized to edit this feedback draft")
            feedback_draft.feedback_data = feedback_data
            feedback_draft.report_type = report_type
            feedback_draft.save()
            return {
                "message": "Feedback draft updated successfully",
                "id": str(feedback_draft.id)
            }
        except ApiException:
            raise
        except Exception as e:
            raise ApiException(500, "Error updating feedback draft"+ str(e))

    def give_access(self, user,feedback_draft_id, editors, viewers):
        try:
            # if user.get("role","") != "admin":
            #     raise ApiException(403, "Only admin can give access")

            user_obj = self.user_model.objects(id=user.get("user_id","")).first()
            if not user_obj:
                raise ApiException(404, "User not found")

            feedback_draft = self.feedback_draft_model.objects(id=feedback_draft_id).first()
            if not feedback_draft:
                raise ApiException(404, "Feedback draft not found")

            if user.get("role") != "admin" and (ObjectId(user.get("user_id")) not in feedback_draft.editors and ObjectId(user.get("user_id")) not in feedback_draft.viewers):
                raise ApiException(403, "You are not authorized to give access to this feedback draft")
            
            if editors:
                for editor in editors:
                    if ObjectId(editor) in feedback_draft.viewers:
                        feedback_draft.viewers.remove(ObjectId(editor))
                    if ObjectId(editor) not in feedback_draft.editors:
                        feedback_draft.editors.append(ObjectId(editor))

            if viewers:
                for viewer in viewers:
                    if ObjectId(viewer) not in feedback_draft.editors:
                        if ObjectId(viewer) not in feedback_draft.viewers:
                            feedback_draft.viewers.append(ObjectId(viewer))

            feedback_draft.save()
            return {
                "message": "Access given successfully",
                "editors": [str(editor) for editor in feedback_draft.editors],
                "viewers": [str(viewer) for viewer in feedback_draft.viewers]
            }
        except ApiException:
            raise
        except Exception as e:
            raise ApiException(500, "Error giving access "+str(e))
    

    
    def delete_feedback_draft(self,user, feedback_draft_id):
        try:
            feedback_draft = self.feedback_draft_model.objects(id=feedback_draft_id).first()
            user_id = user.get("user_id","")
            if not feedback_draft:
                raise ApiException(404, "Feedback draft not found")
            if str(feedback_draft.user_id.id) != user_id:
                if ObjectId(user_id) not in feedback_draft.editors:
                    raise ApiException(403, "You are not authorized to delete this feedback draft")
            if feedback_draft:
                feedback_draft.delete()
                return {
                    "message": "Feedback draft deleted successfully",
                    "id": str(feedback_draft_id)
                }
        except ApiException:
            raise
        except Exception as e:
            raise ApiException(500, "Error deleting feedback draft "+str(e))
    