from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security.base import SecurityBase
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from injector import inject
from jose import jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from isar.config import config
from isar.config.keyvault.keyvault_service import Keyvault


class Token(BaseModel):
    access_token: str
    token_type: str

    @staticmethod
    def get_token():
        should_authenticate = config.getboolean("fastapi", "authentication_enabled")
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
    @inject
    def __init__(
        self,
        keyvault: Keyvault,
        username=config.get("fastapi", "username"),
        token_algorithm=config.get("fastapi", "token_algorithm"),
        token_expire_minutes=config.getint("fastapi", "token_expire_minutes"),
    ) -> None:
        self.keyvault = keyvault
        self.token_key = self.keyvault.get_secret("ISAR-API-TOKEN-KEY").value
        self.hashed_password = self.keyvault.get_secret(
            "ISAR-API-HASHED-PASSWORD"
        ).value

        self.user_data = {
            username: {"username": username, "hashed_password": self.hashed_password}
        }

        self.token_algorithm = token_algorithm
        self.token_expire_minutes = token_expire_minutes
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def verify_password(self, plain_password, hashed_password):
        return self.pwd_context.verify(plain_password, hashed_password)

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
            to_encode, key=self.token_key, algorithm=self.token_algorithm
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
        access_token_expires = timedelta(minutes=self.token_expire_minutes)
        access_token = self.create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
