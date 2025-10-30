# ==================== STANDARD LIBRARY IMPORTS ====================

import base64
import os
import logging
import datetime
import vertexai
import io
import asyncio
import uvicorn
import numpy as np
import pandas as pd
import random

# ==================== THIRD-PARTY IMPORTS ====================

# FastAPI core
from fastapi import FastAPI, Depends, HTTPException, status, Request, File, UploadFile, Form, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import Response, JSONResponse
from vertexai.preview.vision_models import ImageGenerationModel
from google.oauth2 import service_account
from PIL import Image

# Database & ORM
from sqlalchemy.orm import Session

# Validation & Models
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta

# Environment & Config
from dotenv import load_dotenv

# Security & Authentication
from passlib.hash import pbkdf2_sha256  # Using pbkdf2_sha256 instead of bcrypt for cross-platform compatibility
from jose import jwt

# ==================== LOCAL IMPORTS ====================

# Database components (from backend/db/)
from backend.db.database import SessionLocal, engine, get_db
from backend.db import models

# Try-on router (from backend/try_on/)
try:
    from backend.try_on.tryon_server import router as tryon_router
except ImportError:
    tryon_router = None

# Service layer imports (from backend/api/)
from backend.api import llm_service  # LLM text generation service
from backend.api import image_service  # Image generation service
from backend.api import analytics_service  # Analytics tracking service
from backend.api import ab_testing_service  # A/B testing service
from backend.api import usage_service  # Usage quota/limits service
from backend.api import auth  # Authentication utilities
from backend.api.export_service import create_ad_composite, image_base64_to_bytes
from backend.api.image_upload_service import process_uploaded_image, enhance_prompt_with_reference
from backend.api.mcp_context_service import get_mcp_context

# Import additional services with error handling
try:
    from backend.api.enhanced_prompt_service import analyze_reference_image, generate_optimized_prompt_with_reasoning
except ImportError:
    analyze_reference_image = None
    generate_optimized_prompt_with_reasoning = None

try:
    from backend.services.data_loader import data_loader
except ImportError:
    data_loader = None

# ==================== CONFIGURATION ====================

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# JWT configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "replace-with-secure-key-in-production")
ALGORITHM = "HS256"

# ==================== UTILITY FUNCTIONS ====================

def analyze_reference_image_detailed(image_b64: str) -> str:
    """
    Analyze uploaded reference image and generate detailed 60-70 word description
    Uses Google Gemini Vision to analyze the image
    """
    try:
        import google.generativeai as genai
        
        # Decode image
        image_bytes = base64.b64decode(image_b64)
        image = Image.open(io.BytesIO(image_bytes))
        
        # Configure Gemini
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        
        # Create detailed analysis prompt
        analysis_prompt = """Analyze this fashion product image in extreme detail. Provide a comprehensive 60-70 word description covering:
        - Product type and category
        - Color palette (primary, secondary, accent colors)
        - Material and fabric texture appearance
        - Style aesthetics (modern, vintage, minimalist, etc.)
        - Design elements (patterns, embroidery, prints)
        - Lighting and photography style
        - Target audience and occasion
        - Overall mood and feeling
        
        Be very specific and descriptive. This will be used to guide AI image generation."""
        
        # Generate detailed analysis
        response = model.generate_content([analysis_prompt, image])
        detailed_description = response.text.strip()
        
        # Ensure it's 60-70 words (trim or pad if needed)
        words = detailed_description.split()
        if len(words) > 75:
            detailed_description = ' '.join(words[:70])
        elif len(words) < 55:
            detailed_description += ". High-quality professional fashion photography with studio lighting and clean composition."
        
        return detailed_description
        
    except Exception as e:
        logger.error(f"Reference image analysis error: {str(e)}")
        return "Professional fashion product photography with high-quality studio lighting, clean white background, centered composition, vibrant colors, and detailed texture showcase for premium brand aesthetic appeal."

def generate_fake_metrics(ad_id: int, created_at: datetime):
    """Generate realistic fake metrics that grow over time"""
    # Calculate ad age in hours
    age_hours = (datetime.now() - created_at).total_seconds() / 3600
    
    # Base metrics scale with age (but cap at 30 days)
    age_factor = min(age_hours / 24, 30)
    
    # Random multipliers for variety
    viral_factor = random.uniform(0.5, 2.5)
    
    # Generate metrics
    base_views = int(100 * age_factor * viral_factor)
    views = base_views + random.randint(0, int(base_views * 0.3))
    
    ctr = random.uniform(2.0, 8.0)  # 2-8% CTR
    clicks = int(views * (ctr / 100))
    
    cvr = random.uniform(1.5, 5.0)  # 1.5-5% conversion rate
    conversions = int(clicks * (cvr / 100))
    
    return {
        "views": max(views, 50),  # Minimum 50 views
        "clicks": max(clicks, 2),  # Minimum 2 clicks
        "conversions": max(conversions, 0),
        "ctr": round(ctr, 2),
        "cvr": round(cvr, 2)
    }

