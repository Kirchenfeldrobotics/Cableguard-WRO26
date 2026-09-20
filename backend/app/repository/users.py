from sqlalchemy.orm import Session

from app.auth import hash_password
from app.models import User


def get_by_username(db, username): 
    return db.query(User).filter(User.username == username).one_or_none()


def ensure_default_user(db, username, password): 
    """Creates the single operator account on first start.

    An existing account is left untouched, so a password changed in the database
    is never reset back to the default.
    """
    user = get_by_username(db, username)
    if user is not None: 
        return user

    user = User(username=username, password_hash=hash_password(password))
    db.add(user)
    db.flush()
    return user
