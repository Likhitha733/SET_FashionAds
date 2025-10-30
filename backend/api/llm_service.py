from fastapi import APIRouter, Request, HTTPException
from dotenv import load_dotenv
import os
import json
import re
import google.generativeai as genai
from backend.utils import error_handler


load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

router = APIRouter()

def build_prompt(context: dict) -> str:
    geo = context["geo"]
    weather = context["weather"]
    social = context["social"]
    product = context.get("product", {})
    preferences = context.get("preferences", {})

    prompt = f"""
Generate a JSON object for a fashion advertisement with the following details:

Product Information:
- Name: {product.get('name', 'Fashion Item')}
- Type: {product.get('type', 'Clothing')}
- Color: {product.get('color', 'Various')}
- Material: {product.get('material', 'Premium')}
- Collection: {product.get('collection', 'Latest')}

Context:
- City: {geo.get('city', '')}, Country: {geo.get('country', '')}
- Weather: {weather.get('condition', '')}, Temp: {weather.get('temperature', '')}°C

Social Analytics:
- Username: {social.get('username', '')}
- Followers: {social.get('followers_count', '')}
- Engagement Rate: {social.get('engagement_rate', '')}%
- Latest Campaign: {social.get('latest_campaign', '')}
- Hashtags: {', '.join(social['recent_top_post']['hashtags']) if social.get('recent_top_post') else ''}

Preferences:
- Style: {preferences.get('style', 'Modern')}
- Tone: {preferences.get('tone', 'Professional')}
- Platform: {preferences.get('platform', 'Instagram')}
- Target Audience: {preferences.get('target_audience', 'Fashion lovers')}
- Tagline Max Words: {preferences.get('tagline_max_words', 6)}

Output ONLY a valid JSON object in this exact format (no markdown, no extra text):
{{
    "headline": "Catchy headline here",
    "tagline": "Brief tagline (max {preferences.get('tagline_max_words', 6)} words)",
    "body_copy": "Compelling description with emojis and details",
    "cta": "Clear call-to-action"
}}
"""
    return prompt

def generate_ad_text(product_info: dict, preferences: dict, context: dict = None):
    """Generate ad copy using Gemini with error handling"""
    try:
        prompt = build_prompt({
            "geo": context.get("geo", {}),
            "weather": context.get("weather", {}),
            "social": context.get("social", {}),
            "product": product_info,
            "preferences": preferences
        }) if context else build_prompt({
            "geo": {},
            "weather": {},
            "social": {},
            "product": product_info,
            "preferences": preferences
        })
        
        model = genai.GenerativeModel("models/gemini-2.0-flash-exp")
        response = model.generate_content(prompt)
        response_text = response.text.strip()

        # Clean response (remove markdown code blocks if present)
        response_text = re.sub(r'^```.*$', '', response_text, flags=re.MULTILINE)
        response_text = re.sub(r'\s*```+$', '', response_text)
        response_text = response_text.strip()

        # Try to parse JSON
        try:
            ad_json = json.loads(response_text)
        except json.JSONDecodeError:
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                ad_json = json.loads(json_match.group())
            else:
                ad_json = {
                    "headline": response_text[:100] if response_text else "Discover Fashion",
                    "tagline": "Style that speaks.",
                    "body_copy": response_text if response_text else "Experience premium quality.",
                    "cta": "Shop Now"
                }
        required_keys = ["headline", "tagline", "body_copy", "cta"]
        for key in required_keys:
            if key not in ad_json:
                ad_json[key] = ""

        # Ensure all values are strings
        for key in ad_json:
            if not isinstance(ad_json[key], str):
                ad_json[key] = str(ad_json[key])

        return ad_json
    except Exception as e:
        error_handler.handle_llm_error(e)
        raise HTTPException(status_code=500, detail=f"LLM Error: {str(e)}")

def generate_ad_variations(product_info: dict, preferences: dict, context: dict = None, num_variations: int = 3):
    """Generate multiple ad variations"""
    variations = []
    for i in range(num_variations):
        try:
            modified_prefs = preferences.copy()
            if i == 0:
                modified_prefs['tone'] = 'Playful'
            elif i == 1:
                modified_prefs['tone'] = 'Professional'
            else:
                modified_prefs['tone'] = 'Urgent'
            ad_text = generate_ad_text(product_info, modified_prefs, context)
            variations.append({
                "variant_name": chr(65 + i),
                "ad_text": ad_text
            })
        except Exception as e:
            print(f"Variation {i} failed: {str(e)}")
            continue
    return variations

@router.post("/generate_ad")
async def generate_ad(request: Request):
    data = await request.json()
    product_info = data.get("product", {})
    preferences = data.get("preferences", {})
    context = data.get("context", {})
    ad_json = generate_ad_text(product_info, preferences, context)
    return {"ad": ad_json, "prompt": build_prompt(context)}
    
@router.post("/generate_ad_variations")
async def generate_ad_variations_endpoint(request: Request):
    data = await request.json()
    product_info = data.get("product", {})
    preferences = data.get("preferences", {})
    context = data.get("context", {})
    num_variations = data.get("num_variations", 3)
    variations = generate_ad_variations(product_info, preferences, context, num_variations)
    return {"ad_variations": variations}
