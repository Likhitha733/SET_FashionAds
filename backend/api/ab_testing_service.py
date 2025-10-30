from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.db.database import get_db
import backend.api.ab_testing_service as ab_testing_service  # Logic only!

router = APIRouter()

class ABTestRequest(BaseModel):
    product: dict
    preferences: dict
    num_variants: int = 3
    variation_type: str = "tone"

@router.post("/generate", description="Generate AB test ad variants.")
def generate_ab_variants_ab_router(
    request: ABTestRequest, 
    db: Session = Depends(get_db)
):
    try:
        ad_list = ab_testing_service.generate_ab_variants(request.product, request.preferences, request.num_variants, request.variation_type)
        return {"ab_variants": ad_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AB testing failed: {str(e)}")
