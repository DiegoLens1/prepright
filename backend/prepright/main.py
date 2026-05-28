from fastapi import FastAPI
from prepright.routes import app
from prepright.database import init_db

app = app

@app.on_event("startup")
def on_startup():
    init_db()
