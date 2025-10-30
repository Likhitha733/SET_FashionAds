from PIL import Image, ImageDraw, ImageFont
import io
import base64

def create_ad_composite(ad_text: dict, image_base64: str, width: int = 1080, height: int = 1080):
    """
    Create composite ad image with text overlay
    """
    try:
        # Decode image
        image_data = base64.b64decode(image_base64)
        img = Image.open(io.BytesIO(image_data))
        
        # Resize to target dimensions
        img = img.resize((width, height), Image.Resampling.LANCZOS)
        
        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Create drawing context
        draw = ImageDraw.Draw(img)
        
        # Use default font (PIL's built-in font)
        font_headline = ImageFont.load_default()
        font_text = ImageFont.load_default()
        
        # Extract text
        headline = ad_text.get("headline", "")
        tagline = ad_text.get("tagline", "")
        cta = ad_text.get("cta", "")
        
        # Create semi-transparent overlay at bottom
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rectangle(
            [(0, height - 250), (width, height)],
            fill=(0, 0, 0, 180)
        )
        
        # Composite overlay
        img_rgba = img.convert('RGBA')
        img = Image.alpha_composite(img_rgba, overlay).convert('RGB')
        
        # Re-create draw
        draw = ImageDraw.Draw(img)
        
        # Draw text (white color)
        y_pos = height - 230
        if headline:
            draw.text((40, y_pos), headline[:60], fill=(255, 255, 255), font=font_headline)
            y_pos += 60
        
        if tagline:
            draw.text((40, y_pos), tagline[:60], fill=(200, 200, 200), font=font_text)
            y_pos += 60
        
        if cta:
            draw.text((40, y_pos), cta[:40], fill=(100, 200, 255), font=font_text)
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return base64.b64encode(buffer.getvalue()).decode()
    
    except Exception as e:
        print(f"Composite creation error: {str(e)}")
        raise Exception(f"Failed to create composite: {str(e)}")


def image_base64_to_bytes(image_base64: str):
    """Convert base64 image to bytes"""
    return base64.b64decode(image_base64)
