from Models.userModel import User
from Utils.authentication import Authentication
from Utils.apiException import ApiException
from bson import ObjectId


class UserController:
    def __init__(self):
        self.user = User
        self.auth = Authentication()
    
    def create_user(self, data):
        try:
            if not data.get("email") or not data.get("password"):
                raise ApiException(400, "Email and password are required")

            user = self.user.objects(email=data.get("email")).first()
            if user:
                raise ApiException(400, "User already exists")

            user = self.user(**data)
            user.password = self.auth.hash_password(user.password)
            user.save()
            user_dict = user.to_dict()
            return {
                "message": "User created successfully",
                "user": user_dict.get("id","")
            }
        except ApiException:
            raise
        except Exception as e:
            raise ApiException(500, "Error creating user", str(e))

    def get_user_by_id(self, user_id):
        try:
            user = self.user.objects(id=user_id).first()
            if not user:
                raise ApiException(404, "User not found")
            return user.to_dict()
        except ApiException:
            raise
        except Exception as e:
            raise ApiException(500, "Error getting user", str(e))
    
    def get_all_users(self,user_id):
        try:
            users = self.user.objects(id__ne=user_id)
            return [{
                "id": str(user.id),
                "email": user.email,
                "role": user.role
            } for user in users]
        except Exception as e:
            raise ApiException(500, "Error getting users", str(e))

  