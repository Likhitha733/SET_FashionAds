from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from backend.db.database import get_db
import backend.api.analytics_service as analytics_service
from backend.utils import error_handler
  # keep analytics logic here

router = APIRouter()

@router.get("/my-analytics", description="Get current user's ad analytics summary.")
def get_my_analytics(user_id: int = Query(...), db: Session = Depends(get_db)):
    try:
        summary = analytics_service.get_user_analytics_summary(user_id, db)
        return {"analytics_summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics summary failed: {str(e)}")

@router.get("/ads/{ad_id}/analytics", description="Get analytics for a specific ad.")
def get_ad_analytics(ad_id: int, db: Session = Depends(get_db)):
    try:
        stats = analytics_service.get_ad_analytics(ad_id, db)
        return {"stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ad analytics failed: {str(e)}")

@router.post("/ads/{ad_id}/view", description="Record a view for a specific ad.")
def record_ad_view(ad_id: int, db: Session = Depends(get_db)):
    try:
        analytics_service.record_ad_view(ad_id, db)
        return {"message": "View recorded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"View record failed: {str(e)}")

@router.post("/ads/{ad_id}/click", description="Record a click for a specific ad.")
def record_ad_click(ad_id: int, db: Session = Depends(get_db)):
    try:
        analytics_service.record_ad_click(ad_id, db)
        return {"message": "Click recorded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Click record failed: {str(e)}")

@router.post("/ads/{ad_id}/conversion", description="Record a conversion for a specific ad.")
def record_ad_conversion(ad_id: int, db: Session = Depends(get_db)):
    try:
        analytics_service.record_ad_conversion(ad_id, db)
        return {"message": "Conversion recorded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion record failed: {str(e)}")