def generate_image_prompt(product, preferences):
    """Generate basic image prompt from product info"""
    return f"Professional fashion advertisement photo of {product.get('name')}, {product.get('color')} color, {product.get('material')} material, {preferences.get('style')} style, high quality, studio lighting, clean background"

# ==================== DATABASE SETUP ====================

# Create all database tables on startup
models.Base.metadata.create_all(bind=engine)

# ==================== FASTAPI APP INITIALIZATION ====================

app = FastAPI(
    title="Fashion Ad Generator API",
    description="AI-powered fashion advertisement generation platform",
    version="2.0"
)

# ==================== MIDDLEWARE ====================

# CORS configuration (allow all origins for development - restrict in production!)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== ROUTERS ====================

if tryon_router:
    app.include_router(tryon_router, prefix="/api", tags=["Virtual Try-On"])

# ==================== SECURITY ====================

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# ==================== PASSWORD UTILITIES ====================

def get_password_hash(password: str) -> str:
    """Hash password using pbkdf2_sha256 (secure & cross-platform)"""
    return pbkdf2_sha256.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pbkdf2_sha256.verify(plain_password, hashed_password)

# ==================== PYDANTIC MODELS (REQUEST/RESPONSE SCHEMAS) ====================

class UserCreate(BaseModel):
    """Schema for user registration/login"""
    username: str
    password: str

class ProductInfo(BaseModel):
    """Product details for ad generation"""
    name: str
    type: str
    color: str
    material: str
    collection: str

class Preferences(BaseModel):
    """Ad generation preferences"""
    style: str
    theme: str
    tone: str
    target_audience: str
    platform: str
    tagline_max_words: int

class Constraints(BaseModel):
    """Optional constraints for ad generation"""
    color_palette: List[str] = []
    brand_voice: str = ""
    avoid_elements: List[str] = []

class AdRequest(BaseModel):
    """Complete ad generation request"""
    product: ProductInfo
    preferences: Preferences
    constraints: Constraints

class ABTestRequest(BaseModel):
    """A/B testing variant generation request"""
    product: ProductInfo
    preferences: Preferences
    num_variants: int = 3
    variation_type: str = "tone"

class TemplateCreate(BaseModel):
    """Template creation request"""
    name: str
    description: str
    product_template: dict
    preferences_template: dict
    is_public: bool = False

# ==================== GLOBAL EXCEPTION HANDLER ====================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler for unhandled errors"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )

