from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict

app = FastAPI()

# Allow requests from frontend/Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development, allows all. Restrict in production.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define your expected input schema
class ProductInfo(BaseModel):
    name: str
    type: str
    color: str
    material: str
    collection: str

class Preferences(BaseModel):
    style: str
    theme: str
    tone: str
    target_audience: str
    platform: str
    tagline_max_words: int

class Constraints(BaseModel):
    color_palette: List[str] = []
    brand_voice: str = ""
    avoid_elements: List[str] = []

class AdRequest(BaseModel):
    product: ProductInfo
    preferences: Preferences
    constraints: Constraints
    reference_images: List[str] = []

@app.post("/api/generate-ad")
async def generate_ad(request: AdRequest):
    # For now, just echo the data back to test integration
    return {
        "ad_text": {
            "headline": f"Promote {request.product.name}",
            "tagline": f"Best {request.product.type} for {request.preferences.target_audience}",
            "body_copy": f"Get the {request.product.color} {request.product.type} made from {request.product.material} in our new {request.product.collection} collection.",
            "cta": "Shop now"
        },
        "image_url": "",  # Later, connect to image API!
        "metadata": {},
        "quality_scores": {}
    }

@app.get("/")
async def root():
    return {"message": "Fashion Ad Generator Backend is running!"}
