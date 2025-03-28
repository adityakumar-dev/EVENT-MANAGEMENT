import os
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from dependencies import get_db, get_current_app_user
import models
from firebase_controller import firebase_controller
from sqlalchemy import func
from datetime import datetime
from fastapi import Form
from utils.security import SecurityHandler
from typing import List
from fastapi import UploadFile
from uuid import uuid4
import pytz  # Ensure pytz is imported

router = APIRouter()
security_handler = SecurityHandler()

async def save_image(image: UploadFile) -> str:
    """Save uploaded image and return the path"""
    os.makedirs("temp_images", exist_ok=True)
    temp_image_path = os.path.join("temp_images", f"temp_{uuid4().hex}_{image.filename}")
    
    await image.seek(0)
    with open(temp_image_path, "wb") as buffer:
        content = await image.read()
        buffer.write(content)
    
    return temp_image_path
@router.post("/scan_qr")
def scan_qr(
    user_id: int = Form(...),
    current_app_user: models.AppUsers = Depends(get_current_app_user),
    db: Session = Depends(get_db)
):
    try:
        # Validate user
        user = db.query(models.User).filter(models.User.user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        current_time = datetime.now(pytz.timezone('Asia/Kolkata'))
        current_date = current_time.date()
        is_any_entry_exist = db.query(models.FinalRecords).filter(
            models.FinalRecords.user_id == user_id,
            # models.FinalRecords.entry_date == current_date
        ).first()

        # Create new time log entry
        new_entry = {
            "arrival": current_time.isoformat(),
            "qr_verified": True,
            "qr_verification_time": current_time.isoformat()
        }

        # Check for existing entry for current date
        existing_record = db.query(models.FinalRecords).filter(
            models.FinalRecords.user_id == user_id,
            models.FinalRecords.entry_date == current_date
        ).first()

        if existing_record:
            # Initialize time_logs if None
            current_logs = existing_record.time_logs or []
            
            # Create new time_logs array with the new entry
            updated_logs = current_logs + [new_entry]
            
            try:
                # Explicitly update the time_logs column
                db.query(models.FinalRecords).filter(
                    models.FinalRecords.user_id == user_id,
                    models.FinalRecords.entry_date == current_date
                ).update(
                    {"time_logs": updated_logs},
                    synchronize_session=False
                )
                
                db.commit()
                print(f"Added new time log to existing record for user {user_id} on {current_date}")
            except Exception as e:
                db.rollback()
                print(f"Error updating existing record: {str(e)}")
                raise HTTPException(status_code=500, detail="Failed to update time logs")
        else:
            # Create new record for the day
            new_record = models.FinalRecords(
                user_id=user_id,
                entry_date=current_date,
                app_user_id=current_app_user.user_id,
                time_logs=[new_entry]
            )
            
            try:
                db.add(new_record)
                db.commit()
                print(f"Created new record for user {user_id} on {current_date}")
            except Exception as e:
                db.rollback()
                print(f"Error creating new record: {str(e)}")
                raise HTTPException(status_code=500, detail="Failed to create new record")

        # Check if face image exists
        is_image_exist = False
        try:
            is_image_exist = existing_record.face_image_path is not None
        except Exception as e:
            print(f"Error checking face image: {str(e)}")

        return {
            "status": "success",
            "message": "Check-in successful",
            "user_id": user_id,
            "arrival_time": current_time.isoformat(),
            "is_image_captured": is_image_exist,
            "entry_type": "new_record" if not existing_record else "updated_record",
            "is_any_entry_exist": True if is_any_entry_exist else False
        }

    except Exception as e:
        db.rollback()
        print(f"Error in scan_qr: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
@router.post("/departure")
def departure(
    user_id: int = Form(...),
    current_app_user: models.AppUsers = Depends(get_current_app_user),
    db: Session = Depends(get_db)
):
    try:
        app_user_id = current_app_user.user_id
        
        # Validate user
        user = db.query(models.User).filter(models.User.user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            # Process single departure for non-instructor
        return process_single_departure(user_id, app_user_id, db)
        
    except Exception as e:
        db.rollback()
        firebase_controller.log_server_activity("ERROR", f"Error processing departure for user_id: {user_id} - {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

def process_single_departure(user_id: int, app_user_id: int, db: Session):
    # Get today's record for the user
    current_date = datetime.now(pytz.timezone('Asia/Kolkata')).date()
    user_record = db.query(models.FinalRecords).filter(
        models.FinalRecords.user_id == user_id,
        models.FinalRecords.entry_date == current_date
    ).first()
    
    if not user_record or not user_record.time_logs:
        raise HTTPException(status_code=404, detail="No active entry found for today")
    
    # Get the latest entry
    latest_entry = user_record.time_logs[-1]
    
    # Check if already departed
    if latest_entry.get('departure') is not None:
        raise HTTPException(status_code=400, detail="Latest entry already has departure time")
    
    # Calculate duration
    arrival_time = datetime.fromisoformat(latest_entry['arrival'])
    departure_time = datetime.now(pytz.timezone('Asia/Kolkata'))
    duration = departure_time - arrival_time
    
    # Update the latest entry
    latest_entry.update({
        'departure': departure_time.isoformat(),
        'duration': str(duration),
        'departure_verified_by': app_user_id,
        'departure_verification_time': departure_time.isoformat()
    })
    
    # Update the entire time_logs array
    user_record.time_logs[-1] = latest_entry
    
    # Update the record in database
    db.query(models.FinalRecords).filter(
        models.FinalRecords.user_id == user_id,
        models.FinalRecords.entry_date == current_date
    ).update({
        "time_logs": user_record.time_logs
    })
    
    db.commit()
    # firebase_controller.log_server_activity("INFO", f"Departure recorded for user_id: {user_id}")
    
    return {
        "message": "Check-out successful",
        "user_id": user_id,
        "departure_time": departure_time.isoformat(),
        "duration": str(duration),
        "entry_type": latest_entry.get('entry_type', 'normal')
    }
