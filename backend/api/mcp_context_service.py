"""
MCP Context Service - FIXED VERSION
Provides location-aware context (weather, trends, social data) for ad generation
"""

import os
import logging
import random
from datetime import datetime
import requests

logger = logging.getLogger(__name__)

# ✅ FIXED: Changed from 'async def' to regular 'def' (synchronous)
def get_mcp_context(location: str = "Mumbai"):
    """
    Get MCP (Model Context Protocol) data for location-aware ad generation
    ✅ FIXED: Now synchronous - no await needed!
    
    Returns:
        dict: Context with weather, location, fashion trends
    """
    try:
        logger.info(f"🌍 Fetching MCP context for {location}...")
        
        # ==================== WEATHER DATA ====================
        weather_data = _get_weather_data(location)
        
        # ==================== FASHION TREND ====================
        fashion_trend = _get_fashion_trend(location, weather_data)
        
        # ==================== SOCIAL CONTEXT (Optional) ====================
        social_data = _get_social_context()
        
        # ==================== BUILD MCP CONTEXT ====================
        mcp_context = {
            "location": location,
            "weather_desc": weather_data["description"],
            "temperature": weather_data["temp"],
            "weather_icon": weather_data.get("icon", "☀️"),
            "fashion_trend": fashion_trend,
            "season": _get_season(),
            "social_context": social_data,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"✅ MCP Context: {location}, {weather_data['temp']}°C, {fashion_trend}")
        return mcp_context
        
    except Exception as e:
        logger.warning(f"⚠️ MCP context error: {str(e)}, using fallback")
        # Fallback context
        return {
            "location": location,
            "weather_desc": "clear",
            "temperature": 25,
            "weather_icon": "☀️",
            "fashion_trend": "Modern Chic",
            "season": _get_season(),
            "social_context": {},
            "timestamp": datetime.now().isoformat()
        }


def _get_weather_data(location: str) -> dict:
    """Get real-time weather data from OpenWeatherMap API"""
    try:
        api_key = os.getenv("OPENWEATHER_API_KEY")
        
        if not api_key or api_key == "your-openweathermap-api-key-here":
            logger.info("🌤️ Using mock weather data (no API key)")
            return _get_mock_weather()
        
        # Call OpenWeatherMap API
        url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=metric"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            return {
                "temp": round(data["main"]["temp"]),
                "description": data["weather"][0]["description"],
                "icon": data["weather"][0]["icon"],
                "humidity": data["main"]["humidity"]
            }
        else:
            logger.warning(f"Weather API error: {response.status_code}")
            return _get_mock_weather()
            
    except Exception as e:
        logger.warning(f"Weather fetch error: {str(e)}")
        return _get_mock_weather()


def _get_mock_weather() -> dict:
    """Mock weather data for testing/fallback"""
    mock_weathers = [
        {"temp": 28, "description": "clear sky", "icon": "01d", "humidity": 65},
        {"temp": 24, "description": "partly cloudy", "icon": "02d", "humidity": 70},
        {"temp": 22, "description": "light rain", "icon": "10d", "humidity": 85},
        {"temp": 30, "description": "sunny", "icon": "01d", "humidity": 60},
    ]
    return random.choice(mock_weathers)


def _get_fashion_trend(location: str, weather_data: dict) -> str:
    """
    Determine fashion trend based on location and weather
    Returns appropriate fashion aesthetic
    """
    temp = weather_data["temp"]
    weather_desc = weather_data["description"].lower()
    
    # Temperature-based trends
    if temp > 30:
        base_trends = ["Summer Breeze", "Tropical Chic", "Light & Airy"]
    elif temp > 20:
        base_trends = ["Modern Comfort", "Smart Casual", "Urban Elegance"]
    else:
        base_trends = ["Cozy Layers", "Winter Warmth", "Sophisticated Style"]
    
    # Weather-influenced adjustments
    if "rain" in weather_desc:
        return "Rain-Ready Fashion"
    elif "cloud" in weather_desc:
        return random.choice(["Moody Aesthetics", "Soft Neutrals"])
    
    # Location-specific trends
    if location.lower() in ["mumbai", "delhi", "bangalore"]:
        indian_trends = ["Fusion Wear", "Contemporary Indian", "Indo-Western"]
        return random.choice(indian_trends + base_trends)
    
    return random.choice(base_trends)


def _get_season() -> str:
    """Get current season based on month"""
    month = datetime.now().month
    
    if month in [12, 1, 2]:
        return "Winter"
    elif month in [3, 4, 5]:
        return "Spring"
    elif month in [6, 7, 8]:
        return "Summer"
    else:
        return "Fall"


def _get_social_context() -> dict:
    """
    Get trending social media data (optional enhancement)
    Can integrate with social media APIs in future
    """
    # Mock data for now - can integrate real APIs later
    return {
        "trending_hashtags": ["#FashionWeek", "#OOTD", "#StyleInspo"],
        "engagement_peak_hours": [9, 12, 18, 21],
        "popular_platforms": ["Instagram", "Pinterest", "TikTok"]
    }


# ==================== HELPER FUNCTION FOR WEATHER EMOJI ====================

def get_weather_emoji(weather_desc: str) -> str:
    """Convert weather description to emoji"""
    weather_desc = weather_desc.lower()
    
    if "clear" in weather_desc or "sunny" in weather_desc:
        return "☀️"
    elif "cloud" in weather_desc:
        return "☁️"
    elif "rain" in weather_desc:
        return "🌧️"
    elif "storm" in weather_desc:
        return "⛈️"
    elif "snow" in weather_desc:
        return "❄️"
    elif "fog" in weather_desc or "mist" in weather_desc:
        return "🌫️"
    else:
        return "🌤️"


# ==================== EXPORT ====================

__all__ = ["get_mcp_context", "get_weather_emoji"]
