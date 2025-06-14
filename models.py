from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Date, UniqueConstraint
from sqlalchemy.orm import relationship, backref
from datetime import datetime
from database import Base
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
import pytz  # Import pytz for timezone handling

class User(Base):
    __tablename__ = "users"
    
    user_id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    image_path = Column(String)
    id_type = Column(String)
    id = Column(String, nullable=True)
    qr_code = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(pytz.timezone('Asia/Kolkata')))
    group_name = Column(String, nullable=True)
    count = Column(String, nullable=True)


class AppUsers(Base):
    __tablename__ = "app_users"

    user_id = Column(String, primary_key=True, index=True)
    password = Column(String, nullable=False)
    email = Column(String, unique=False, index=True)
    image_path = Column(String,nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(pytz.timezone('Asia/Kolkata')))
    api_key = Column(String, unique=True, nullable=True)
    api_key_expiry = Column(DateTime, nullable=True)

    
class FinalRecords(Base):
    __tablename__ = "final_records"

    record_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), unique=False)
    entry_date = Column(Date, default=datetime.utcnow().date())
    # app_user_id = Column(Integer, ForeignKey("app_users.user_id"), nullable=True)
        
    # Time tracking using JSONB
    time_logs = Column(JSONB, default=list)  # Store array of time entries
    # Example structure:
    # [
    #   {
    #     "arrival": "2024-03-21T09:00:00",
    #     "departure": "2024-03-21T12:00:00",
    #     "duration": "3:00:00",
    #     "entry_type": "normal"  # or "bypass"
    #     "bypass_details": {      # only present if entry_type is "bypass"
    #         "reason": "Face not detected",
    #         "approved_by": "app_user_id"
    #     }
    #   }
    # ]
    
    # Verification timestamps and face image
    face_image_path = Column(String, nullable=True)
    app_user_id = Column(String, ForeignKey("app_users.user_id"), nullable=True)
    
    # Relationship
    # user = relationship("User", back_populates="final_records")

class FoodRecords(Base):
    __tablename__ = "food_records"

    record_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), unique=False)
    entry_date = Column(Date, default=datetime.utcnow().date())
    time_logs = Column(JSONB, default=list)
    created_at = Column(DateTime, default=lambda: datetime.now(pytz.timezone('Asia/Kolkata')))
    
    