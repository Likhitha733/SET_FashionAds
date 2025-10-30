from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import base64
from typing import Optional, List
from backend.utils import error_handler


# Vertex AI - Google Imagen
from vertexai.preview.vision_models import ImageGenerationModel
import vertexai

load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

router = APIRouter()

# Pydantic models for request validation
class ProductInfo(BaseModel):
    name: str = "fashion item"
    type: str = "clothing"
    color: str = ""
    material: str = ""
    collection: str = ""

class Preferences(BaseModel):
    style: str = "modern"
    theme: str = "elegant"
    platform: str = "Instagram"

class ImageGenerationRequest(BaseModel):
    product: ProductInfo
    preferences: Preferences
    negative_prompt: Optional[str] = "low quality, blurry, distorted, ugly, deformed"
    num_images: int = 1

class ImageResponse(BaseModel):
    prompt: str
    images_b64: List[str]
    num_images: int

class SimpleImageRequest(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = "low quality, blurry, distorted"
    num_images: int = 1
    aspect_ratio: str = "1:1"


def create_fashion_prompt(product_info: ProductInfo, preferences: Preferences) -> str:
    """
    Create optimized prompt for fashion ad image generation
    """
    product_name = product_info.name
    product_type = product_info.type
    color = product_info.color
    material = product_info.material
    collection = product_info.collection
    
    style = preferences.style
    theme = preferences.theme
    platform = preferences.platform

    prompt = f"Professional fashion advertisement photo of {product_name}, "
    
    if color:
        prompt += f"{color} "
    if material:
        prompt += f"{material} "
        
    prompt += f"{product_type}, "
    
    if collection:
        prompt += f"{collection} collection, "
    
    prompt += f"{style} style, {theme} theme, "
    prompt += f"high-quality product photography, studio lighting, "
    
    if platform.lower() == "instagram":
        prompt += "square format, Instagram-ready, vibrant colors, "
    elif platform.lower() == "pinterest":
        prompt += "vertical format, Pinterest-style, aesthetic, "
    elif platform.lower() == "facebook":
        prompt += "attention-grabbing, social media optimized, "
    
    prompt += "professional fashion photography, detailed, sharp focus, 4K quality"
    
    return prompt


def generate_fashion_image(
    prompt: str, 
    negative_prompt: str = "", 
    num_images: int = 1,
    aspect_ratio: str = "1:1"
) -> List[str]:
    """
    Generate fashion ad image using Google Imagen via Vertex AI.
    Returns: list of base64 images (as strings).
    """
    try:
        # Initialize Vertex AI
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        
        # Load the Imagen model
        model = ImageGenerationModel.from_pretrained("imagegeneration@006")
        
        # Generate images
        response = model.generate_images(
            prompt=prompt,
            number_of_images=min(num_images, 4),  # Max 4 images per request
            negative_prompt=negative_prompt if negative_prompt else "low quality, blurry, distorted",
            aspect_ratio=aspect_ratio,
            safety_filter_level="block_some",
            person_generation="allow_adult"
        )
        
        # Convert to base64
        images = []
        for image in response.images:
            # Get base64 string
            image_b64 = image._as_base64_string()
            images.append(image_b64)
        
        return images
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Image generation error: {str(e)}"
        )


@router.post("/generate", response_model=ImageResponse)
async def generate_image_endpoint(request: ImageGenerationRequest):
    """
    Generate fashion ad images with automatic prompt engineering
    """
    try:
        # Create optimized prompt
        prompt = create_fashion_prompt(request.product, request.preferences)
        
        # Generate images
        images_b64 = generate_fashion_image(
            prompt=prompt,
            negative_prompt=request.negative_prompt,
            num_images=request.num_images
        )
        
        return ImageResponse(
            prompt=prompt,
            images_b64=images_b64,
            num_images=len(images_b64)
        )
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate images: {str(e)}"
        )


@router.post("/generate-simple")
async def generate_simple_image(request: SimpleImageRequest):
    """
    Generate image from a simple text prompt (for custom use cases)
    """
    try:
        images_b64 = generate_fashion_image(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            num_images=request.num_images,
            aspect_ratio=request.aspect_ratio
        )
        
        return {
            "images_b64": images_b64,
            "num_images": len(images_b64),
            "prompt_used": request.prompt
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Simple image generation failed: {str(e)}"
        )


@router.get("/test")
async def test_imagen_connection():
    """
    Test endpoint to verify Vertex AI Imagen setup
    """
    try:
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        return {
            "status": "success",
            "message": "Vertex AI Imagen is configured correctly",
            "project_id": PROJECT_ID,
            "location": LOCATION
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Vertex AI setup error: {str(e)}"
        )
