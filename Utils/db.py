from mongoengine import connect
import os

def connect_to_db():
    try:
        connect(
            db=os.getenv('MONGO_DB_NAME'),
            host=os.getenv('MONGO_URI')
        )
        print("Connected to MongoDB")
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")



