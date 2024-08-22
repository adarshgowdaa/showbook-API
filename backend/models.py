from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    username: str = Field(...)
    email: EmailStr = Field(...)
    password: str = Field(...)
    phone: str = Field(...)
    is_admin: Optional[bool] = False 

class UserLogin(BaseModel):
    email: EmailStr = Field(...)
    password: str = Field(...)

class MovieCreate(BaseModel):
    title: str = Field(...)
    genre: str = Field(...)
    rating: float = Field(...)
    duration: int = Field(...)
    release_date: datetime = Field(...) 

class MovieUpdate(BaseModel):
    title: Optional[str] = Field(None)
    genre: Optional[str] = Field(None)
    rating: Optional[float] = Field(None)
    duration: Optional[int] = Field(None)
    release_date: Optional[datetime] = Field(None)

class UserResponse(BaseModel):
    username: str
    email: EmailStr
    phone: str
    is_admin: Optional[bool] 

class CinemaHallCreate(BaseModel):
    name: str
    address: str
    phone: str

class ScreenCreate(BaseModel):
    hall_id: str
    name: str
    total_seats: int

class ShowCreate(BaseModel):
    movie_id: str
    screen_id: str
    show_time: datetime 

class BookingCreate(BaseModel):
    show_id: str
    user_id: str
    seat_number: int

class ShowResponse(BaseModel):
    show_id: str
    movie_id: str
    screen_id: str
    show_time: datetime
    movie_title: Optional[str] = None

class MovieSearchResponse(BaseModel):
    movie_id: str
    title: str
    genre: str
    rating: float
    duration: int
    release_date: datetime