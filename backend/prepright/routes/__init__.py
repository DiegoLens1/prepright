from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prepright.settings import get_cors_origins
from prepright.routes import categories, ingredients, products, recipes, events, settings, receipts, predictions, templates, print_orders

app = FastAPI(title="PrepRight", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(categories.router)
app.include_router(ingredients.router)
app.include_router(products.router)
app.include_router(recipes.router)
app.include_router(events.router)
app.include_router(settings.router)
app.include_router(receipts.router)
app.include_router(predictions.router)
app.include_router(templates.router)
app.include_router(print_orders.router)
