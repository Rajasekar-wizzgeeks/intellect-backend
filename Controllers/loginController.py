from Models.userModel import User
from Utils.authentication import Authentication
from Utils.apiException import ApiException
import os
from datetime import datetime, timedelta,timezone

class LoginController:
    def __init__(self):
        self.user = User
        self.auth = Authentication()

    
    def login(self, data):
        try:
            user = self.user.objects(email=data["email"]).first()
            if user and self.auth.verify_password(data["password"], user.password):
                expires_in_hrs = int(os.getenv("ACCESS_TOKEN_EXPIRE_HOURS"))
                expires_in = datetime.now(timezone.utc) + timedelta(hours=expires_in_hrs)
                token = self.auth.create_token({
                    "user_id": str(user.id),
                    "email": user.email,
                    "role": user.role,
                    "exp": expires_in
                })
                user.token = token
                user.save()
                return {
                    "message": "User logged in successfully",
                    "user": str(user.id),
                    "email": user.email,
                    "role": user.role,
                    "token": token
                }
            else:
                raise ApiException(401, "Invalid credentials")
        except ApiException:
            raise
        except Exception as e:
            raise ApiException(500, "Error logging in " + str(e))

    def logout(self, token):
        try:
            user = self.user.objects(token=token).first()
            if user:
                user.token = ""
                user.save()
                return {
                    "message": "User logged out successfully"
                }
            else:
                raise ApiException(404, "User not found")

        except ApiException:
            raise
        except Exception as e:
            raise ApiException(500, "Error logging out " + str(e))


