from datetime import datetime
from email.header import Header
from fastapi import APIRouter, Depends, HTTPException, File, Form, UploadFile, Query, Header
from sqlalchemy.orm import Session
from dependencies import get_db, get_current_app_user
import models
from utils.file_handlers import save_upload_file, delete_file
from qr_generation import generate_qr_code
import base64
import os
from typing import Optional
import traceback
from fastapi.responses import JSONResponse, FileResponse
from firebase_controller import firebase_controller
from uuid import uuid4
from template_generator import create_visitor_card
from utils.security import SecurityHandler
from fastapi import BackgroundTasks
from pathlib import Path
import mimetypes  # Add this import
from utils.email_handler import send_welcome_email_background
import pytz  # Import the pytz library

router = APIRouter()


@router.post("/check/email/{email}")
def check_email(email: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    return {"exists": bool(user)}

@router.post("/create")
def create_user(
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    email: str = Form(...),
    image: UploadFile = File(...),
    institution_name: str = Form(...),
    contact_number: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        request_data = {
            "name": name,
            "email": email,
            "institution_name": institution_name,
            "contact_number": contact_number,
            "image_filename": image.filename    
        }
        print(f"Creating new user with data: {request_data}")
        
        # Validate image format
        if image.filename.split(".")[-1] not in ["jpg", "jpeg", "png", "webp"]:
            raise HTTPException(status_code=400, detail="Image must be a jpg, jpeg, png, or webp file")
        
        # Check for existing user
        existing_user = db.query(models.User).filter(
            models.User.email == email
        ).first()
        
        if existing_user:
            raise HTTPException(status_code=400, detail="User already exists with this email")

        # Save image
        image_path = save_upload_file(image)
        print(f"Saved image at: {image_path}")

        # Create user with direct institution name
        new_user = models.User(
            name=name,
            email=email,
            image_path=image_path,
            institution_name=institution_name,
            contact_number=contact_number
        )
        
        db.add(new_user)
        db.flush()
        
        print(f"Generated user with ID: {new_user.user_id}")
        
        # Generate QR Code
        qr_path = generate_qr_code(new_user.user_id, new_user.name, new_user.email)
        new_user.qr_code = qr_path
        print(f"Generated QR code at: {qr_path}")
        
        db.commit()
        db.refresh(new_user)
        
        # Generate visitor card
        card_path = create_visitor_card({
            "name": new_user.name,
            "profile_image_path": str(Path(new_user.image_path)),
            "qr_code_path": new_user.qr_code,
            "user_contact": new_user.contact_number,
            "user_id": str(new_user.user_id),
            "institution_name": new_user.institution_name
        })

        print(f"Successfully created user: {new_user.user_id}")

        # Send welcome email in background
        # send_welcome_email_background(
        #     background_tasks=background_tasks,
        #     user_email=new_user.email,
        #     user_name=new_user.name,
        #     qr_code_path=new_user.qr_code,
        #     visitor_card_path=card_path
        # )

        return {
            "user_id": new_user.user_id,
            "name": new_user.name,
            "email": new_user.email,
            "qr_code": new_user.qr_code,
            "image_path": new_user.image_path,
            "institution_name": new_user.institution_name,
            "visitor_card_path": card_path,
            "card_path": card_path,
            "email_status": "sending_in_background"
        }

    except Exception as e:
        db.rollback()
        print(f"Error creating user: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error creating user: {str(e)}")

@router.get("/{user_id}")
def get_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    try:
        user = db.query(models.User).filter(
            models.User.user_id == user_id
        ).first()

        if user:
            # Get all records for the user
            records = db.query(models.FinalRecords).filter(
                models.FinalRecords.user_id == user_id
            ).order_by(models.FinalRecords.entry_date.desc()).all()

            # Process records into a more organized structure
            processed_records = []
            for record in records:
                entry_data = {
                    "record_id": record.record_id,
                    "entry_date": record.entry_date.isoformat(),
                    "face_image_path": record.face_image_path,
                    "app_user_id": record.app_user_id,
                    "entries": []
                }

                if record.time_logs:
                    for log in record.time_logs:
                        # Convert UTC times to IST
                        arrival_time = datetime.fromisoformat(log.get("arrival")) if log.get("arrival") else None
                        departure_time = datetime.fromisoformat(log.get("departure")) if log.get("departure") else None

                        if arrival_time:
                            arrival_time = arrival_time.replace(tzinfo=pytz.UTC).astimezone(pytz.timezone('Asia/Kolkata'))
                        if departure_time:
                            departure_time = departure_time.replace(tzinfo=pytz.UTC).astimezone(pytz.timezone('Asia/Kolkata'))

                        entry = {
                            "arrival": arrival_time.isoformat() if arrival_time else None,
                            "departure": departure_time.isoformat() if departure_time else None,
                            "duration": log.get("duration"),
                            "face_image_path": log.get("face_image_path")
                        }

                        # Add bypass details if present
                        if log.get("bypass_details"):
                            entry["bypass_details"] = log["bypass_details"]



                        entry_data["entries"].append(entry)

                processed_records.append(entry_data)

            # Get the count of users associated with the instructor's institution
           
            response_data = {
                "user": {
                    "user_id": user.user_id,
                    "name": user.name,
                    "email": user.email,
                    "institution_name": user.institution_name,
                    "image_path": f"{user.image_path}",
                    "qr_code_path": f"{user.qr_code}",
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                },
                "entry_records": processed_records,
                "summary": {
                    "total_days": len(processed_records),
                    "total_entries": sum(len(record["entries"]) for record in processed_records),
                  
                   
                },
                "image_base64": None,
                "qr_base64": None
            }

            # Add base64 encoded images
            try:
                if user.qr_code and os.path.exists(user.qr_code):
                    with open(user.qr_code, "rb") as qr_file:
                        qr_data = base64.b64encode(qr_file.read()).decode()
                        response_data["qr_base64"] = f"data:image/png;base64,{qr_data}"
            except Exception as qr_error:
                print(f"Error processing QR code: {str(qr_error)}")

            try:
                if user.image_path and os.path.exists(user.image_path):
                    with open(user.image_path, "rb") as img_file:
                        img_data = base64.b64encode(img_file.read()).decode()
                        response_data["image_base64"] = f"data:image/jpeg;base64,{img_data}"
            except Exception as img_error:
                print(f"Error processing image: {str(img_error)}")

            return response_data
        else:
            raise HTTPException(status_code=404, detail="User not found")

    except Exception as e:
        print(f"Error in get_user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/all")
def get_all_users(
    user_type: str = Query(None),
    institution_name: str = Query(None),  # Optional filter by institution name
    db: Session = Depends(get_db)
):
    try:
        current_date = datetime.now(pytz.timezone('Asia/Kolkata')).date()
        current_time = datetime.now(pytz.timezone('Asia/Kolkata'))
        
        response = {
            "all_users": [],
            "individual": [],
            "statistics": {
                "total_users": 0,
                "total_individual": 0,
            },
            "today_statistics": {
                "active_entries": 0,
                "total_entries": 0,
                "active_individual": 0,
            },
        }
        
        # Build query with optional institution filter
        query = db.query(models.User)
        if institution_name:
            query = query.filter(models.User.institution_name == institution_name)
        
        users = query.all()

        for user in users:
            # Get today's records for the user
            final_records = db.query(models.FinalRecords).filter(
                models.FinalRecords.user_id == user.user_id,
                models.FinalRecords.entry_date == current_date
            ).all()
            
            # Initialize current entry details
            current_entry = {
                "is_active": False,
                "arrival_time": None,
                "duration_minutes": 0,
                "entry_id": None,
                "qr_verified": False,
            }
            
            # Process user records
            for record in final_records:
                if record.time_logs:
                    for log in record.time_logs:
                        if log.get('arrival') and not log.get('departure'):
                            arrival_time = datetime.fromisoformat(log['arrival']).replace(tzinfo=pytz.timezone('Asia/Kolkata'))
                            duration = (current_time - arrival_time).total_seconds() / 60
                            
                            current_entry.update({
                                "is_active": True,
                                "arrival_time": log['arrival'],
                                "duration_minutes": round(duration, 2),
                                "entry_id": record.record_id,
                                "qr_verified": log.get('qr_verified', False),
                            })
                            
                            response["today_statistics"]["active_entries"] += 1
                            response["today_statistics"]["active_individual"] += 1

            user_data = {
                "id": user.user_id,
                "name": user.name,
                "email": user.email,
                "image_path": user.image_path,
                "institution_name": user.institution_name,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "current_entry": current_entry
            }

            response["all_users"].append(user_data)
            response["individual"].append(user_data)
            response["statistics"]["total_individual"] += 1
            response["today_statistics"]["total_entries"] += sum(
                len(record.time_logs) for record in final_records
            )

        response["statistics"]["total_users"] = len(users)

        # Sort users by active status and creation date
        for key in ["all_users", "individual"]:
            response[key] = sorted(
                response[key],
                key=lambda x: (not x["current_entry"]["is_active"], x["created_at"] if x["created_at"] else "0"),
                reverse=False
            )

        return {
            "status": "success",
            "message": "Users fetched successfully",
            "data": response,
            "timestamp": current_time.isoformat()
        }

    except Exception as e:
        print(f"Error fetching users: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching users: {str(e)}"
        )

# from fastapi import Query

@router.get("/download-visitor-card/")
async def download_visitor_card(
    card_path: str = Query(..., description="Path of the visitor card file"),
):

    try:
        # Print debug info
        print(f"Requested card path: {card_path}")
        print(f"File exists check: {os.path.exists(card_path)}")
        
        if not os.path.exists(card_path):
            raise HTTPException(
                status_code=404, 
                detail=f"File not found at path: {card_path}"
            )
        
        return FileResponse(
            path=card_path,
            filename=os.path.basename(card_path),
            media_type='image/png'  # Set specific media type for PNG
        )
    except Exception as e:
        print(f"Error serving file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

