import streamlit as st
import requests

st.title("Fashion Ad Generator")

# User Input Form
product_name = st.text_input("Product Name")
product_type = st.selectbox("Product Type", ["Shirt", "Dress", "Shoes", "Jacket", "Bag"])
color = st.text_input("Color")
material = st.text_input("Material")
collection = st.text_input("Collection/Season")
style = st.selectbox("Style", ["Minimalist", "Bold", "Vintage", "Streetwear", "Luxury"])
tone = st.selectbox("Tone", ["Playful", "Edgy", "Sophisticated"])
platform = st.selectbox("Platform", ["Instagram", "TikTok", "Billboard"])

# Generate Ad Button
if st.button("Generate Advertisement"):
    # Compose your payload
    data = {
        "product": {
            "name": product_name,
            "type": product_type,
            "color": color,
            "material": material,
            "collection": collection
        },
        "preferences": {
            "style": style,
            "theme": tone,  # For now
            "tone": tone,
            "target_audience": "Fashion lovers",
            "platform": platform,
            "tagline_max_words": 8
        },
        "constraints": {},
        "reference_images": []
    }
    # Call backend (when implemented)
    # response = requests.post("http://localhost:8000/api/generate-ad", json=data)
    # st.write(response.json())
    st.write(data)
