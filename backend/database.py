from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("MONGODB_URL")

client = AsyncIOMotorClient(DATABASE_URL)
db = client.movie_booking
users_collection = db.get_collection("users")
movies_collection = db.get_collection("movies")
cinema_halls_collection = db.get_collection("cinema_halls")
screens_collection = db.get_collection("screens")
shows_collection = db.get_collection("shows")
bookings_collection = db.get_collection("bookings")