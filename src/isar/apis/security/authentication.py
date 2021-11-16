from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security.base import SecurityBase
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from isar.config import config


class Token(BaseModel):
    access_token: str
    token_type: str

    @staticmethod
    def get_token():
        should_authenticate = config.getboolean("fastapi", "authentication")
        if should_authenticate:
            return OAuth2PasswordBearer(tokenUrl="token")
        return NoSecurity


class User(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None


class UserInDB(User):
    hashed_password: str


class NoSecurity(SecurityBase):
    def __init__(self) -> None:
        self.scheme_name = "No Security"


class Authenticator:
    def __init__(
        self,
        username=config.get("fastapi", "username"),
        hashed_password=config.get("fastapi", "hashed_password"),
        access_token_key=config.get("fastapi", "access_token_key"),
        access_token_algorithm=config.get("fastapi", "access_token_algorithm"),
        access_token_expire_minutes=config.getint(
            "fastapi", "access_token_expire_minutes"
        ),
    ) -> None:
        self.user_data = {
            username: {"username": username, "hashed_password": hashed_password}
        }
        self.access_token_key = access_token_key
        self.access_token_algorithm = access_token_algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def verify_password(self, plain_password, hashed_password):
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password):
        return self.pwd_context.hash(password)

    def get_user(self, username: str):
        if username in self.user_data:
            user_dict = self.user_data[username]
            return UserInDB(**user_dict)

    def authenticate_user(self, username: str, password: str):
        user = self.get_user(username)
        if not user:
            return False
        if not self.verify_password(password, user.hashed_password):
            return False
        return user

    def create_access_token(
        self, data: dict, expires_delta: Optional[timedelta] = None
    ):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode, key=self.access_token_key, algorithm=self.access_token_algorithm
        )
        return encoded_jwt

    def login_for_access_token(
        self,
        form_data: OAuth2PasswordRequestForm = Depends(),
    ):
        user = self.authenticate_user(form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        access_token_expires = timedelta(minutes=self.access_token_expire_minutes)
        access_token = self.create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
