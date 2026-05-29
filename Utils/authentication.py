import jwt
from jwt.exceptions import (
    InvalidTokenError,
    ExpiredSignatureError
)
from passlib.context import CryptContext
import os


class Authentication:
    def __init__(self):
        self.secret_key = os.getenv("SECRET_KEY")
        self.algorithm = os.getenv("ALGORITHM")
        self.expires_in = int(os.getenv("ACCESS_TOKEN_EXPIRE_HOURS"))
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
    def hash_password(self, password):
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password, hashed_password):
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def create_token(self, data: dict):
        return jwt.encode(data, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str):
        return jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

