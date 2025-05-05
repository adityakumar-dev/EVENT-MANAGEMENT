import os
from fastapi import FastAPI, Depends, UploadFile, File, Form, Query
from fastapi.responses import  JSONResponse
from sqlalchemy.orm import Session
from database import SessionLocal, engine, sessionmaker
import models
from uuid import uuid4
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from sqlalchemy import func
from dotenv import load_dotenv
import json
from fastapi.responses import FileResponse
# Load environment variables from .env file
load_dotenv()

from routes import analytics, app_users_handler, food_router, push_update, qr, users
from routes import face_capture
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

# Create Tables
models.Base.metadata.create_all(bind=engine)
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

IMAGE_DIR = "images"
if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
# Mount the static directory
app.mount("/static", StaticFiles(directory="uploads"), name="static")
# app.mount("/static/app_users", StaticFiles(directory="app_users"), name="app_users")
# app.mount("/static/images", StaticFiles(directory="institutions"), name="institutions")
app.mount("/images", StaticFiles(directory="images"), name="images")

app.mount("/uploads", StaticFiles(directory="uploads"))
app.include_router(users.router, prefix="/users", tags=["users"])
# app.include_router(institutions.router, prefix="/institutions", tags=["institutions"])
app.include_router(qr.router, prefix="/qr", tags=["qr"])
app.include_router(app_users_handler.router, prefix="/app_users", tags=["app_users"])
app.include_router(analytics.router, )
app.include_router(push_update.router, )
app.include_router(face_capture.router, prefix="/face_capture", tags=["face_capture"])
app.include_router(food_router.router)
@app.get("/")
async def check():
    return {True}

@app.get("/health-check")
async def health_check():
    return {"status": "ok"}

# Face get route


@app.get("/users/image/")
async def get_user_image(
    path: str = Form(...),
):
    # /static/hey/1_0f323d8e-6673-4037-b0e9-6d068baad518.jpg
    try:
        #check file exist or not
        if not os.path.exists(f"images/{path}"):
            raise HTTPException(status_code=404, detail="Image not found")
        return FileResponse(f"images/{path}")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Image not found")
@app.get("/users/image/all") 
async def get_all_user_images(user_id: str = Form(...),db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    #get all the images list on the user name directory  
    images = os.listdir(f"images/{user.name}")
    #adding the user name to the images list
    images = [f"{user.name}/{image}" for image in images]
    return images
    # return FileResponse(f"images/")