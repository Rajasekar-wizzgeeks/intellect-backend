from mongoengine import Document, DateTimeField, ReferenceField,ListField,DictField,StringField,ObjectIdField
from datetime import datetime,timezone
from mongoengine import CASCADE

class FeedbackDraft(Document):
    user_id = ReferenceField("User", required=True,default=None,reverse_delete_rule=CASCADE)
    feedback_data = ListField(DictField(),required=True,default=list)
    excel_name = StringField(required=True,default="")
    report_type = StringField(required=True,default="lbscore360",choices=["lbscore360","feedback360","360summaryreport"])
    editors = ListField(ObjectIdField(),default=list)
    viewers = ListField(ObjectIdField(),default=list)
    created_at = DateTimeField(default=lambda: datetime.now(timezone.utc))
    updated_at = DateTimeField(default=lambda: datetime.now(timezone.utc))
    
    def save(self, *args, **kwargs):
        self.updated_at = datetime.now(timezone.utc)
        self._mark_as_changed('updated_at')
        return super().save(*args, **kwargs)
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id.id),
            "feedback_data": self.feedback_data,
            "report_type": self.report_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    meta = {
        'collection': 'feedback_drafts',
        'indexes': [
            'user_id',
            'report_type',
            ('user_id', 'report_type')
        ]
    }
    