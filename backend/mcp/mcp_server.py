import os
import random
import requests
import httpx
from fastapi import FastAPI, Request, HTTPException

app = FastAPI()

# ENV variables
SOCIALBLADE_API_KEY = os.getenv("SOCIALBLADE_API_KEY", None)
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", None)
IPAPI_URL = "https://ipapi.co/{ip}/json/"
OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"

# GEOIP
async def fetch_geo(ip: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(IPAPI_URL.format(ip=ip))
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail="GeoIP API Error")
        geo = resp.json()
        return {
            "city": geo.get("city"),
            "country": geo.get("country_name"),
            "lat": geo.get("latitude"),
            "lon": geo.get("longitude")
        }

# WEATHER WITH HYBRID (API/Mock)
async def fetch_weather(lat, lon):
    if OPENWEATHER_API_KEY:
        params = {
            "lat": lat,
            "lon": lon,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric"
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(OPENWEATHER_URL, params=params)
            if resp.status_code == 200:
                weather = resp.json()
                return {
                    "temperature": weather["main"]["temp"],
                    "condition": weather["weather"][0]["main"],
                    "humidity": weather["main"].get("humidity"),
                    "wind": weather["wind"].get("speed")
                }
    # Fallback/mock
    return {
        "temperature": round(random.uniform(17,35), 1),
        "condition": random.choice(["Sunny","Cloudy","Rainy","Clear","Stormy"]),
        "humidity": random.randint(30,90),
        "wind": round(random.uniform(0.5, 5.2), 1)
    }

# SOCIALBLADE API OR MOCK
def generate_realistic_social_stats(username: str = "demo_brand") -> dict:
    followers_count = random.randint(500, 20000)
    engagement_rate = round(random.uniform(1.2, 10.0), 2)
    media_count = random.randint(50, 350)
    recent_top_post = {
        "likes": random.randint(75, 1200),
        "comments": random.randint(2, 50),
        "reach": random.randint(500, followers_count*3),
        "hashtags": random.sample([
            "#fashion", "#ootd", "#style", "#newcollection", "#trends2025", "#limited", "#organic", "#musthave"
        ], 3)
    }
    latest_campaign = random.choice([
        "Spring Sale 2025", "Festive Offers", "New Arrivals", "Summer Essentials", "Influencer Collab"
    ])
    return {
        "username": username,
        "followers_count": followers_count,
        "engagement_rate": engagement_rate,
        "media_count": media_count,
        "recent_top_post": recent_top_post,
        "latest_campaign": latest_campaign
    }

def fetch_socialblade_instagram(username: str) -> dict:
    if not SOCIALBLADE_API_KEY:
        return None
    url = f"https://api.socialblade.com/v2/instagram/user/{username}?apiKey={SOCIALBLADE_API_KEY}"
    resp = requests.get(url)
    if resp.status_code == 200:
        data = resp.json()
        return {
            "username": data.get("username", username),
            "followers_count": data.get("followers", 0),
            "engagement_rate": data.get("engagement", 0),
            "media_count": data.get("uploads", 0),
            "recent_top_post": {
                "likes": data.get("average_likes", 0),
                "comments": data.get("average_comments", 0),
                "hashtags": []
            },
            "latest_campaign": "N/A"
        }
    return None

@app.post("/context")
async def get_full_context(request: Request):
    data = await request.json()
    ip = data.get("ip", "8.8.8.8")
    geo = await fetch_geo(ip)
    weather = await fetch_weather(geo["lat"], geo["lon"])
    username = data.get("social_username", "demo_brand")
    social_stats = fetch_socialblade_instagram(username)
    if social_stats is None:
        social_stats = generate_realistic_social_stats(username)
    return {
        "geo": geo,
        "weather": weather,
        "social": social_stats,
        "user": data.get("user_id", ""),
        "product": data.get("product_info", {})
    }
