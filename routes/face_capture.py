from datetime import datetime
import fastapi
from fastapi import Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from models import User, FinalRecords
from dependencies import get_db, get_current_app_user
import os
import uuid
import pytz
from fastapi import Form
router = fastapi.APIRouter()
import models
from dependencies import get_current_app_user
@router.post("/capture")
async def capture_face(
    user_id: str = Form(...),
    current_app_user: models.AppUsers = Depends(get_current_app_user),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        # Validate the uploaded file type
        #check image using extension
        if not file.filename.endswith(('.jpg', '.jpeg', '.png','.PNG','.JPG','.JPEG','.WEBP','.webp')):
            raise HTTPException(status_code=400, detail="Uploaded file is not an image")

        # Get the user from the database
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Create a directory for the user's images if it doesn't exist
        path = f"images/{user.name}"
        os.makedirs(path, exist_ok=True)

        # Save the uploaded image with a unique filename
        image_filename = f"{user.user_id}_{uuid.uuid4()}.jpg"
        image_path = os.path.join(path, image_filename)
        
        # Write the image to the file system
        with open(image_path, "wb") as f:
            f.write(await file.read())

        # Construct the URL for accessing the image
        image_url = f"/{user.name}/{image_filename}"  # Adjust the URL path as needed

        # Get today's record for the user
        current_date = datetime.now(pytz.timezone('Asia/Kolkata')).date()
        get_user_entry = db.query(FinalRecords).filter(
            FinalRecords.user_id == user_id,
            FinalRecords.entry_date == current_date
        ).first()

        if get_user_entry is None:
            raise HTTPException(status_code=404, detail="No record found for today")
        
       
        # Save the image path to the user's record
        get_user_entry.face_image_path = image_path  # Assign the image path to the existing record
        db.commit()
        db.refresh(get_user_entry)

        return {
            "message": "Face captured successfully",
            "image_path": image_url  # Return the URL instead of the file path
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error capturing face: {str(e)}")
        
