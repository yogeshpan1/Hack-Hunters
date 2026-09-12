import os
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .db import get_db
from .models import User

# A process-local random key is safe for an unconfigured local demo; restarts expire tokens.
SECRET = os.getenv("JWT_SECRET") or secrets.token_hex(32)
bearer = HTTPBearer(auto_error=False)
ROLES = ["Registrar"]
MANAGE = {entity: ["Registrar"] for entity in ["rooms", "faculty", "programmes", "modules", "cohorts", "students", "users", "sessions", "rules"]}

def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()
    return f"{salt}${digest}"

def verify_password(password, value):
    return hmac.compare_digest(password_hash(password, value.split("$")[0]), value)

def token_for(user):
    return jwt.encode({"sub": str(user.id), "iss":"nexus-mongodb-v1", "exp": datetime.now(timezone.utc) + timedelta(hours=8)}, SECRET, algorithm="HS256")

def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer), db=Depends(get_db)):
    try:
        data = jwt.decode(credentials.credentials, SECRET, algorithms=["HS256"],issuer="nexus-mongodb-v1",options={"require":["sub","exp","iss"]}) if credentials else {}
        user = db.get(User, int(data["sub"]))
        if not user or not user.active:
            raise ValueError()
        return user
    except (jwt.PyJWTError, ValueError, KeyError, AttributeError):
        raise HTTPException(401, "Please sign in again.")

def require(user, roles):
    if user.role not in ["Super Admin", "Registrar", *roles]:
        raise HTTPException(403, "Your role does not permit this action.")

def public_user(user):
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role, "active": user.active, "faculty_id": user.faculty_id, "cohort_id": user.cohort_id}
