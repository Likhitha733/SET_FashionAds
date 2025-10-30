from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import timedelta
from backend.db.database import get_db
from backend.db import models
from backend.db.database import SessionLocal, get_db


router = APIRouter()

class UserCreate(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

@router.post("/register", description="Register a new user.")
def register(user: UserCreate, db: Session = Depends(get_db)):
    if len(user.password) > 72:
        raise HTTPException(status_code=400, detail="Password too long (<=72 required).")
    if db.query(models.User).filter(models.User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    try:
        hashed = auth_utils.get_password_hash(user.password)
        db_user = models.User(username=user.username, hashed_password=hashed)
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return {"msg": "User registered successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/login", response_model=TokenResponse, description="User login, returns JWT token.")
def login(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if not db_user or not auth_utils.verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = auth_utils.create_access_token(
        data={"sub": user.username}, expires_delta=timedelta(minutes=120)
    )
    return {"access_token": access_token, "token_type": "bearer"}
