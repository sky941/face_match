from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, select, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
import face_recognition
from datetime import datetime
import numpy as np
import cv2
import io

# Initialize FastAPI appß
app = FastAPI()

# Database configuration
DATABASE_URL = "mysql+pymysql://root:Root%40123@127.0.0.1/face_recognition"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define table structure (assuming a table named 'users' exists with 'id', 'name', and 'face_encoding')
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    face_encoding = Column(String(2000), nullable=False)  # Face encodings stored as a serialized string
    attendances = relationship("Attendance", back_populates="user")

    # Define Attendance table
class Attendance(Base):
    __tablename__ = 'attendance'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    match_time = Column(DateTime, default=datetime.utcnow)
    address = Column(String(255), nullable=True)
    image_path = Column(String(255), nullable=True)
    user = relationship("User", back_populates="attendances")

# Create the table if it doesn't exist
Base.metadata.create_all(bind=engine)

# Function to get face encoding from uploaded image
def get_face_encoding(file: UploadFile):
    try:
        image = np.array(cv2.imdecode(np.frombuffer(file.file.read(), np.uint8), cv2.IMREAD_COLOR))
        face_locations = face_recognition.face_locations(image)
        if not face_locations:
            raise ValueError("No face detected in the image.")
        face_encoding = face_recognition.face_encodings(image, face_locations)[0]
        return face_encoding
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing image: {str(e)}")

# Route to upload image and match with stored faces
@app.post("/match-face/")
async def match_face(file: UploadFile = File(...), address: str = Form(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")

    try:
        # Get uploaded image's face encoding
        uploaded_face_encoding = get_face_encoding(file)

        # Save image locally for record
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        image_path = f"uploads/matched_{timestamp}.jpg"
        with open(image_path, "wb") as buffer:
            buffer.write(file.file.read())

        # Fetch all stored face encodings from the database
        session = SessionLocal()
        users = session.query(User).all()

        # Compare uploaded face with stored faces
        for user in users:
            stored_face_encoding = np.array(eval(user.face_encoding))  # Deserialize face encoding
            match = face_recognition.compare_faces([stored_face_encoding], uploaded_face_encoding)[0]
            if match:
                # Save attendance data
                attendance = Attendance(user_id=user.id, address=address, image_path=image_path)
                session.add(attendance)
                session.commit()

                return JSONResponse(content={
                    "id": user.id,
                    "name": user.name,
                    "match": True,
                    "address": address,
                    "match_time": attendance.match_time.isoformat(),
                    "image_path": image_path
                })

        return JSONResponse(content={"match": False, "message": "No matching face found."})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
    finally:
        session.close()

# Route to add a new face to the database
@app.post("/add-face/")
async def add_face(name: str = Form(...), file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")

    try:
        # Get face encoding from the uploaded image
        face_encoding = get_face_encoding(file)

        # Serialize encoding to store in database
        face_encoding_str = str(face_encoding.tolist())

        # Insert into database
        session = SessionLocal()
        new_user = User(name=name, face_encoding=face_encoding_str)
        session.add(new_user)
        session.commit()

        return JSONResponse(content={"message": "Face added successfully!"})

    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
    finally:
        session.close()

        # Route to get all users with their attendance details
@app.get("/users-with-attendance/")
def get_users_with_attendance():
    try:
        session = SessionLocal()
        users = session.query(User).all()

        response = []
        for user in users:
            attendance_records = []
            for attendance in user.attendances:
                attendance_records.append({
                    "match_time": attendance.match_time.isoformat(),
                    "address": attendance.address,
                    "image_path": attendance.image_path
                })

            response.append({
                "id": user.id,
                "name": user.name,
                "attendance": attendance_records
            })

        return JSONResponse(content=response)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
    finally:
        session.close()

# Route to initialize the database
@app.get("/initialize-database/")
def initialize_database():
    try:
        # Create the users table if it doesn't exist
        Base.metadata.create_all(bind=engine)
        return JSONResponse(content={"message": "Database initialized successfully!"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error initializing database: {str(e)}")