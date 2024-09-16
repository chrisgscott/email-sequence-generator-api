from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.db.database import get_db, SessionLocal
from app.core.auth import get_password_hash, verify_password
from app.models.user import User
from app.models.api_key import APIKey
from app.services import user_service
import secrets
from app.services.user_service import send_password_reset_email
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def get_admin_user(request: Request, db: Session = Depends(get_db)):
    email = request.session.get("admin_user")
    if not email:
        raise HTTPException(status_code=302, detail="Not authenticated")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=302, detail="Not authenticated")
    return user

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if user and verify_password(password, user.hashed_password):
        request.session["admin_user"] = user.email
        return RedirectResponse(url="/admin/users", status_code=303)
    return RedirectResponse(url="/admin/login?error=Invalid credentials", status_code=303)

@router.get("/logout")
async def logout(request: Request):
    request.session.pop("admin_user", None)
    return RedirectResponse(url="/admin/login", status_code=302)

@router.get("/users", response_class=HTMLResponse)
async def list_users(request: Request, db: Session = Depends(get_db), admin_user: User = Depends(get_admin_user)):
    users = db.query(User).all()
    return templates.TemplateResponse("users.html", {"request": request, "users": users})

@router.get("/users/create", response_class=HTMLResponse)
async def create_user_form(request: Request, admin_user: str = Depends(get_admin_user)):
    return templates.TemplateResponse("user_form.html", {"request": request, "user": None})

@router.post("/users/create")
async def create_user(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    wordpress_url: str = Form(...),
    wordpress_username: str = Form(...),
    wordpress_password: str = Form(...),
    db: Session = Depends(get_db),
    admin_user: str = Depends(get_admin_user)
):
    user = User(email=email, hashed_password=get_password_hash(password))
    db.add(user)
    db.flush()

    api_key = APIKey(
        key=secrets.token_urlsafe(32),
        user_id=user.id,
        wordpress_url=wordpress_url,
        wordpress_username=wordpress_username,
        wordpress_password=wordpress_password
    )
    db.add(api_key)
    db.commit()

    return RedirectResponse(url="/admin/users", status_code=302)

@router.get("/users/{user_id}/edit", response_class=HTMLResponse)
async def edit_user_form(request: Request, user_id: int, db: Session = Depends(get_db), admin_user: str = Depends(get_admin_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return templates.TemplateResponse("user_form.html", {"request": request, "user": user})

@router.post("/users/{user_id}/edit")
async def edit_user(
    request: Request,
    user_id: int,
    email: str = Form(...),
    password: str = Form(None),
    wordpress_url: str = Form(...),
    wordpress_username: str = Form(...),
    wordpress_password: str = Form(None),
    db: Session = Depends(get_db),
    admin_user: str = Depends(get_admin_user)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.email = email
    if password:
        user.hashed_password = get_password_hash(password)

    if not user.api_key:
        user.api_key = APIKey(key=secrets.token_urlsafe(32), user_id=user.id)

    user.api_key.wordpress_url = wordpress_url
    user.api_key.wordpress_username = wordpress_username
    if wordpress_password:
        user.api_key.wordpress_password = wordpress_password

    db.commit()
    return RedirectResponse(url="/admin/users", status_code=302)

@router.post("/users/{user_id}/delete")
async def delete_user(request: Request, user_id: int, db: Session = Depends(get_db), admin_user: str = Depends(get_admin_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return RedirectResponse(url="/admin/users", status_code=302)

@router.get("/", response_class=HTMLResponse)
async def admin_index(request: Request, admin_user: str = Depends(get_admin_user)):
    return RedirectResponse(url="/admin/users", status_code=303)

@router.get("/users/{user_id}/reset-password", response_class=HTMLResponse)
async def reset_password_form(request: Request, user_id: int, db: Session = Depends(get_db), admin_user: str = Depends(get_admin_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return templates.TemplateResponse("reset_password.html", {"request": request, "user": user})

@router.post("/users/{user_id}/reset-password")
async def reset_password(
    request: Request,
    user_id: int,
    new_password: str = Form(...),
    db: Session = Depends(get_db),
    admin_user: str = Depends(get_admin_user)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = get_password_hash(new_password)
    user.reset_token = None
    user.reset_token_expiry = None
    db.commit()

    return RedirectResponse(url="/admin/users", status_code=302)

@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_form(request: Request):
    return templates.TemplateResponse("forgot_password.html", {"request": request})

@router.post("/forgot-password")
async def forgot_password(request: Request, email: str = Form(...)):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            reset_token = secrets.token_urlsafe(32)
            user.reset_token = reset_token
            user.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
            db.commit()

            try:
                send_password_reset_email(db, user.email, reset_token)
            except Exception as e:
                logger.error(f"Failed to send password reset email to {email}: {str(e)}")
                # Optionally, you can roll back the database changes if the email fails to send
                # db.rollback()
                return templates.TemplateResponse("forgot_password_error.html", {"request": request, "error": "Failed to send reset email. Please try again later."})

        # Always return a success message, even if the email doesn't exist (for security reasons)
        return templates.TemplateResponse("forgot_password_sent.html", {"request": request})
    except Exception as e:
        logger.error(f"Error in forgot_password: {str(e)}")
        return templates.TemplateResponse("forgot_password_error.html", {"request": request, "error": "An unexpected error occurred. Please try again later."})
    finally:
        db.close()

@router.get("/reset-password/{token}", response_class=HTMLResponse)
async def reset_password_form(request: Request, token: str, db: Session = Depends(get_db)):
    with db as session:
        user = session.query(User).filter(User.reset_token == token, User.reset_token_expiry > datetime.utcnow()).first()
        if not user:
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")
        return templates.TemplateResponse("reset_password.html", {"request": request, "token": token})

@router.post("/reset-password/{token}")
async def reset_password(request: Request, token: str, new_password: str = Form(...), db: Session = Depends(get_db)):
    with db as session:
        user = session.query(User).filter(User.reset_token == token, User.reset_token_expiry > datetime.utcnow()).first()
        if not user:
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")

        user.hashed_password = get_password_hash(new_password)
        user.reset_token = None
        user.reset_token_expiry = None
        session.commit()

    return RedirectResponse(url="/admin/login", status_code=302)