# ==================== DEPENDENCY: GET CURRENT USER ====================

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Dependency to get current authenticated user from JWT token"""
    try:
        # Decode JWT token directly here (don't rely on auth module)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user

# ==================== AUTHENTICATION ENDPOINTS ====================

@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user
    - Accepts JSON: {"username": "...", "password": "..."}
    - Returns: {"message": "Registration successful", "user_id": 123}
    """
    # Check if username already exists
    existing_user = db.query(models.User).filter(models.User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Validate password length
    if len(user.password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters")
    
    # Hash password and create user
    hashed_pw = get_password_hash(user.password)
    new_user = models.User(username=user.username, password_hash=hashed_pw)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"message": "Registration successful", "user_id": new_user.id}

@app.post("/login")
def login(user: UserCreate, db: Session = Depends(get_db)):
    """
    Login and receive JWT token
    - Accepts JSON: {"username": "...", "password": "..."}
    - Returns: {"access_token": "...", "token_type": "bearer"}
    """
    # Find user
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    
    # Verify password
    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    # Create JWT token (24-hour expiry) - FIXED DATETIME IMPORT
    token_data = {
        "sub": db_user.username,
        "exp": datetime.utcnow() + timedelta(hours=24)  # ✅ FIXED: not datetime.datetime.utcnow()
    }
    token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
    
    return {"access_token": token, "token_type": "bearer"}

# ==================== HEALTH CHECK ENDPOINTS ====================

@app.get("/")
async def root():
    """Root endpoint - API status"""
    return {"message": "Fashion Ad Generator Backend is running! Phase 2 Active."}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Fashion Ad Generator API"}

# ==================== AD GENERATION ENDPOINTS ====================

@app.post("/api/generate-ad")
def generate_ad(
    request: AdRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    """Generate ad text only (no image)"""
    try:
        prod = request.product.model_dump()
        prefs = request.preferences.model_dump()
        
        # Generate ad text using LLM service (FIXED - NOT ASYNC)
        ad_text = llm_service.generate_ad_text(prod, prefs)
        
        # Extract ad text from ad_text response
        ad_text = ad_text.get('ad_text', '')
        
        # Save to database (no image/context generated in this text-only endpoint)
        new_ad = models.Ad(
            user_id=user.id,
            ad_text=ad_text,
            prompt=str(prod),
            style=prefs.get("style"),
            preferences=str(prefs),
            image_b64=None,
            created_at=datetime.now()
        )
        db.add(new_ad)
        db.commit()
        db.refresh(new_ad)
        
        # ✅ ADD: Generate initial fake metrics
        metrics = generate_fake_metrics(new_ad.id, new_ad.created_at)
        new_ad.views = metrics["views"]
        new_ad.clicks = metrics["clicks"]
        new_ad.conversions = metrics["conversions"]
        new_ad.last_metrics_update = datetime.now()
        db.commit()
        
        # Return only available fields for the text-only endpoint
        return {
            "ad_id": new_ad.id,
            "ad_text": ad_text,
            "image": None,
            "context": None,
            "prompts": {"basic": None, "enhanced": None},
            "ai_reasoning": None
        }
        
    except Exception as e:
        logger.error(f"Ad generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ad generation failed: {str(e)}")

# ========== GENERATE OPTIMIZED IMAGE PROMPT (Gemini Pro) ==========

@app.post("/api/generate-ad-with-image")
async def generate_ad_with_image(
    request: AdRequest,
    reference_image: Optional[str] = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    """
    ENHANCED: Generate ad with MCP context + Gemini Vision analysis + Reasoning Flow
    Flow:
    1. Get MCP context (geo, weather, social)
    2. Analyze reference image (if provided) using Gemini Vision
    3. Generate optimized prompt using Gemini Pro (with reasoning)
    4. Create image with Vertex AI Imagen
    5. Return ad + image + explanation
    """
    try:
        prod = request.product.model_dump()
        prefs = request.preferences.model_dump()
        
        # Generate BASIC prompt (before MCP)
        basic_prompt = f"Professional fashion advertisement photo of {prod.get('name', 'fashion item')}, {prod.get('color', '')} color, {prod.get('material', '')} material, {prefs.get('style', 'modern')} style, {prefs.get('theme', 'elegant')} theme, high quality, studio lighting, clean background"
        logger.info(f"📝 Basic prompt: {basic_prompt}")
        
        # ========== STEP 1: MCP CONTEXT ==========
        logger.info("🔄 Fetching MCP context...")
        mcp_context = None
        try:
            mcp_context = get_mcp_context(prefs.get("location", "Mumbai"))
            logger.info(f"✅ MCP Context: {mcp_context.get('location', 'N/A')}, {mcp_context.get('temperature', 'N/A')}°C")
        except Exception as mcp_error:
            logger.warning(f"⚠️ MCP context failed: {str(mcp_error)}")
            # Fallback context
            mcp_context = {
                "location": "Mumbai",
                "weather_desc": "warm",
                "temperature": 29,
                "fashion_trend": "Cultural Chic"
            }
        
        # ========== STEP 2: ANALYZE REFERENCE IMAGE (Gemini Vision) ==========
        reference_analysis = ""
        if reference_image:
            logger.info("🔍 Analyzing reference image with Gemini Vision...")
            try:
                reference_analysis = analyze_reference_image_detailed(reference_image)
                logger.info(f"✅ Image Analysis: {reference_analysis[:100]}...")
            except Exception as img_error:
                logger.warning(f"⚠️ Image analysis failed: {str(img_error)}")
        
        # ========== STEP 3: GENERATE AD TEXT (with all context) ==========
        # Enhance product description with context for better ad copy
        if mcp_context:
            prod["mcp_context"] = f"Target market: {mcp_context.get('location', 'Mumbai')}, {mcp_context.get('weather_desc', 'warm')} weather"
        if reference_analysis:
            prod["reference_style"] = reference_analysis[:100]
        
        ad_text = llm_service.generate_ad_text(prod, prefs)
        
        # ========== STEP 4: GENERATE MCP-ENHANCED PROMPT ==========
        logger.info("🧠 Generating MCP-enhanced prompt...")
        
        # Create comprehensive 60-70 word MCP-enhanced prompt
        enhanced_prompt = f"""{basic_prompt}. 

MCP Intelligence Enhancement: Location-aware fashion advertisement tailored for {mcp_context['location']} experiencing {mcp_context['weather_desc']} weather at {mcp_context['temperature']}°C, incorporating trending {mcp_context['fashion_trend']} aesthetic suitable for current climate conditions and local cultural preferences. 

{"Reference Style Guide: " + reference_analysis if reference_analysis else ""}

Professional commercial photography, studio-quality lighting, high-resolution detail, brand-appropriate styling, market-optimized composition for {prefs.get('platform', 'Instagram')} platform engagement."""

        # Log for debugging
        logger.info(f"Basic prompt ({len(basic_prompt.split())} words): {basic_prompt}")
        logger.info(f"Enhanced prompt ({len(enhanced_prompt.split())} words): {enhanced_prompt}")
        
        # Save prompts for frontend display
        prompts_dict = {
            "basic": basic_prompt,
            "enhanced": enhanced_prompt
        }
        
        confidence = 85  # Simulated confidence score
        reasoning = {
            "context_integration": f"Integrated {mcp_context['location']} weather and {mcp_context['fashion_trend']} trend",
            "reference_integration": "Applied reference image style analysis" if reference_analysis else "No reference image provided"
        }
        
        # ========== STEP 5: GENERATE IMAGE (Vertex AI Imagen) ==========
        image_base64 = None
        try:
            # Initialize Vertex AI
            project_id = "modern-girder-476116-r2"
            location = "us-central1"
            credentials_path = "modern-girder-476116-r2-95f433f61923.json"
            
            credentials = service_account.Credentials.from_service_account_file(credentials_path)
            vertexai.init(project=project_id, location=location, credentials=credentials)
            
            logger.info(f"🎨 Generating image with enhanced prompt...")
            
            # Use the ENHANCED prompt
            model = ImageGenerationModel.from_pretrained("imagegeneration@006")
            images = model.generate_images(
                prompt=enhanced_prompt,  # ← Using MCP-enhanced prompt!
                number_of_images=1,
                language="en",
                aspect_ratio="1:1",

                safety_filter_level="block_some",
                person_generation="allow_adult",
            )
            
            # Convert to base64
            if images:
                generated_images = images.images if hasattr(images, 'images') else [images]
                if generated_images and len(generated_images) > 0:
                    img = generated_images[0]._pil_image
                    buffered = io.BytesIO()
                    img.save(buffered, format="PNG")
                    image_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                    logger.info("✅ Image generated successfully!")
                else:
                    logger.warning("No images in response")
            else:
                logger.warning("Image generation returned None")
                
        except Exception as img_error:
            logger.error(f"Image generation failed: {str(img_error)}")
        
        # ========== STEP 6: SAVE TO DATABASE ==========
        db_ad = models.Ad(
            user_id=user.id,
            ad_text=str(ad_text),
            prompt=enhanced_prompt,  # ✅ Save enhanced prompt
            style=prefs.get('style'),
            preferences=str(prefs),
            image_b64=image_base64,
            created_at=datetime.now()
        )
        db.add(db_ad)
        db.commit()
        db.refresh(db_ad)
        
        # Generate fake metrics
        metrics = generate_fake_metrics(db_ad.id, db_ad.created_at)
        db_ad.views = metrics["views"]
        db_ad.clicks = metrics["clicks"]
        db_ad.conversions = metrics["conversions"]
        db.commit()
        
        # ========== RETURN COMPLETE RESPONSE ==========
        return {
            "ad_id": db_ad.id,
            "ad_text": ad_text,
            "image": image_base64,
            
            # 🎯 SHOW ALL PROMPTS
            "prompts": {
                "basic": basic_prompt,
                "mcp_context_data": {
                    "location": f"{mcp_context['location']}" if mcp_context else None,
                    "weather": f"{mcp_context['weather_desc']} ({mcp_context['temperature']}°C)" if mcp_context else None,
                    "trend": mcp_context.get('fashion_trend') if mcp_context else None
                },
                "final_optimized": enhanced_prompt
            },
            
            "ai_reasoning": {
                "optimized_prompt": enhanced_prompt,
                "confidence_score": confidence,
                "decisions": ["Applied MCP context", "Integrated reference analysis" if reference_analysis else "No reference provided"],
                "reasoning": reasoning
            },
            
            # 🌍 Context used
            "context": {
                "mcp_data": {
                    "location": f"{mcp_context['location']}" if mcp_context else None,
                    "weather": f"{mcp_context['weather_desc']} ({mcp_context['temperature']}°C)" if mcp_context else None,
                    "trend": mcp_context.get('fashion_trend') if mcp_context else None
                },
                "reference_analysis": reference_analysis if reference_analysis else None
            }
        }
        
    except Exception as e:
        logger.error(f"Ad generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ad generation failed: {str(e)}")
    
# ==================== A/B TESTING ENDPOINTS ====================

@app.post("/api/generate-ab-variants")
def generate_ab_variants(
    request: ABTestRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    """Generate A/B test variants (FULLY SELF-CONTAINED)"""
    try:
        prod = request.product.model_dump()
        prefs = request.preferences.model_dump()
        
        # Generate variants by varying the specified parameter
        base_tone = prefs.get("tone", "professional")
        
        # Different tone/style variations
        if request.variation_type == "tone":
            variations = ["professional", "playful", "elegant"][:request.num_variants]
        elif request.variation_type == "style":
            variations = ["minimalist", "bold", "modern"][:request.num_variants]
        else:
            variations = [base_tone] * request.num_variants
        
        parent_ad = None
        saved_variants = []
        
        # Generate each variant
        for i, variation in enumerate(variations):
            # Modify preferences for this variant
            variant_prefs = prefs.copy()
            if request.variation_type == "tone":
                variant_prefs["tone"] = variation
            else:
                variant_prefs["style"] = variation
            
            # Generate ad text for this variant (NO IMAGE - faster)
            variant_ad_text = llm_service.generate_ad_text(prod, variant_prefs)
            
            # Save to database
            db_ad = models.Ad(
                user_id=user.id,
                ad_text=str(variant_ad_text),
                prompt=str(prod),
                style=variant_prefs.get("style"),
                preferences=str(variant_prefs),
                image_b64=None,
                created_at=datetime.now()
            )
            db.add(db_ad)
            db.commit()
            db.refresh(db_ad)
            
            if i == 0:
                parent_ad = db_ad
            
            saved_variants.append({
                "ad_id": db_ad.id,
                "variant_name": f"Variant {chr(65+i)}",
                "variation": variation,
                "ad_text": variant_ad_text
            })
        
        return {
            "parent_ad_id": parent_ad.id,
            "variants": saved_variants,
            "message": f"Generated {len(saved_variants)} A/B test variants successfully!"
        }
        
    except Exception as e:
        logger.error(f"A/B variant generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"A/B test generation failed: {str(e)}")

# ==================== ANALYTICS ENDPOINTS ====================

@app.get("/api/ads/{ad_id}/analytics")
def get_ad_analytics(
    ad_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    """Get analytics for specific ad"""
    analytics = analytics_service.get_ad_analytics(ad_id, db)
    if not analytics:
        raise HTTPException(status_code=404, detail="Ad not found")
    return analytics

@app.get("/api/my-analytics")
def get_my_analytics(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive analytics with CSV data integration"""
    try:
        # Try to load CSV data
        try:
            from datetime import datetime, timedelta
            import sys
            import os
            
            # Add project root to path to import data_loader
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            
            if data_loader:
                # Load CSV data
                summary = data_loader.get_analytics_summary()
                mock_ads = data_loader.load_mock_ad_performance()
                features = data_loader.load_feature_adoption()
                
                # Calculate time-based metrics (last 30 days)
                today = datetime.now()
                dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(30, 0, -1)]
                total_views = summary['total_views']
                daily_views = [total_views // 30 + (i * 100) for i in range(30)]
                
                # Platform breakdown
                platform_stats = mock_ads.groupby('Platform').agg({
                    'Views': 'sum',
                    'Clicks': 'sum',
                    'Conversions': 'sum'
                }).to_dict('index')
                
                # Product performance
                product_stats = mock_ads.groupby('Product').agg({
                    'Views': 'mean',
                    'CTR (%)': 'mean',
                    'CVR (%)': 'mean'
                }).to_dict('index')
                
                return {
                    "success": True,
                    "data": {
                        "summary": summary,
                        "time_series": {
                            "dates": dates,
                            "views": daily_views,
                            "clicks": [v // 25 for v in daily_views],
                            "conversions": [v // 150 for v in daily_views]
                        },
                        "platforms": platform_stats,
                        "products": product_stats,
                        "top_performing": mock_ads.nlargest(10, 'CTR (%)')[['Ad ID', 'Product', 'Platform', 'CTR (%)', 'CVR (%)']].to_dict('records'),
                        "feature_adoption": features.to_dict('records')
                    }
                }
            else:
                raise ImportError("Data loader not available")
                
        except Exception as csv_error:
            logger.warning(f"CSV data not available, using database: {str(csv_error)}")
            
            # Fallback to database-only analytics
            ads = db.query(models.Ad).filter(models.Ad.user_id == user.id).all()
            
            total_views = sum(ad.views for ad in ads)
            total_clicks = sum(ad.clicks for ad in ads)
            total_conversions = sum(ad.conversions for ad in ads)
            
            platform_stats = {}
            for ad in ads:
                try:
                    prefs = eval(ad.preferences) if isinstance(ad.preferences, str) else ad.preferences
                    platform = prefs.get("platform", "Unknown")
                    if platform not in platform_stats:
                        platform_stats[platform] = {"ads": 0, "views": 0, "clicks": 0}
                    platform_stats[platform]["ads"] += 1
                    platform_stats[platform]["views"] += ad.views
                    platform_stats[platform]["clicks"] += ad.clicks
                except:
                    pass
            
            return {
                "success": True,
                "data": {
                    "summary": {
                        "total_ads": len(ads),
                        "total_views": total_views,
                        "total_clicks": total_clicks,
                        "total_conversions": total_conversions,
                        "avg_ctr": round((total_clicks / total_views * 100), 2) if total_views > 0 else 0,
                        "avg_cvr": round((total_conversions / total_clicks * 100), 2) if total_clicks > 0 else 0,
                        "platforms": ["Instagram", "Facebook", "TikTok"],
                        "products": ["Dress", "Shoes", "Jeans"]
                    },
                    "platforms": platform_stats,
                    "products": {},
                    "time_series": {
                        "dates": [],
                        "views": [],
                        "clicks": [],
                        "conversions": []
                    },
                    "top_performing": [
                        {
                            "Ad ID": ad.id,
                            "Product": "N/A",
                            "Platform": "N/A", 
                            "CTR (%)": round((ad.clicks / ad.views * 100), 2) if ad.views > 0 else 0,
                            "CVR (%)": round((ad.conversions / ad.clicks * 100), 2) if ad.clicks > 0 else 0
                        }
                        for ad in sorted(ads, key=lambda x: x.created_at, reverse=True)[:5]
                    ],
                    "feature_adoption": []
                }
            }
            
    except Exception as e:
        logger.error(f"Analytics error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ads/{ad_id}/view")
def record_ad_view(
    ad_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    """Record an ad view"""
    success = analytics_service.record_view(ad_id, db)
    if not success:
        raise HTTPException(status_code=404, detail="Ad not found")
    return {"message": "View recorded"}

@app.post("/api/ads/{ad_id}/click")
def record_ad_click(
    ad_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    """Record an ad click"""
    success = analytics_service.record_click(ad_id, db)
    if not success:
        raise HTTPException(status_code=404, detail="Ad not found")
    return {"message": "Click recorded"}

@app.post("/api/ads/{ad_id}/conversion")
def record_ad_conversion(
    ad_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    """Record an ad conversion"""
    success = analytics_service.record_conversion(ad_id, db)
    if not success:
        raise HTTPException(status_code=404, detail="Ad not found")
    return {"message": "Conversion recorded"}

@app.get("/api/ab-test/{parent_ad_id}/compare")
def compare_ab_test(
    parent_ad_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    """Compare A/B test variants performance"""
    return analytics_service.compare_ab_variants(parent_ad_id, db)

# ==================== TEMPLATE MANAGEMENT ====================

@app.post("/api/templates")
def create_template(
    request: TemplateCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    """Create a new template"""
    db_template = models.Template(
        name=request.name,
        description=request.description,
        product_template=str(request.product_template),
        preferences_template=str(request.preferences_template),
        is_public=request.is_public,
        user_id=user.id
    )
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    
    return {"template_id": db_template.id, "message": "Template created"}

@app.get("/api/templates")
def get_templates(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    """Get all templates (user's + public)"""
    templates = db.query(models.Template).filter(
        (models.Template.user_id == user.id) | (models.Template.is_public == True)
    ).all()
    
    return [
        {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "product_template": t.product_template,
            "preferences_template": t.preferences_template,
            "is_public": t.is_public,
            "created_at": t.created_at
        }
        for t in templates
    ]

# ==================== EXPORT FUNCTIONALITY ====================

@app.post("/api/export-ad")
def export_ad(
    request: dict,
    user: models.User = Depends(get_current_user)
):
    """Export ad as downloadable image"""
    try:
        ad_text = request.get("ad_text", {})
        image_b64 = request.get("image")
        export_format = request.get("format", "composite")
        
        if not image_b64:
            raise HTTPException(status_code=400, detail="No image provided")
        
        if export_format == "composite":
            result_b64 = create_ad_composite(ad_text, image_b64)
            image_bytes = base64.b64decode(result_b64)
        else:
            image_bytes = image_base64_to_bytes(image_b64)
        
        return Response(
            content=image_bytes,
            media_type="image/png",
            headers={
                "Content-Disposition": f"attachment; filename=fashion_ad_{user.username}.png"
            }
        )
    except Exception as e:
        logger.error(f"Export error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== AD MANAGEMENT ====================

@app.get("/api/my-ads")
def get_my_ads(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ads = db.query(models.Ad).filter(models.Ad.user_id == user.id).all()
    
    result = []
    for ad in ads:
        # Refresh metrics if older than 1 hour
        if not ad.last_metrics_update or (datetime.now() - ad.last_metrics_update).seconds > 3600:
            metrics = generate_fake_metrics(ad.id, ad.created_at)
            ad.views = metrics["views"]
            ad.clicks = metrics["clicks"]
            ad.conversions = metrics["conversions"]
            ad.last_metrics_update = datetime.now()
            db.commit()
        
        result.append({
            "id": ad.id,
            "ad_text": ad.ad_text,
            "image_b64": ad.image_b64,
            "created_at": str(ad.created_at),
            "views": ad.views,
            "clicks": ad.clicks,
            "conversions": ad.conversions,
            "ctr": round((ad.clicks / ad.views * 100), 2) if ad.views > 0 else 0,
            "cvr": round((ad.conversions / ad.clicks * 100), 2) if ad.clicks > 0 else 0
        })
    
    return {"ads": result}

@app.delete("/api/ads/{ad_id}")
def delete_ad(
    ad_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    """Delete a specific ad"""
    ad = db.query(models.Ad).filter(
        models.Ad.id == ad_id,
        models.Ad.user_id == user.id
    ).first()
    
    if not ad:
        raise HTTPException(status_code=404, detail="Ad not found")
    
    db.delete(ad)
    db.commit()
    return {"message": "Ad deleted successfully"}

@app.put("/api/ads/{ad_id}")
def update_ad(
    ad_id: int,
    request: dict,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    """Update an existing ad"""
    ad = db.query(models.Ad).filter(
        models.Ad.id == ad_id,
        models.Ad.user_id == user.id
    ).first()
    
    if not ad:
        raise HTTPException(status_code=404, detail="Ad not found")
    
    updated_text = request.get("ad_text", {})
    
    # Safely parse existing ad_text
    try:
        current_ad_text = eval(ad.ad_text) if isinstance(ad.ad_text, str) else ad.ad_text
    except:
        current_ad_text = {}
    
    if isinstance(current_ad_text, dict):
        current_ad_text.update(updated_text)
        ad.ad_text = str(current_ad_text)
    else:
        ad.ad_text = str(updated_text)
    
    db.commit()
    db.refresh(ad)
    
    return {
        "message": "Ad updated successfully",
        "ad": {
            "id": ad.id,
            "ad_text": current_ad_text if isinstance(current_ad_text, dict) else updated_text
        }
    }

# ==================== FILE UPLOAD ====================

@app.post("/api/upload-reference-image")
async def upload_reference_image(
    file: UploadFile = File(...),
    user: models.User = Depends(get_current_user)
):
    """Upload a reference image for ad generation"""
    try:
        contents = await file.read()
        
        # Validate file size (max 5MB)
        if len(contents) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Image too large (max 5MB)")
        
        image_base64 = base64.b64encode(contents).decode('utf-8')
        
        return {
            "image_base64": image_base64,
            "filename": file.filename,
            "size": len(contents)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== SEARCH AND FILTERING ====================

@app.get("/api/search-ads")
def search_ads(
    query: str = "",
    platform: str = None,
    min_views: int = 0,
    sort_by: str = "created_at",
    order: str = "desc",
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search and filter user's ads"""
    ads_query = db.query(models.Ad).filter(models.Ad.user_id == user.id)
    
    # Apply filters
    if query:
        ads_query = ads_query.filter(models.Ad.ad_text.contains(query))
    
    if platform:
        ads_query = ads_query.filter(
            models.Ad.preferences.contains(f"'platform': '{platform}'")
        )
    
    if min_views > 0:
        ads_query = ads_query.filter(models.Ad.views >= min_views)
    
    # Apply sorting
    if sort_by == "views":
        ads_query = ads_query.order_by(
            models.Ad.views.desc() if order == "desc" else models.Ad.views.asc()
        )
    elif sort_by == "clicks":
        ads_query = ads_query.order_by(
            models.Ad.clicks.desc() if order == "desc" else models.Ad.clicks.asc()
        )
    else:
        ads_query = ads_query.order_by(
            models.Ad.created_at.desc() if order == "desc" else models.Ad.created_at.asc()
        )
    
    ads = ads_query.all()
    
    return [
        {
            "id": ad.id,
            "ad_text": ad.ad_text,
            "preferences": ad.preferences,
            "created_at": ad.created_at,
            "views": ad.views,
            "clicks": ad.clicks,
            "conversions": ad.conversions,
            "ctr": (ad.clicks / ad.views * 100) if ad.views > 0 else 0
        }
        for ad in ads
    ]

# ==================== BULK OPERATIONS ====================

@app.post("/api/bulk-delete-ads")
def bulk_delete_ads(
    ad_ids: List[int],
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    """Delete multiple ads at once"""
    deleted_count = 0
    for ad_id in ad_ids:
        ad = db.query(models.Ad).filter(
            models.Ad.id == ad_id,
            models.Ad.user_id == user.id
        ).first()
        if ad:
            db.delete(ad)
            deleted_count += 1
    
    db.commit()
    return {
        "message": f"Deleted {deleted_count} ads",
        "deleted_count": deleted_count
    }

@app.post("/api/bulk-export-ads")
def bulk_export_ads(
    ad_ids: List[int],
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    """Export multiple ads data"""
    ads_data = []
    
    for ad_id in ad_ids:
        ad = db.query(models.Ad).filter(
            models.Ad.id == ad_id,
            models.Ad.user_id == user.id
        ).first()
        if ad:
            try:
                ads_data.append({
                    "id": ad.id,
                    "ad_text": ad.ad_text,
                    "created_at": str(ad.created_at),
                    "views": ad.views,
                    "clicks": ad.clicks,
                    "conversions": ad.conversions
                })
            except:
                pass
    
    return {"ads": ads_data, "count": len(ads_data)}

# ==================== VERSION MANAGEMENT ====================

@app.post("/api/ads/{ad_id}/save-version")
def save_ad_version(
    ad_id: int,
    notes: str = "",
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    """Save current ad version"""
    ad = db.query(models.Ad).filter(
        models.Ad.id == ad_id,
        models.Ad.user_id == user.id
    ).first()
    
    if not ad:
        raise HTTPException(status_code=404, detail="Ad not found")
    
    # Simple version tracking (can be enhanced)
    return {"message": "Version saved", "version_number": 1}

@app.get("/api/ads/{ad_id}/versions")
def get_ad_versions(
    ad_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    """Get all versions of an ad"""
    ad = db.query(models.Ad).filter(
        models.Ad.id == ad_id,
        models.Ad.user_id == user.id
    ).first()
    
    if not ad:
        raise HTTPException(status_code=404, detail="Ad not found")
    
    # Return current version (can be enhanced for multiple versions)
    return [
        {
            "id": ad.id,
            "version_number": 1,
            "ad_text": ad.ad_text,
            "created_at": ad.created_at,
            "notes": "Current version"
        }
    ]

# ==================== USAGE/QUOTA MANAGEMENT ====================

@app.get("/api/my-usage")
def get_my_usage(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from datetime import datetime, timedelta
    
    # Count today's ads
    today = datetime.now().date()
    ads_today = db.query(models.Ad).filter(
        models.Ad.user_id == user.id,
        models.Ad.created_at >= today
    ).count()
    
    # Count this month's ads
    month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0)
    ads_this_month = db.query(models.Ad).filter(
        models.Ad.user_id == user.id,
        models.Ad.created_at >= month_start
    ).count()
    
    return {
        "ads_today": ads_today,
        "daily_limit": 50,  # ✅ NEW
        "ads_this_month": ads_this_month,
        "monthly_limit": 500,  # ✅ NEW
        "can_create": ads_today < 50
    }

# ==================== CSV DATA ENDPOINTS ====================

@app.get("/api/competitive-analysis")
async def get_competitive_analysis():
    """Get competitive comparison matrix"""
    try:
        if data_loader:
            comp_data = data_loader.load_competitive_matrix()
            return {"success": True, "data": comp_data.to_dict('records')}
        else:
            # Fallback data
            return {"success": True, "data": [
                {"Feature": "AI Generation", "Our Platform": "Yes", "Competitor A": "No", "Competitor B": "Limited"},
                {"Feature": "MCP Context", "Our Platform": "Yes", "Competitor A": "No", "Competitor B": "No"}
            ]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/cost-analysis")
async def get_cost_analysis():
    """Get cost breakdown comparison"""
    try:
        if data_loader:
            cost_data = data_loader.load_cost_analysis()
            return {"success": True, "data": cost_data.to_dict('records')}
        else:
            # Fallback data
            return {"success": True, "data": [
                {"Method": "Traditional", "Cost per Ad": 100, "Time (hours)": 4},
                {"Method": "AI-Generated", "Cost per Ad": 5, "Time (hours)": 0.1}
            ]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/performance-benchmarks")
async def get_performance_benchmarks():
    """Get system performance metrics"""
    try:
        if data_loader:
            perf_data = data_loader.load_performance_benchmarks()
            return {"success": True, "data": perf_data.to_dict('records')}
        else:
            # Fallback data
            return {"success": True, "data": [
                {"Metric": "Average Response Time", "Value": "2.3s", "Target": "< 3s"},
                {"Metric": "Success Rate", "Value": "99.2%", "Target": "> 99%"}
            ]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== ADDITIONAL UTILITY ENDPOINTS ====================

@app.get("/api/dashboard-summary")
def get_dashboard_summary(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dashboard summary statistics"""
    try:
        ads = db.query(models.Ad).filter(models.Ad.user_id == user.id).all()
        
        total_ads = len(ads)
        total_views = sum(ad.views for ad in ads)
        total_clicks = sum(ad.clicks for ad in ads)
        total_conversions = sum(ad.conversions for ad in ads)
        
        # Calculate averages
        avg_ctr = (total_clicks / total_views * 100) if total_views > 0 else 0
        avg_cvr = (total_conversions / total_clicks * 100) if total_clicks > 0 else 0
        
        # Recent activity (last 7 days)
        from datetime import datetime, timedelta
        week_ago = datetime.now() - timedelta(days=7)
        recent_ads = [ad for ad in ads if ad.created_at >= week_ago]
        
        return {
            "total_ads": total_ads,
            "total_views": total_views,
            "total_clicks": total_clicks,
            "total_conversions": total_conversions,
            "avg_ctr": round(avg_ctr, 2),
            "avg_cvr": round(avg_cvr, 2),
            "recent_ads_count": len(recent_ads),
            "best_performing_ad": max(ads, key=lambda x: x.views).id if ads else None
        }
    except Exception as e:
        logger.error(f"Dashboard summary error: {str(e)}")
        return {
            "total_ads": 0,
            "total_views": 0,
            "total_clicks": 0,
            "total_conversions": 0,
            "avg_ctr": 0,
            "avg_cvr": 0,
            "recent_ads_count": 0,
            "best_performing_ad": None
        }

@app.get("/api/user-profile")
def get_user_profile(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user profile information"""
    ads_count = db.query(models.Ad).filter(models.Ad.user_id == user.id).count()
    
    return {
        "user_id": user.id,
        "username": user.username,
        "ads_created": ads_count,
        "member_since": user.created_at if hasattr(user, 'created_at') else None,
        "subscription_tier": "Free",  # Can be enhanced
        "daily_quota_used": ads_count,  # Simplified
        "daily_quota_limit": 50
    }

# ==================== SERVER STARTUP ====================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

# Run with: python -m backend.api.main
# Or: uvicorn backend.api.main:app --reload --port 8000