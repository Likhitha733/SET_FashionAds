# backend/api/working_tryon.py
# REAL VIRTUAL TRY-ON using Fal.ai (FREE API)

import os
import base64
import requests
from typing import Dict
import logging
import fal_client

logger = logging.getLogger(__name__)

FAL_API_KEY = os.getenv("FAL_API_KEY")  # Get from fal.ai


async def fal_virtual_tryon(
    person_image_b64: str,
    garment_image_b64: str
) -> Dict:
    """
    REAL Virtual Try-On using Fal.ai IDM-VTON
    - Actual AI model, not copy-paste
    - Works with free API key
    - Professional results
    """
    
    try:
        
        
        logger.info("🎨 Starting Fal.ai Virtual Try-On...")
        
        # Decode images to upload
        person_data = base64.b64decode(person_image_b64)
        garment_data = base64.b64decode(garment_image_b64)
        
        # Upload images to Fal
        person_url = fal_client.upload(person_data, "image/jpeg")
        garment_url = fal_client.upload(garment_data, "image/jpeg")
        
        logger.info("📤 Calling IDM-VTON model...")
        
        # Call IDM-VTON
        result = fal_client.subscribe(
            "fal-ai/idm-vton",
            arguments={
                "human_image_url": person_url,
                "garment_image_url": garment_url,
                "category": "upper_body",  # or "lower_body", "dress"
                "num_inference_steps": 30
            }
        )
        
        # Download result
        result_url = result["image"]["url"]
        response = requests.get(result_url)
        result_b64 = base64.b64encode(response.content).decode()
        
        logger.info("✅ Fal.ai try-on successful!")
        
        return {
            "success": True,
            "result_image_b64": result_b64,
            "message": "Virtual try-on completed with Fal.ai IDM-VTON",
            "method": "fal_ai_idm_vton"
        }
    
    except Exception as e:
        logger.error(f"❌ Fal.ai try-on failed: {str(e)}")
        return {
            "success": False,
            "result_image_b64": None,
            "message": f"Error: {str(e)}"
        }


# ========== ALTERNATIVE: Replicate API ==========
async def replicate_virtual_tryon(
    person_image_b64: str,
    garment_image_b64: str
) -> Dict:
    """
    Virtual Try-On using Replicate's IDM-VTON
    """
    
    try:
        import replicate
        
        logger.info("🎨 Starting Replicate Virtual Try-On...")
        
        # Decode images
        person_data = base64.b64decode(person_image_b64)
        garment_data = base64.b64decode(garment_image_b64)
        
        # Create data URIs
        person_uri = f"data:image/jpeg;base64,{person_image_b64}"
        garment_uri = f"data:image/jpeg;base64,{garment_image_b64}"
        
        # Run model
        output = replicate.run(
            "cuuupid/idm-vton:c871bb9b046607b680449ecbae55fd8c6d945e0a1948644bf2361b3d021d3ff4",
            input={
                "human_img": person_uri,
                "garm_img": garment_uri,
                "category": "upper_body"
            }
        )
        
        # Download result
        result_url = output[0] if isinstance(output, list) else output
        response = requests.get(result_url)
        result_b64 = base64.b64encode(response.content).decode()
        
        logger.info("✅ Replicate try-on successful!")
        
        return {
            "success": True,
            "result_image_b64": result_b64,
            "message": "Virtual try-on completed with Replicate IDM-VTON",
            "method": "replicate_idm_vton"
        }
    
    except Exception as e:
        logger.error(f"❌ Replicate try-on failed: {str(e)}")
        return {
            "success": False,
            "result_image_b64": None,
            "message": f"Error: {str(e)}"
        }


# ========== SETUP INSTRUCTIONS ==========
"""
OPTION 1: Fal.ai (Recommended)
1. pip install fal-client
2. Get API key: https://fal.ai/dashboard/keys
3. Add to .env: FAL_API_KEY=your_key_here

OPTION 2: Replicate
1. pip install replicate
2. Get API key: https://replicate.com/account/api-tokens
3. Add to .env: REPLICATE_API_TOKEN=your_key_here
"""
