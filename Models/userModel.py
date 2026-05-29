from mongoengine import Document, StringField, DateTimeField,ObjectIdField,ListField
from datetime import datetime,timezone

class User(Document):
    email = StringField(required=True,unique=True)
    password = StringField(required=True)
    created_at = DateTimeField(default=lambda: datetime.now(timezone.utc))
    updated_at = DateTimeField(default=lambda: datetime.now(timezone.utc))
    role = StringField(required=True, default="user",choices=["user","admin"])
    token = StringField(required=False)
    meta = {
        "collection": "users",
        "indexes": [
            "role",
            "-created_at",
            ("role", "-created_at"),
        ]
    }
    def save(self, *args, **kwargs):
        self.updated_at = datetime.now(timezone.utc)
        return super().save(*args, **kwargs)

    def to_dict(self):
        return {
            "id": str(self.id),
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }