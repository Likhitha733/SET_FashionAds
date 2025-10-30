# backend/sources/geo_server.py
from fastapi import FastAPI

app = FastAPI()

@app.get("/geo")
def get_geo(user_id: str):
    # Demo: static location, replace with real GeoIP lookup
    return {"city": "Bangalore", "country": "IN", "lat": 12.97, "lon": 77.59}
