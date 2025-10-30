# backend/api/enhanced_prompt_service.py - COMPLETE FIXED VERSION
# This file fixes all the issues you're experiencing

import os
import base64
import google.generativeai as genai
from typing import Dict, Optional
import logging
import json

logger = logging.getLogger(__name__)

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


async def generate_optimized_prompt_with_reasoning(
    product_info: Dict,
    user_preferences: Dict,
    mcp_context: Optional[Dict] = None,
    reference_image_analysis: Optional[Dict] = None
) -> Dict:
    """
    FIXED VERSION - Generates optimized prompt with MCP integration
    
    Returns:
        Dict with:
        - final_prompt: Complete prompt WITH MCP context
        - reasoning: Detailed explanation
        - confidence_score: 0-100
        - key_decisions: List of decisions made
    """
    try:
        # ========== CRITICAL FIX: Use correct model name ==========
        model = genai.GenerativeModel('gemini-pro')  # NOT gemini-1.5-pro!
        
        # ========== BUILD CONTEXT WITH MCP ==========
        context_parts = []
        
        # 1. Product Info
        context_parts.append(f"PRODUCT:")
        context_parts.append(f"- Name: {product_info.get('name', 'Fashion Item')}")
        context_parts.append(f"- Type: {product_info.get('type', 'Clothing')}")
        context_parts.append(f"- Color: {product_info.get('color', 'Not specified')}")
        context_parts.append(f"- Material: {product_info.get('material', 'Not specified')}")
        context_parts.append(f"- Collection: {product_info.get('collection', 'Not specified')}")
        
        # 2. User Preferences
        context_parts.append(f"\nUSER PREFERENCES:")
        context_parts.append(f"- Style: {user_preferences.get('style', 'modern')}")
        context_parts.append(f"- Theme: {user_preferences.get('theme', 'elegant')}")
        context_parts.append(f"- Tone: {user_preferences.get('tone', 'professional')}")
        context_parts.append(f"- Platform: {user_preferences.get('platform', 'Instagram')}")
        
        # 3. MCP Context (CRITICAL - This is what integrates context!)
        if mcp_context:
            context_parts.append(f"\nMCP MARKET CONTEXT:")
            
            if 'geo' in mcp_context:
                geo = mcp_context['geo']
                context_parts.append(f"- Target Location: {geo.get('city')}, {geo.get('country')}")
                context_parts.append(f"- Regional Trend: {geo.get('fashion_trend', 'Contemporary')}")
                context_parts.append(f"- Market Demographics: {geo.get('city')} fashion enthusiasts")
            
            if 'weather' in mcp_context:
                weather = mcp_context['weather']
                context_parts.append(f"- Current Weather: {weather.get('condition')} at {weather.get('temperature')}°C")
                context_parts.append(f"- Season Consideration: {_get_season_from_temp(weather.get('temperature', 20))}")
            
            if 'social' in mcp_context:
                social = mcp_context['social']
                hashtags = social.get('trending_hashtags', [])
                if hashtags:
                    context_parts.append(f"- Trending: {', '.join(hashtags[:3])}")
        
        context = "\n".join(context_parts)
        
        # ========== GEMINI PROMPT FOR OPTIMIZATION ==========
        gemini_prompt = f"""You are an expert fashion advertising AI. Create an optimized image generation prompt.

{context}

TASK: Generate a detailed Vertex AI Imagen prompt that:
1. Uses EXACT product color: "{product_info.get('color', 'default')}"
2. Matches {user_preferences.get('style', 'modern')} style
3. Considers the weather ({mcp_context['weather']['temperature']}°C if available)
4. Appeals to {mcp_context['geo']['city'] if mcp_context and 'geo' in mcp_context else 'global'} market
5. Optimized for {user_preferences.get('platform', 'social media')}

Return ONLY valid JSON (no markdown):
{{
    "final_prompt": "Professional fashion advertisement photo of [COLOR] [PRODUCT], [MATERIAL], [STYLE] [THEME] aesthetic, shot in [LOCATION STYLE], [WEATHER-APPROPRIATE STYLING], high-end product photography, studio lighting, clean background, optimized for [PLATFORM]",
    "reasoning": {{
        "color_preservation": "Used exact user color: {product_info.get('color')}",
        "style_choice": "Explanation of style choice",
        "weather_adaptation": "How weather influenced the styling",
        "market_localization": "Why this works for target market",
        "platform_optimization": "How it's optimized for platform"
    }},
    "confidence_score": 85,
    "key_decisions": ["Decision 1", "Decision 2", "Decision 3"]
}}"""
        
        # ========== CALL GEMINI ==========
        logger.info("🧠 Calling Gemini Pro for prompt optimization...")
        response = model.generate_content(gemini_prompt)
        result_text = response.text.strip()
        
        # ========== PARSE JSON RESPONSE ==========
        # Clean markdown formatting if present
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()
        
        result = json.loads(result_text)
        
        logger.info(f"✅ Gemini optimization complete - Confidence: {result.get('confidence_score', 0)}%")
        logger.info(f"📝 Reasoning keys: {list(result.get('reasoning', {}).keys())}")
        
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {str(e)}")
        logger.error(f"Response text: {result_text[:500]}")
        return _create_fallback_with_mcp(product_info, user_preferences, mcp_context)
        
    except Exception as e:
        logger.error(f"Prompt optimization failed: {str(e)}")
        return _create_fallback_with_mcp(product_info, user_preferences, mcp_context)


