# backend/try_on/tryon_server.py
# UPDATED TO USE VERTEX AI IMAGEN

from fastapi import APIRouter, File, UploadFile, HTTPException
import base64
import logging
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.api.vertex_ai_tryon import vertex_ai_virtual_tryon, simple_overlay_tryon

logger = logging.getLogger(__name__)

router = APIRouter()


from backend.api.working_tryon import fal_virtual_tryon

@router.post("/tryon")
async def tryon_endpoint(
    user_photo: UploadFile = File(..., description="Person's photo"),
    product_photo: UploadFile = File(..., description="Garment photo")
):
    # Read uploaded files
    user_bytes = await user_photo.read()
    garment_bytes = await product_photo.read()
    user_b64 = base64.b64encode(user_bytes).decode()
    garment_b64 = base64.b64encode(garment_bytes).decode()

    result = await fal_virtual_tryon(user_b64, garment_b64)

    if result["success"]:
        return {
            "result_image_b64": result["result_image_b64"],
            "message": "Virtual try-on completed successfully",
            "method": "fal_ai_idm_vton"
        }
    else:
        raise HTTPException(status_code=500, detail=result["message"])
