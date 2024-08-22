from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import List, Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, date
import models
import database
from bson import ObjectId
from dotenv import load_dotenv
import os


load_dotenv()


SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

app = FastAPI()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_user(email: str):
    user = await database.users_collection.find_one({"email": email})
    if user:
        return user
    return None

async def authenticate_user(email: str, password: str):
    user = await get_user(email)
    if not user:
        return False
    if not verify_password(password, user["password"]):
        return False
    return user

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        user = await get_user(email=email)
        if user is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return user

async def is_admin_user(user: dict = Depends(get_current_user)):
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return user

@app.post("/api/signup", response_model=models.UserResponse)
async def create_user(user: models.UserCreate):
    user_dict = user.dict()
    user_dict["password"] = get_password_hash(user_dict["password"])
    await database.users_collection.insert_one(user_dict)
    user_dict.pop("password")
    return models.UserResponse(**user_dict)

@app.post("/token", response_model=dict)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["email"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}



@app.post("/api/cinemahalls", response_model=models.CinemaHallCreate, dependencies=[Depends(is_admin_user)])
async def create_cinema_hall(hall: models.CinemaHallCreate):
    hall_dict = hall.dict()
    await database.cinema_halls_collection.insert_one(hall_dict)
    return hall_dict



@app.post("/api/screens", response_model=models.ScreenCreate, dependencies=[Depends(is_admin_user)])
async def create_screen(screen: models.ScreenCreate):
    screen_dict = screen.dict()
    await database.screens_collection.insert_one(screen_dict)
    return screen_dict



@app.post("/api/shows", response_model=models.ShowCreate, dependencies=[Depends(is_admin_user)])
async def create_show(show: models.ShowCreate):
    show_dict = show.dict()
    await database.shows_collection.insert_one(show_dict)
    return show_dict



@app.post("/api/movies", response_model=models.MovieCreate, dependencies=[Depends(is_admin_user)])
async def create_movie(movie: models.MovieCreate, current_user: dict = Depends(get_current_user)):
    movie_dict = movie.dict()
    await database.movies_collection.insert_one(movie_dict)
    return movie_dict

@app.get("/api/movies/{id}", response_model=models.MovieCreate)
async def read_movie(id: str, current_user: dict = Depends(get_current_user)):
    movie = await database.movies_collection.find_one({"_id": ObjectId(id)})
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return models.MovieCreate(**movie)

@app.put("/api/movies/{id}", response_model=dict, dependencies=[Depends(is_admin_user)])
async def update_movie(id: str, movie: models.MovieUpdate, current_user: dict = Depends(get_current_user)):
    movie_dict = movie.dict(exclude_unset=True)
    update_result = await database.movies_collection.update_one({"_id": ObjectId(id)}, {"$set": movie_dict})
    if not update_result.matched_count:
        raise HTTPException(status_code=404, detail="Movie not found")
    return {"message": "Movie updated"}

@app.delete("/api/movies/{id}", response_model=dict, dependencies=[Depends(is_admin_user)])
async def delete_movie(id: str, current_user: dict = Depends(get_current_user)):
    delete_result = await database.movies_collection.delete_one({"_id": ObjectId(id)})
    if not delete_result.deleted_count:
        raise HTTPException(status_code=404, detail="Movie not found")
    
    await database.shows_collection.delete_many({"movie_id": id})

    return {"message": "Movie and related shows deleted"}

@app.get("/api/movies", response_model=List[models.MovieSearchResponse])
async def search_movies(title: str = None, genre: str = None, rating: float = None, current_user: dict = Depends(get_current_user)):
    query = {}
    if title:
        query["title"] = {"$regex": title, "$options": "i"} 
    if genre:
        query["genre"] = genre
    if rating:
        query["rating"] = {"$gte": rating} if rating >= 4 else rating

    movies = await database.movies_collection.find(query).to_list(length=100)
    return [models.MovieSearchResponse(movie_id=str(movie["_id"]), **movie) for movie in movies]



@app.get("/api/shows", response_model=List[models.ShowResponse])
async def search_shows(movie_id: str = None, show_time: Optional[date] = None, current_user: dict = Depends(get_current_user)):
    query = {}
    if movie_id:
        query["movie_id"] = movie_id
    if show_time:
        start_of_day = datetime.combine(show_time, datetime.min.time())
        end_of_day = datetime.combine(show_time, datetime.max.time())
        query["show_time"] = {"$gte": start_of_day, "$lt": end_of_day}

    shows = await database.shows_collection.find(query).to_list(length=100)

    shows_with_titles = []
    for show in shows:
        movie = await database.movies_collection.find_one({"_id": ObjectId(show["movie_id"])})
        show["movie_title"] = movie["title"] if movie else None
        shows_with_titles.append(models.ShowResponse(show_id=str(show["_id"]), **show))

    return shows_with_titles



@app.post("/api/bookings", response_model=dict)
async def create_booking(booking: models.BookingCreate, current_user: dict = Depends(get_current_user)):
    booking_dict = booking.dict()
    booking_dict['user_id'] = str(current_user['_id'])

    result = await database.bookings_collection.find_one_and_update(
        {"show_id": booking_dict["show_id"], "seat_number": booking_dict["seat_number"]},
        {"$setOnInsert": booking_dict},
        upsert=True,
        return_document=False  
    )
    
    if result is not None:
        raise HTTPException(status_code=400, detail="Seat already booked")
    
    return {"message": "Booking successful"}