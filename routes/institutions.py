import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from dependencies import get_db
import models

router = APIRouter()

@router.post("/login_url")
def get_login_url(
    admin_name: str = Form(...),
    admin_password: str = Form(...),
    db: Session = Depends(get_db)
):
    if admin_name == os.getenv("ADMIN_NAME") and admin_password == os.getenv("ADMIN_PASSWORD"):
        key = str(uuid.uuid4())

        # Create a new LoginUrlKey instance
        login_url_key = models.LoginUrlKey(key=key)

        # Add the instance to the session
        db.add(login_url_key)
        db.commit()  # Commit to persist the instance

        # Refresh the instance to get the updated state
        db.refresh(login_url_key)

        return key
    else:
        raise HTTPException(status_code=401, detail="Invalid admin credentials")

@router.post("/")
def add_institutions(
    name: str = Form(...),
    address: str = Form(...),
    contact_number: str = Form(...),
    email: str = Form(...),
    key: str = Form(...),
    login_id: str = Form(...),
    password: str = Form(...),
    count: int = Form(...),
    db: Session = Depends(get_db)
):
    # Debug: Print incoming data
    print(f"Adding institution with name: {name} and count: {count} and key: {key} and address: {address} and contact_number: {contact_number} and email: {email}")

    # Check if the institution already exists
    existing_institution = db.query(models.Institution).filter(models.Institution.name == name).first()
    if existing_institution:
        raise HTTPException(status_code=400, detail="Institution already exists")
    
    search_key = db.query(models.LoginUrlKey).filter(models.LoginUrlKey.key == key).first()
    if search_key is None:
        raise HTTPException(status_code=400, detail="Invalid key")
    if search_key.is_used:
        raise HTTPException(status_code=400, detail="Key already used")
    
    is_id_exist = db.query(models.InstitutionLogin).filter(models.InstitutionLogin.login_id == login_id).first()
    if is_id_exist is not None:
        raise HTTPException(status_code=400, detail="Login id already exists")
    
    # Create a new institution
    new_institution = models.Institution(name=name, count=str(count), address=address, contact_number=contact_number, email=email)
    
    # Add the new institution to the session
    db.add(new_institution)
    
    # Commit to persist the new institution and get its ID
    db.commit()
    db.refresh(new_institution)  # Refresh to get the new institution's ID

    # Create the institution login with the key as the login_id
    institution_login = models.InstitutionLogin(institution_id=new_institution.institution_id, login_id=login_id, password=password)
    
    # Mark the key as used
    search_key.is_used = True
    
    # Add the institution login to the session
    db.add(institution_login)

    try:
        db.commit()  # Commit to persist the institution login
        db.refresh(institution_login)  # Refresh to get the updated state
        db.refresh(search_key)  # Refresh the search key if needed
    except Exception as e:
        db.rollback()  # Rollback in case of error
        print(f"Error adding institution: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to add institution")

    return {
        "message": "Institution added successfully",
        "institution": {
            "id": new_institution.institution_id,
            "name": new_institution.name,
            "count": new_institution.count,
            "address": new_institution.address,
            "contact_number": new_institution.contact_number,
            "email": new_institution.email
        }
    }
@router.get("/")
def get_institutions(db: Session = Depends(get_db)):
    print("Getting institutions")
    response = db.query(models.Institution).all()
    return response

@router.get("/credentials")
def get_credentials(institution_id: int, db: Session = Depends(get_db)):
    institution = db.query(models.Institution).filter(models.Institution.institution_id == institution_id).first()
    if institution is None:
        raise HTTPException(status_code=400, detail="Invalid institution ID")
    institution_login = db.query(models.InstitutionLogin).filter(models.InstitutionLogin.institution_id == institution_id).first()
    if institution_login is None:
        raise HTTPException(status_code=400, detail="Invalid institution ID")
    return {
        "password": institution_login.password,
        "institution_id": institution_id
    }
@router.post("/enable_login")
def enable_login(
    admin_name: str = Form(...),
    admin_password: str = Form(...),
    institution_id: int = Form(...),
    db: Session = Depends(get_db)):
    if admin_name == "admin" and admin_password == "future_scope":
        institution = db.query(models.Institution).filter(models.Institution.institution_id == institution_id).first()
        if institution is None:
            raise HTTPException(status_code=400, detail="Invalid institution ID")
        institution_login = db.query(models.InstitutionLogin).filter(models.InstitutionLogin.institution_id == institution_id).first()
        if institution_login is None:
            raise HTTPException(status_code=400, detail="Invalid institution ID")
        institution_login.is_login_enabled = True
        db.commit()
        return {"message": "one time Login enabled successfully"}
    else:
        raise HTTPException(status_code=400, detail="Invalid admin credentials")