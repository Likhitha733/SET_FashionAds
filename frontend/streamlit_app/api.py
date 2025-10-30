import requests

BACKEND_URL = "http://localhost:8000"

def login(username, password):
    """Login user"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/login",
            json={"username": username, "password": password}  # Use data, not json for OAuth2
        )
        return response
    except Exception as e:
        print(f"Login error: {e}")
        return None

def register(username, password):
    """Register new user"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/register",
            json={"username": username, "password": password}
        )
        return response
    except Exception as e:
        print(f"Register error: {e}")
        return None

def get_my_analytics(token):
    """Get user analytics"""
    return requests.get(
        f"{BACKEND_URL}/api/my-analytics",
        headers={"Authorization": f"Bearer {token}"}
    )

def get_my_usage(token):
    """Get usage stats"""
    return requests.get(
        f"{BACKEND_URL}/api/my-usage",
        headers={"Authorization": f"Bearer {token}"}
    )

def generate_ad_with_image(payload, token):
    """Generate complete ad"""
    return requests.post(
        f"{BACKEND_URL}/api/generate-ad-with-image",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )

def bulk_delete_ads(ad_ids, token):
    """Delete multiple ads"""
    return requests.post(
        f"{BACKEND_URL}/api/bulk-delete-ads",
        json=ad_ids,
        headers={"Authorization": f"Bearer {token}"}
    )

def bulk_export_ads(ad_ids, token):
    """Export multiple ads"""
    return requests.post(
        f"{BACKEND_URL}/api/bulk-export-ads",
        json=ad_ids,
        headers={"Authorization": f"Bearer {token}"}
    )

def my_ads(token):
    """Get all user ads"""
    return requests.get(
        f"{BACKEND_URL}/api/my-ads",
        headers={"Authorization": f"Bearer {token}"}
    )

def tryon(user_photo, product_photo, token):
    """Virtual try-on (may not work yet)"""
    try:
        return requests.post(
            f"{BACKEND_URL}/api/tryon/tryon",
            files={"user_photo": user_photo, "product_photo": product_photo},
            headers={"Authorization": f"Bearer {token}"}
        )
    except:
        return type('obj', (object,), {
            'status_code': 503,
            'text': 'Virtual try-on service unavailable'
        })

def tryon(person_image, garment_image, token):
    files = {
        'user_photo': ('person.jpg', person_image, 'image/jpeg'),
        'product_photo': ('garment.jpg', garment_image, 'image/jpeg')
    }
    headers = {"Authorization": f"Bearer {token}"}
    return requests.post(f"{BACKEND_URL}/api/tryon", files=files, headers=headers, timeout=120)

def get_competitive_analysis():
    """Get competitive comparison"""
    return requests.get(f"{BACKEND_URL}/api/competitive-analysis")

def get_cost_analysis():
    """Get cost breakdown"""
    return requests.get(f"{BACKEND_URL}/api/cost-analysis")

def get_performance_benchmarks():
    """Get performance benchmarks"""
    return requests.get(f"{BACKEND_URL}/api/performance-benchmarks")
