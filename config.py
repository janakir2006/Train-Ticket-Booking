import os

class Config:
    # Format: postgresql://username:password@localhost:port/database_name
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:jan1558@localhost:5432/flaskapp'
    SQLALCHEMY_TRACK_MODIFICATIONS = False