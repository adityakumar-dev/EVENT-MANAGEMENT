from datetime import datetime
import fastapi
from fastapi import Depends, HTTPException, UploadFile, File, Form
import models
from sqlalchemy.orm import Session
from models import FoodRecords, User, FinalRecords
from dependencies import get_db, get_current_app_user
import os
import uuid
import pytz

router = fastapi.APIRouter()

@router.post("/food/add")
async def food(
    user_id: str = Form(...),
    food_type: str = Form(...),
    current_app_user: models.AppUsers  = Depends(get_current_app_user),
    db: Session = Depends(get_db)
):
    try:
        # Validate food type
        if food_type not in ["breakfast", "lunch", "dinner"]:
            raise HTTPException(status_code=400, detail="Invalid food type")
        
        # Get the user
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        current_time = datetime.now(pytz.timezone('Asia/Kolkata'))
        current_date = current_time.date()

        # Check for existing record for today
        existing_record = db.query(FoodRecords).filter(
            FoodRecords.user_id == user_id,
            FoodRecords.entry_date == current_date
        ).first()

        # Create new food log entry
        new_log = {
            "food_type": food_type,
            "time": current_time.isoformat()
        }

        if existing_record:
            # Check if this food type already exists for today
            if any(log["food_type"] == food_type for log in existing_record.time_logs):
                raise HTTPException(
                    status_code=400,
                    detail=f"{food_type.capitalize()} already recorded for today"
                )
            records = existing_record.time_logs
            records.append(new_log)
            print(records)
            # Append new food log to existing record
            db.query(FoodRecords).filter(FoodRecords.user_id == user_id, FoodRecords.entry_date == current_date).update({FoodRecords.time_logs: records})
            db.commit()
        else:
            # Create new record with initial food log
            new_record = FoodRecords(
                user_id=user_id,
                entry_date=current_date,
                time_logs=[new_log],
                created_at=current_time
            )
            db.add(new_record)
            db.commit()

        return {
            "status": "success",
            "message": f"{food_type.capitalize()} record added successfully",
            "data": {
                "user_id": user_id,
                "food_type": food_type,
                "date": current_date.isoformat(),
                "time": current_time.isoformat(),
                "log_entry": new_log
            }
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        print(f"Error adding food record: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error adding food record: {str(e)}")

@router.get("/food/{user_id}")
async def get_food_records(
    user_id: str,
    db: Session = Depends(get_db)
):
    try:
        # Get today's record
        current_date = datetime.now(pytz.timezone('Asia/Kolkata')).date()
        
        food_record = db.query(FoodRecords).filter(
            FoodRecords.user_id == user_id,
            FoodRecords.entry_date == current_date
        ).first()

        if not food_record:
            return {
                "status": "success",
                "data": {
                    "date": current_date.isoformat(),
                    "meals": []
                }
            }

        return {
            "status": "success",
            "data": {
                "date": current_date.isoformat(),
                "meals": food_record.time_logs
            }
        }

    except Exception as e:
        print(f"Error fetching food records: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching food records: {str(e)}"
        )
