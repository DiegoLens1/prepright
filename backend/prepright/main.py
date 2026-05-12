from fastapi import FastAPI
from prepright.routes import app as routes_app
from prepright.database import init_db

app = routes_app

@app.on_event("startup")
def on_startup():
    init_db()
