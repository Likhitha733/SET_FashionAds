import base64
from PIL import Image
import io

def process_uploaded_image(image_base64: str, max_size=(512, 512)):
    """
    Process and resize uploaded reference image
    
    Args:
        image_base64: Base64 encoded image
        max_size: Maximum dimensions (width, height)
    
    Returns:
        Processed base64 string
    """
    try:
        # Decode image
        image_data = base64.b64decode(image_base64)
        img = Image.open(io.BytesIO(image_data))
        
        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize if larger than max_size
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Convert back to base64
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        buffer.seek(0)
        return base64.b64encode(buffer.getvalue()).decode()
    
    except Exception as e:
        print(f"Image processing error: {str(e)}")
        return None


def enhance_prompt_with_reference(base_prompt: str, has_reference: bool):
    """
    Enhance image generation prompt when reference images exist
    """
    if has_reference:
        return f"{base_prompt}, inspired by reference style, matching aesthetic and composition"
    return base_prompt
