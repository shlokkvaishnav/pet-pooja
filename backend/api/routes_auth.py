"""
routes_auth.py — Authentication routes for multi-restaurant login
"""
import hashlib
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from models import Restaurant

router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    restaurant_id: int
    restaurant_name: str
    slug: str
    cuisine_type: str | None
    email: str


class RestaurantUpdateRequest(BaseModel):
    restaurant_name: str | None = None
    cuisine_type: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    logo_url: str | None = None


@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """
    POST /api/auth/login
    Validates email + password against the restaurants table.
    Returns restaurant context (id, name, slug, etc.)
    """
    email = (req.email or "").strip().lower()
    if not email or not req.password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    password_hash = hashlib.sha256(req.password.encode()).hexdigest()

    restaurant = db.query(Restaurant).filter(
        Restaurant.email == email,
        Restaurant.password_hash == password_hash,
        Restaurant.is_active == True,
    ).first()

    if not restaurant:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return {
        "restaurant_id": restaurant.id,
        "restaurant_name": restaurant.name,
        "slug": restaurant.slug,
        "cuisine_type": restaurant.cuisine_type,
        "email": restaurant.email,
    }


@router.get("/me/{restaurant_id}")
def get_restaurant(restaurant_id: int, db: Session = Depends(get_db)):
    """
    GET /api/auth/me/{restaurant_id}
    Returns the restaurant profile.
    """
    restaurant = db.query(Restaurant).filter(
        Restaurant.id == restaurant_id,
        Restaurant.is_active == True,
    ).first()

    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    return {
        "restaurant_id": restaurant.id,
        "restaurant_name": restaurant.name,
        "slug": restaurant.slug,
        "cuisine_type": restaurant.cuisine_type,
        "email": restaurant.email,
        "phone": restaurant.phone,
        "address": restaurant.address,
        "logo_url": restaurant.logo_url,
    }


@router.patch("/me/{restaurant_id}")
def update_restaurant(
    restaurant_id: int,
    body: RestaurantUpdateRequest,
    db: Session = Depends(get_db),
):
    restaurant = db.query(Restaurant).filter(
        Restaurant.id == restaurant_id,
        Restaurant.is_active == True,
    ).first()

    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    if body.restaurant_name is not None:
        restaurant.name = body.restaurant_name
    if body.cuisine_type is not None:
        restaurant.cuisine_type = body.cuisine_type
    if body.email is not None:
        restaurant.email = body.email.strip().lower()
    if body.phone is not None:
        restaurant.phone = body.phone
    if body.address is not None:
        restaurant.address = body.address
    if body.logo_url is not None:
        restaurant.logo_url = body.logo_url

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Restaurant profile conflicts with existing records")
    db.refresh(restaurant)

    return {
        "restaurant_id": restaurant.id,
        "restaurant_name": restaurant.name,
        "slug": restaurant.slug,
        "cuisine_type": restaurant.cuisine_type,
        "email": restaurant.email,
        "phone": restaurant.phone,
        "address": restaurant.address,
        "logo_url": restaurant.logo_url,
    }