def _create_fallback_with_mcp(
    product_info: Dict,
    user_preferences: Dict,
    mcp_context: Optional[Dict] = None
) -> Dict:
    """
    IMPROVED FALLBACK - Actually integrates MCP context
    """
    
    # Base prompt
    color = product_info.get('color', 'elegant')
    name = product_info.get('name', 'fashion item')
    material = product_info.get('material', 'premium fabric')
    style = user_preferences.get('style', 'modern')
    theme = user_preferences.get('theme', 'elegant')
    
    # Start building contextualized prompt
    prompt_parts = [
        f"Professional fashion advertisement photo of {color} {name}",
        f"{material} material",
        f"{style} {theme} aesthetic"
    ]
    
    # ADD MCP CONTEXT TO PROMPT
    if mcp_context:
        if 'weather' in mcp_context:
            temp = mcp_context['weather'].get('temperature', 20)
            if temp < 15:
                prompt_parts.append("layered for cool weather")
            elif temp > 25:
                prompt_parts.append("light and breathable styling")
            else:
                prompt_parts.append("versatile seasonal styling")
        
        if 'geo' in mcp_context:
            city = mcp_context['geo'].get('city', 'urban')
            trend = mcp_context['geo'].get('fashion_trend', 'contemporary')
            prompt_parts.append(f"{city} {trend} fashion style")
    
    # Complete prompt
    prompt_parts.extend([
        "high-end product photography",
        "studio lighting",
        "clean background",
        f"optimized for {user_preferences.get('platform', 'social media')}"
    ])
    
    final_prompt = ", ".join(prompt_parts)
    
    # Build reasoning
    reasoning = {
        "color_preservation": f"Using exact user-specified color: {color}",
        "style_choice": f"Applied {style} style for {theme} theme",
        "fallback_note": "Using enhanced fallback with MCP integration"
    }
    
    if mcp_context:
        if 'weather' in mcp_context:
            reasoning["weather_adaptation"] = f"Adapted for {mcp_context['weather'].get('temperature')}°C conditions"
        if 'geo' in mcp_context:
            reasoning["market_localization"] = f"Optimized for {mcp_context['geo'].get('city')} market"
    
    return {
        "final_prompt": final_prompt,
        "reasoning": reasoning,
        "confidence_score": 70,  # Higher than before because MCP is integrated
        "key_decisions": [
            "Preserved exact product color",
            "Integrated MCP weather context" if mcp_context else "No MCP context available",
            "Platform-optimized composition"
        ]
    }


def _get_season_from_temp(temp: float) -> str:
    """Helper to determine season from temperature"""
    if temp < 10:
        return "Winter styling"
    elif temp < 18:
        return "Spring/Fall transition"
    elif temp < 25:
        return "Comfortable Spring/Fall"
    else:
        return "Summer styling"


# ========== REFERENCE IMAGE ANALYSIS (Optional) ==========
async def analyze_reference_image(image_base64: str) -> Dict:
    """
    Analyzes reference image using Gemini Vision
    Returns: style, colors, mood, composition insights
    """
    try:
        if not GEMINI_API_KEY:
            logger.warning("No Gemini API key - skipping image analysis")
            return {}
        
        # Gemini Vision model
        model = genai.GenerativeModel('gemini-pro-vision')
        
        # Decode image
        image_data = base64.b64decode(image_base64)
        
        # Analyze
        prompt = """Analyze this fashion product image and return ONLY valid JSON:
{
    "style": "modern/vintage/classic/edgy",
    "colors": ["primary color", "secondary color"],
    "mood": "elegant/playful/bold/minimal",
    "composition": "close-up/full-body/lifestyle",
    "lighting": "studio/natural/dramatic"
}"""
        
        response = model.generate_content([prompt, {"mime_type": "image/jpeg", "data": image_data}])
        result_text = response.text.strip()
        
        # Parse
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        
        analysis = json.loads(result_text)
        logger.info(f"✅ Image analysis complete: {analysis.get('style')} style")
        
        return analysis
        
    except Exception as e:
        logger.error(f"Image analysis failed: {str(e)}")
        return {
            "style": "contemporary",
            "colors": ["neutral"],
            "mood": "elegant",
            "note": "Fallback analysis"
        }
