from fastapi import APIRouter, Depends, HTTPException

from app.auth import create_access_token, dummy_verify, get_current_user, verify_password
from app.database import get_db
from app.models import User
from app.repository import users as users_repo
from app.schemas import LoginRequest, TokenOut, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


# Exchange username and password for a JWT the webapp sends as a Bearer token
@router.post("/login", response_model=TokenOut)
def login(payload: LoginRequest, db=Depends(get_db)): 
    user = users_repo.get_by_username(db, payload.username)

    if user is None: 
        dummy_verify(payload.password)
        raise HTTPException(401, "wrong username or password")

    if not verify_password(payload.password, user.password_hash): 
        raise HTTPException(401, "wrong username or password")

    token, expires_in = create_access_token(user)
    return TokenOut(access_token=token, expires_in=expires_in, user=UserOut.model_validate(user))


# Who the current token belongs to; the webapp calls this to restore a session
@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)): 
    return user
