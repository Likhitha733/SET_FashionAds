import streamlit as st
import base64
from PIL import Image
import io
import json
import requests
import plotly
import numpy as np
import random

# Import Plotly for interactive charts
try:
    import plotly.graph_objects as go
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

from api import *

# ==================== PAGE CONFIG ====================
st.set_page_config(
    page_title="Fashion Ad Generator",
    page_icon="👗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== ENHANCED CSS ====================
st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
        font-weight: 600;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
    }
    
    /* MCP Context Cards */
    .mcp-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 12px;
        margin: 10px 0;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        text-align: center;
    }
    .mcp-card h4 {
        margin: 0 0 10px 0;
        font-size: 14px;
        opacity: 0.9;
        font-weight: 600;
    }
    .mcp-card p {
        margin: 0;
        font-size: 18px;
        font-weight: 700;
    }
    
    /* Prompt Evolution Box */
    .prompt-box {
        background: #f0f2f6;
        padding: 15px;
        border-left: 4px solid #667eea;
        border-radius: 8px;
        margin: 10px 0;
        font-family: 'Courier New', monospace;
        font-size: 13px;
        line-height: 1.6;
    }
    
    .ad-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin: 10px 0;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 12px;
        text-align: center;
    }
    
    .success-banner {
        background: #d4edda;
        color: #155724;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #28a745;
        margin: 10px 0;
    }
    
    .usage-warning {
        background: #fff3cd;
        color: #856404;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #ffc107;
        margin: 10px 0;
    }
    
    .confidence-badge {
        background: #10b981;
        color: white;
        padding: 5px 15px;
        border-radius: 20px;
        font-weight: 700;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# ==================== SESSION STATE ====================
for k in ["token", "username", "generated_ad", "generated_image", "current_ad_id",
          "uploaded_reference", "selected_ads", "mcp_context", "prompts", "ai_reasoning"]:
    if k not in st.session_state:
        st.session_state[k] = None if k != "selected_ads" else []

def logout():
    for k in ["token", "username", "generated_ad", "generated_image", "uploaded_reference",
              "selected_ads", "mcp_context", "prompts", "ai_reasoning"]:
        st.session_state[k] = None if k != "selected_ads" else []
    st.rerun()

# ==================== HEADER ====================
st.title("👗 Fashion Ad Generator")
st.markdown("### AI-Powered Fashion Marketing with MCP Intelligence")

# ==================== SIDEBAR ====================
with st.sidebar:
    if st.session_state.token:
        st.success(f"✅ Logged in as **{st.session_state.username}**")
        if st.button("🚪 Logout", use_container_width=True):
            logout()
        
        st.markdown("---")
        st.markdown("### 📊 Quick Stats")
        try:
            analytics_resp = get_my_analytics(st.session_state.token)
            if analytics_resp.status_code == 200:
                analytics_data = analytics_resp.json()
                
                # Handle both structures
                if "data" in analytics_data and "summary" in analytics_data["data"]:
                    summary = analytics_data["data"]["summary"]
                else:
                    summary = analytics_data
                
                # Custom styled metrics
                st.markdown(f'''
                <div style="
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 15px;
                    border-radius: 10px;
                    margin-bottom: 10px;
                    color: white;
                ">
                    <div style="font-size: 12px; opacity: 0.9;">Total Ads</div>
                    <div style="font-size: 28px; font-weight: bold;">{summary.get("total_ads", 0)}</div>
                </div>
                ''', unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f'''
                    <div style="
                        background: #2d3748;
                        padding: 10px;
                        border-radius: 8px;
                        text-align: center;
                        color: white;
                    ">
                        <div style="font-size: 10px; opacity: 0.8;">Views</div>
                        <div style="font-size: 20px; font-weight: bold;">{summary.get("total_views", 0):,}</div>
                    </div>
                    ''', unsafe_allow_html=True)
                with col2:
                    st.markdown(f'''
                    <div style="
                        background: #2d3748;
                        padding: 10px;
                        border-radius: 8px;
                        text-align: center;
                        color: white;
                    ">
                        <div style="font-size: 10px; opacity: 0.8;">Clicks</div>
                        <div style="font-size: 20px; font-weight: bold;">{summary.get("total_clicks", 0):,}</div>
                    </div>
                    ''', unsafe_allow_html=True)
                
                ctr = summary.get("avg_ctr", 0)
                st.markdown(f'''
                <div style="
                    background: {'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)' if ctr > 5 else '#4a5568'};
                    padding: 10px;
                    border-radius: 8px;
                    text-align: center;
                    color: white;
                    margin-top: 10px;
                ">
                    <div style="font-size: 10px; opacity: 0.9;">Average CTR</div>
                    <div style="font-size: 24px; font-weight: bold;">{ctr:.2f}%</div>
                </div>
                ''', unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Stats error: {str(e)}")

        
        st.markdown("---")
        st.markdown("### 📈 Usage Quota")
        try:
            usage_resp = get_my_usage(st.session_state.token)
            if usage_resp.status_code == 200:
                usage = usage_resp.json()
                quota_used = usage.get("ads_today", 0)
                quota_limit = usage.get("daily_limit", 50)  # ✅ NEW: 50
                percent = (quota_used / quota_limit * 100) if quota_limit > 0 else 0
                
                # Beautiful progress bar
                st.markdown(f'''
                <div style="
                    background: #2d3748;
                    padding: 15px;
                    border-radius: 10px;
                    color: white;
                ">
                    <div style="font-size: 14px; font-weight: bold; margin-bottom: 8px;">
                        Daily Quota
                    </div>
                    <div style="
                        background: #4a5568;
                        height: 20px;
                        border-radius: 10px;
                        overflow: hidden;
                    ">
                        <div style="
                            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
                            height: 100%;
                            width: {min(percent, 100)}%;
                            transition: width 0.5s;
                        "></div>
                    </div>
                    <div style="
                        display: flex;
                        justify-content: space-between;
                        margin-top: 8px;
                        font-size: 12px;
                    ">
                        <span>{quota_used} / {quota_limit} ads</span>
                        <span>{100-percent:.0f}% remaining</span>
                    </div>
                </div>
                ''', unsafe_allow_html=True)
                
                # Monthly quota
                monthly_used = usage.get('ads_this_month', 0)
                monthly_limit = usage.get('monthly_limit', 500)
                monthly_percent = (monthly_used / monthly_limit * 100) if monthly_limit > 0 else 0
                
                st.markdown(f'''
                <div style="
                    background: #1a202c;
                    padding: 10px;
                    border-radius: 8px;
                    color: white;
                    margin-top: 10px;
                    font-size: 11px;
                ">
                    <div><b>Monthly:</b> {monthly_used} / {monthly_limit}</div>
                    <div style="margin-top: 5px;">
                        <div style="background: #4a5568; height: 8px; border-radius: 4px;">
                            <div style="
                                background: #fbbf24;
                                height: 100%;
                                width: {min(monthly_percent, 100)}%;
                            "></div>
                        </div>
                    </div>
                </div>
                ''', unsafe_allow_html=True)
                
                if percent > 90:
                    st.error("⚠️ Almost at limit!")
                elif percent > 75:
                    st.warning(f"⚠️ {100-percent:.0f}% left")
        except Exception as e:
            st.caption(f"Quota: 0/50 today")

        
        st.markdown("---")
        page = st.radio(
            "Navigation",
            ["🎨 Create Ad", "📋 My Ads", "🔍 Search Ads", "🧪 A/B Testing",
             "🧑‍🦰 Virtual Try-On", "📊 Analytics", "📁 Templates"]
        )
    else:
        st.info("Please login or register to continue")
        page = None

# ==================== AUTHENTICATION ====================
if not st.session_state.token:
    tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])
    
    with tab1:
        st.markdown("### Login to Your Account")
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login", key="login_btn", use_container_width=True):
            if username and password:
                resp = login(username, password)
                if resp.status_code == 200:
                    st.session_state.token = resp.json()["access_token"]
                    st.session_state.username = username
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error(resp.json().get("detail", "Login failed"))
            else:
                st.warning("Please fill in all fields")
    
    with tab2:
        st.markdown("### Create New Account")
        username = st.text_input("Username", key="reg_username")
        password = st.text_input("Password", type="password", key="reg_password")
        password2 = st.text_input("Confirm Password", type="password", key="reg_password2")
        if st.button("Register", key="reg_btn", use_container_width=True):
            if username and password and password2:
                if password != password2:
                    st.error("Passwords don't match")
                elif len(password) < 6:
                    st.error("Password must be at least 6 characters")
                else:
                    resp = register(username, password)
                    if resp.status_code == 200:
                        st.success("Registration successful! Please login.")
                    else:
                        st.error(resp.json().get("detail", "Registration failed"))
            else:
                st.warning("Please fill in all fields")

# ==================== CREATE AD PAGE ====================
elif page == "🎨 Create Ad":
    st.markdown("## 🎨 Create New Advertisement")
    
    st.markdown("#### 📸 Reference Image (Optional)")
    uploaded_file = st.file_uploader("Upload a product image to use as reference", type=["jpg", "jpeg", "png"])
    if uploaded_file:
        try:
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded Reference Image", width=200)
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            st.session_state.uploaded_reference = img_str
            st.success("✅ Reference image uploaded!")
        except Exception as e:
            st.error(f"Error uploading image: {str(e)}")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("#### 👔 Product Information")
        product_name = st.text_input("Product Name", placeholder="e.g., Summer Dress")
        product_type = st.text_input("Product Type", placeholder="e.g., Dress, Jacket, Shoes")
        col_a, col_b = st.columns(2)
        with col_a:
            color = st.text_input("Color", placeholder="e.g., Red")
        with col_b:
            material = st.text_input("Material", placeholder="e.g., Cotton")
        collection = st.text_input("Collection", placeholder="e.g., Spring 2024")
    
    with col2:
        st.markdown("#### 🎯 Ad Preferences")
        style = st.selectbox("Style", ["Minimalist", "Bold", "Elegant", "Edgy", "Casual", "Luxurious"])
        theme = st.selectbox("Theme", ["Playful", "Sophisticated", "Romantic", "Urban", "Vintage", "Futuristic"])
        tone = st.selectbox("Tone", ["Playful", "Professional", "Urgent", "Casual", "Inspirational"])
        target_audience = st.text_input("Target Audience", value="Fashion lovers")
        platform = st.selectbox("Platform", ["Instagram", "Facebook", "Pinterest", "Twitter", "TikTok"])
        tagline_max_words = st.slider("Tagline Length (words)", 3, 10, 6)
    
    if st.button("✨ Generate Advertisement with MCP", use_container_width=True, type="primary"):
        if not all([product_name, product_type, color, material, collection]):
            st.error("Please fill in all product information")
        else:
            with st.spinner("🎨 Creating your fashion ad with context intelligence..."):
                payload = {
                    "product": {
                        "name": product_name,
                        "type": product_type,
                        "color": color,
                        "material": material,
                        "collection": collection
                    },
                    "preferences": {
                        "style": style,
                        "theme": theme,
                        "tone": tone,
                        "target_audience": target_audience,
                        "platform": platform,
                        "tagline_max_words": tagline_max_words
                    },
                    "constraints": {
                        "color_palette": [],
                        "brand_voice": "",
                        "avoid_elements": []
                    }
                }
                if st.session_state.uploaded_reference:
                    payload["reference_image"] = st.session_state.uploaded_reference
                
                resp = generate_ad_with_image(payload, st.session_state.token)
                
                if resp.status_code == 200:
                    data = resp.json()
                    st.session_state.generated_ad = data["ad_text"]
                    st.session_state.generated_image = data.get("image")
                    st.session_state.current_ad_id = data.get("ad_id")
                    st.session_state.mcp_context = data.get("context")
                    st.session_state.prompts = data.get("prompts")
                    st.session_state.ai_reasoning = data.get("ai_reasoning")
                    st.markdown('<div class="success-banner">✅ Advertisement generated successfully with MCP!</div>', unsafe_allow_html=True)
                    st.rerun()
                elif resp.status_code == 429:
                    st.error("⚠️ Quota exceeded! You've reached your daily limit.")
                else:
                    st.error(f"Error: {resp.json().get('detail', 'Unknown error')}")
    
    # ========== DISPLAY GENERATED AD WITH MCP ==========
    if st.session_state.generated_ad:
        st.markdown("---")
        st.markdown("## 📝 Your Generated Ad")
        
        # MCP Context Display
        if st.session_state.mcp_context:
            mcp_data = st.session_state.mcp_context.get("mcp_data", {})
            if mcp_data:
                st.markdown("### 🌍 MCP Context Intelligence")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    location = mcp_data.get('location', 'N/A')
                    st.markdown(f"""
                    <div class='mcp-card'>
                        <h4>📍 Target Market</h4>
                        <p>{location}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    weather = mcp_data.get('weather', 'N/A')
                    st.markdown(f"""
                    <div class='mcp-card'>
                        <h4>🌡️ Weather Context</h4>
                        <p>{weather}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    trend = mcp_data.get('trend', 'N/A')
                    st.markdown(f"""
                    <div class='mcp-card'>
                        <h4>📈 Fashion Trend</h4>
                        <p>{trend}</p>
                    </div>
                    """, unsafe_allow_html=True)
        
        # Prompt Evolution Display
        if st.session_state.prompts and isinstance(st.session_state.prompts, dict):
            with st.expander("🧠 AI Prompt Evolution (MCP Enhancement)", expanded=False):
                col1, col2 = st.columns(2)
                prompts = st.session_state.prompts
                with col1:
                    st.markdown("**📝 Basic Prompt:**")
                    basic_prompt = st.session_state.prompts.get("basic", "No basic prompt available")
                    st.markdown(f'''
                    <div style="
                        background: #2d3748; 
                        color: #e2e8f0; 
                        padding: 15px; 
                        border-radius: 10px;
                        border: 2px solid #4a5568;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
                        font-family: 'Segoe UI', sans-serif;
                    ">
                        {basic_prompt}
                    </div>
                    ''', unsafe_allow_html=True)
                with col2:
                    st.markdown("**✨ MCP Enhanced Prompt:**")
                    enhanced_prompt = st.session_state.prompts.get("enhanced", st.session_state.prompts.get("basic", "No enhanced prompt available"))
                    st.markdown(f'''
                    <div style="
                        background: #1a202c; 
                        color: #fbbf24; 
                        padding: 15px; 
                        border-radius: 10px;
                        border: 2px solid #f59e0b;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
                        font-family: 'Segoe UI', sans-serif;
                    ">
                        {enhanced_prompt}
                    </div>
                    ''', unsafe_allow_html=True)


                st.markdown("#### MCP Context")
                mcp_ctx = prompts.get('mcp_context_data', {})
                if mcp_ctx:
                    st.info(f"📍 {mcp_ctx.get('location')} | 🌡️ {mcp_ctx.get('weather')} | 📈 {mcp_ctx.get('trend')}")
                
                if st.session_state.ai_reasoning:
                    with st.expander("🧠 See AI Reasoning", expanded=False):
                        st.markdown(f'''
                        <div style="
                            background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); 
                            color: #1a202c; 
                            padding: 20px; 
                            border-radius: 10px;
                            border: 2px solid #90cdf4;
                            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                            font-family: 'Segoe UI', sans-serif;
                            line-height: 1.6;
                        ">
                            {st.session_state.ai_reasoning}
                        </div>
                        ''', unsafe_allow_html=True)

        
        st.markdown("---")
        
        # Ad Display
        col1, col2 = st.columns([1, 1])
        
        with col1:
            ad = st.session_state.generated_ad
            st.markdown('<div class="ad-card">', unsafe_allow_html=True)
            st.markdown(f"### {ad.get('headline', 'N/A')}")
            st.markdown(f"**Tagline:** {ad.get('tagline', 'N/A')}")
            st.markdown(f"**Body Copy:**\n\n{ad.get('body_copy', 'N/A')}")
            st.markdown(f"**CTA:** {ad.get('cta', 'N/A')}")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            if st.session_state.generated_image:
                try:
                    img_data = base64.b64decode(st.session_state.generated_image)
                    img = Image.open(io.BytesIO(img_data))
                    st.image(img, use_container_width=True, caption="Generated Image")
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.download_button(
                            "📥 Download Image",
                            data=img_data,
                            file_name=f"fashion_ad_{st.session_state.username}.png",
                            mime="image/png",
                            use_container_width=True
                        )
                    with col_b:
                        if st.button("📥 Download Composite", use_container_width=True):
                            export_resp = requests.post(
                                "http://localhost:8000/api/export-ad",
                                json={
                                    "ad_text": st.session_state.generated_ad,
                                    "image": st.session_state.generated_image,
                                    "format": "composite"
                                },
                                headers={"Authorization": f"Bearer {st.session_state.token}"}
                            )
                            if export_resp.status_code == 200:
                                st.download_button(
                                    "Download",
                                    data=export_resp.content,
                                    file_name=f"composite_{st.session_state.username}.png",
                                    mime="image/png",
                                )
                except Exception as e:
                    st.error(f"Image display error: {str(e)}")

# ==================== VIRTUAL TRY-ON ====================
elif page == "🧑‍🦰 Virtual Try-On":
    st.markdown("## 👚 Virtual Try-On")
    user_photo = st.file_uploader("Upload Your Photo", type=["jpg","jpeg","png"], key="user_photo_tryon")
    product_photo = st.file_uploader("Upload Garment/Clothes Photo", type=["jpg","jpeg","png"], key="garment_photo_tryon")
    
    if st.button("👕 Try On Now!", use_container_width=True, type="primary"):
        if user_photo and product_photo:
            with st.spinner("Sending to virtual try-on AI..."):
                resp = tryon(user_photo, product_photo, st.session_state.token)
                if resp.status_code == 200:
                    result = resp.json()
                    img_data = base64.b64decode(result["result_image_b64"])
                    st.image(img_data, caption="AI Try-On Result", use_container_width=True)
                else:
                    st.error(f"Try-on failed: {resp.text}")
        else:
            st.warning("Please upload both your photo and product image")

# ==================== ANALYTICS PAGE ====================
elif page == "📊 Analytics":
    st.markdown("## 📊 Comprehensive Analytics Dashboard")
    
    # Fetch analytics
    with st.spinner("Loading analytics data..."):
        try:
            analytics_resp = get_my_analytics(st.session_state.token)
            if analytics_resp.status_code == 200:
                analytics = analytics_resp.json()

                # Debug: Print response to see structure
                st.write("DEBUG - Response:", analytics)

                # Handle different response structures
                if "data" in analytics:
                    data = analytics["data"]
                elif "success" in analytics and analytics["success"]:
                    data = analytics.get("data", analytics)
                else:
                    # Fallback: use the response directly if it contains the data
                    data = analytics

                
                # Summary Metrics
                st.markdown("### 📈 Performance Summary")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Ads", data['summary']['total_ads'])
                with col2:
                    st.metric("Total Views", f"{data['summary']['total_views']:,}")
                with col3:
                    st.metric("Total Clicks", f"{data['summary']['total_clicks']:,}")
                with col4:
                    st.metric("Conversions", f"{data['summary']['total_conversions']:,}")
                
                # Time Series Chart
                if PLOTLY_AVAILABLE:
                    st.markdown("### 📅 Performance Over Time")
                    import pandas as pd
                    time_data = pd.DataFrame({
                        'Date': data['time_series']['dates'],
                        'Views': data['time_series']['views'],
                        'Clicks': data['time_series']['clicks'],
                        'Conversions': data['time_series']['conversions']
                    })
                    
                    fig = px.line(time_data, x='Date', y=['Views', 'Clicks', 'Conversions'],
                                  title="30-Day Performance Trend")
                    st.plotly_chart(fig, use_container_width=True)
                
                # Platform Breakdown
                st.markdown("### 🎯 Platform Performance")
                col1, col2 = st.columns(2)
                
                if PLOTLY_AVAILABLE:
                    with col1:
                        # Platform views pie chart
                        platform_views = {k: v['Views'] for k, v in data['platforms'].items()}
                        fig_pie = px.pie(values=list(platform_views.values()), 
                                         names=list(platform_views.keys()),
                                         title="Views by Platform")
                        st.plotly_chart(fig_pie, use_container_width=True)
                    
                    with col2:
                        # Platform conversions bar chart
                        platform_conv = {k: v['Conversions'] for k, v in data['platforms'].items()}
                        fig_bar = px.bar(x=list(platform_conv.keys()), 
                                        y=list(platform_conv.values()),
                                        title="Conversions by Platform")
                        st.plotly_chart(fig_bar, use_container_width=True)
                
                # Top Performing Ads
                st.markdown("### 🏆 Top Performing Ads")
                import pandas as pd
                top_ads = pd.DataFrame(data['top_performing'])
                st.dataframe(top_ads, use_container_width=True)
                
                # Product Performance
                st.markdown("### 🛍️ Product Category Analysis")
                product_data = pd.DataFrame([
                    {
                        'Product': k,
                        'Avg Views': v['Views'],
                        'Avg CTR': v['CTR (%)'],
                        'Avg CVR': v['CVR (%)']
                    }
                    for k, v in data['products'].items()
                ])
                st.dataframe(product_data.sort_values('Avg CTR', ascending=False), 
                            use_container_width=True)
                
                # Feature Adoption
                if PLOTLY_AVAILABLE:
                    st.markdown("### 🎨 Feature Adoption Rates")
                    feature_data = pd.DataFrame(data['feature_adoption'])
                    fig_features = px.bar(feature_data, x='Feature', y='Adoption Rate (%)',
                                         title="Feature Usage by Users",
                                         color='Adoption Rate (%)')
                    st.plotly_chart(fig_features, use_container_width=True)
                
            else:
                st.error("Failed to load analytics data")
        except Exception as e:
            st.error(f"Error loading analytics: {str(e)}")


# ==================== MY ADS ====================
elif page == "📋 My Ads":
    st.markdown("## 📋 My Advertisements")
    st.markdown("Manage all your generated ads in one place")
    
    # Bulk operations section
    st.markdown("### 🔧 Bulk Operations")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🗑️ Delete Selected", use_container_width=True):
            if st.session_state.selected_ads:
                try:
                    resp = bulk_delete_ads(st.session_state.selected_ads, st.session_state.token)
                    if resp.status_code == 200:
                        deleted_count = resp.json().get('deleted_count', len(st.session_state.selected_ads))
                        st.success(f"✅ Deleted {deleted_count} ads successfully")
                        st.session_state.selected_ads.clear()
                        st.rerun()
                    else:
                        st.error("❌ Failed to delete ads")
                except Exception as e:
                    st.error(f"Delete error: {str(e)}")
            else:
                st.warning("⚠️ No ads selected. Check boxes below to select ads.")
    
    with col2:
        if st.button("📥 Export Selected", use_container_width=True):
            if st.session_state.selected_ads:
                try:
                    resp = bulk_export_ads(st.session_state.selected_ads, st.session_state.token)
                    if resp.status_code == 200:
                        data = resp.json()
                        ads_export = data.get('ads', [])
                        
                        st.download_button(
                            label="💾 Download JSON",
                            data=json.dumps(ads_export, indent=2),
                            file_name=f"ads_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json",
                            use_container_width=True
                        )
                        st.success(f"✅ Prepared {len(ads_export)} ads for download")
                    else:
                        st.error("❌ Export failed")
                except Exception as e:
                    st.error(f"Export error: {str(e)}")
            else:
                st.warning("⚠️ No ads selected")
    
    with col3:
        if st.button("🔄 Refresh Metrics", use_container_width=True):
            st.rerun()
    
    st.markdown("---")
    
    # Load and display ads
    try:
        # Use direct HTTP call to the backend if helper function is not available
        resp = requests.get(
            "http://localhost:8000/api/my-ads",
            headers={"Authorization": f"Bearer {st.session_state.token}"}
        )
        
        if resp.status_code == 200:
            ads_data = resp.json()
            ads = ads_data.get("ads", [])
            
            if not ads:
                st.info("📭 No ads yet. Create your first ad to see it here!")
                if st.button("➕ Create First Ad", type="primary"):
                    st.session_state.page = "🎨 Create Ad"
                    st.rerun()
            else:
                st.success(f"📊 Found {len(ads)} ads")
                
                # Filter and sort options
                col_filter, col_sort = st.columns([1, 1])
                with col_filter:
                    filter_option = st.selectbox(
                        "Filter by",
                        ["All Ads", "High Performers (CTR > 5%)", "Recent (Last 7 days)"],
                        key="ads_filter"
                    )
                with col_sort:
                    sort_option = st.selectbox(
                        "Sort by",
                        ["Newest First", "Oldest First", "Highest CTR", "Most Views"],
                        key="ads_sort"
                    )
                
                # Apply filters and sorting
                filtered_ads = ads.copy()
                
                if filter_option == "High Performers (CTR > 5%)":
                    filtered_ads = [ad for ad in filtered_ads if ad.get('ctr', 0) > 5.0]
                elif filter_option == "Recent (Last 7 days)":
                    from datetime import datetime, timedelta
                    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
                    filtered_ads = [ad for ad in filtered_ads if ad.get('created_at', '') > week_ago]
                
                # Apply sorting
                if sort_option == "Newest First":
                    filtered_ads.sort(key=lambda x: x.get('created_at', ''), reverse=True)
                elif sort_option == "Oldest First":
                    filtered_ads.sort(key=lambda x: x.get('created_at', ''))
                elif sort_option == "Highest CTR":
                    filtered_ads.sort(key=lambda x: x.get('ctr', 0), reverse=True)
                elif sort_option == "Most Views":
                    filtered_ads.sort(key=lambda x: x.get('views', 0), reverse=True)
                
                st.markdown(f"*Showing {len(filtered_ads)} of {len(ads)} ads*")
                
                # Display ads
                for ad in filtered_ads:
                    ad_id = ad.get('id')
                    created_date = ad.get('created_at', 'Unknown')[:10]
                    ctr = ad.get('ctr', 0)
                    
                    # Performance indicator
                    if ctr > 7:
                        performance = "🟢 Excellent"
                        perf_color = "green"
                    elif ctr > 4:
                        performance = "🟡 Good"
                        perf_color = "orange"
                    else:
                        performance = "🔴 Needs Improvement"
                        perf_color = "red"
                    
                    with st.expander(f"Ad #{ad_id} - {created_date} | {performance} (CTR: {ctr:.2f}%)", expanded=False):
                        # Selection checkbox
                        col_check, col_content = st.columns([0.1, 0.9])
                        
                        with col_check:
                            is_selected = st.checkbox(
                                "Select",
                                key=f"select_ad_{ad_id}",
                                value=ad_id in st.session_state.selected_ads
                            )
                            
                            if is_selected and ad_id not in st.session_state.selected_ads:
                                st.session_state.selected_ads.append(ad_id)
                            elif not is_selected and ad_id in st.session_state.selected_ads:
                                st.session_state.selected_ads.remove(ad_id)
                        
                        with col_content:
                            col_img, col_details = st.columns([1, 2])
                            
                            # Display image
                            with col_img:
                                if ad.get("image_b64"):
                                    try:
                                        st.image(
                                            f"data:image/png;base64,{ad['image_b64']}", 
                                            caption=f"Ad #{ad_id}",
                                            use_column_width=True
                                        )
                                    except Exception as img_error:
                                        st.error("🖼️ Image display error")
                                else:
                                    st.info("📷 No image available")
                            
                            # Display details and metrics
                            with col_details:
                                # Ad copy
                                ad_text = ad.get('ad_text', 'No text available')
                                
                                # Parse if JSON string
                                if isinstance(ad_text, str) and ad_text.startswith('{'):
                                    try:
                                        ad_json = json.loads(ad_text)
                                        st.markdown(f"**📌 Headline:** {ad_json.get('headline', 'N/A')}")
                                        st.markdown(f"**✨ Tagline:** {ad_json.get('tagline', 'N/A')}")
                                        st.markdown(f"**📝 Body:** {ad_json.get('body_copy', 'N/A')[:100]}...")
                                    except:
                                        st.markdown(f"**Ad Copy:** {ad_text[:150]}...")
                                else:
                                    st.markdown(f"**Ad Copy:** {ad_text[:150]}...")
                                
                                st.markdown(f"**📅 Created:** {created_date}")
                                
                                # Performance metrics
                                st.markdown("### 📊 Performance Metrics")
                                
                                col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                                
                                with col_m1:
                                    st.metric(
                                        "👁️ Views",
                                        f"{ad.get('views', 0):,}",
                                        delta="Live" if ad.get('views', 0) > 0 else None
                                    )
                                
                                with col_m2:
                                    st.metric(
                                        "🖱️ Clicks",
                                        f"{ad.get('clicks', 0):,}",
                                        delta=f"{ctr:.1f}% CTR"
                                    )
                                
                                with col_m3:
                                    cvr = ad.get('cvr', 0)
                                    st.metric(
                                        "💰 Conversions",
                                        f"{ad.get('conversions', 0):,}",
                                        delta=f"{cvr:.1f}% CVR" if cvr > 0 else None
                                    )
                                
                                with col_m4:
                                    st.metric(
                                        "⭐ CTR Score",
                                        f"{ctr:.2f}%",
                                        delta="High" if ctr > 5 else "Low"
                                    )
                                
                                # Actions
                                st.markdown("### ⚙️ Actions")
                                action_col1, action_col2, action_col3 = st.columns(3)
                                
                                with action_col1:
                                    if st.button("📊 View Details", key=f"details_{ad_id}", use_container_width=True):
                                        st.info("Detailed analytics coming soon!")
                                
                                with action_col2:
                                    if st.button("✏️ Edit", key=f"edit_{ad_id}", use_container_width=True):
                                        st.info("Edit feature coming soon!")
                                
                                with action_col3:
                                    if st.button("🗑️ Delete", key=f"delete_{ad_id}", use_container_width=True, type="secondary"):
                                        st.session_state.selected_ads = [ad_id]
                                        st.rerun()
        
        else:
            st.error(f"❌ Failed to load ads (Status: {resp.status_code})")
            st.caption("Try refreshing the page or check your connection")
    
    except Exception as e:
        st.error(f"❌ Error loading ads: {str(e)}")
        st.caption("Please contact support if this persists")

# ==================== SEARCH ADS ====================
elif page == "🔍 Search Ads":
    st.markdown("## 🔍 Search & Filter Ads")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        search_query = st.text_input("🔎 Search by product name", "")
    with col2:
        platform_filter = st.selectbox("Platform", ["All", "Instagram", "Facebook", "Pinterest", "Twitter", "TikTok"])
    with col3:
        sort_by = st.selectbox("Sort by", ["created_at", "views", "clicks", "ctr"])
    
    min_views = st.slider("Minimum views", 0, 1000, 0)
    
    if st.button("🔍 Search", use_container_width=True):
        try:
            params = {
                "query": search_query,
                "platform": None if platform_filter == "All" else platform_filter,
                "min_views": min_views,
                "sort_by": sort_by,
                "order": "desc"
            }
            resp = requests.get(
                "http://localhost:8000/api/search-ads",
                params=params,
                headers={"Authorization": f"Bearer {st.session_state.token}"}
            )
            if resp.status_code == 200:
                ads = resp.json()
                if not ads:
                    st.info("No ads found matching your criteria.")
                else:
                    st.success(f"Found {len(ads)} ads")
                    for ad in ads:
                        with st.expander(f"Ad #{ad['id']} - CTR: {ad['ctr']:.1f}%"):
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Views", ad['views'])
                            with col2:
                                st.metric("Clicks", ad['clicks'])
                            with col3:
                                st.metric("Conversions", ad['conversions'])
            else:
                st.error("Search failed")
        except Exception as e:
            st.error(f"Error: {str(e)}")

# ==================== A/B TESTING ====================
elif page == "🧪 A/B Testing":
    st.markdown("## 🧪 A/B Testing Lab")
    st.markdown("Generate multiple ad variants and compare performance to optimize campaigns")
    
    # Two-tab interface: Generate Variants | Compare Existing
    tab1, tab2 = st.tabs(["📝 Generate New Variants", "📊 Compare Existing Ads"])
    
    # TAB 1: Generate new A/B test variants
    with tab1:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("#### Product Information")
            product_name = st.text_input("Product Name", placeholder="e.g., Summer Floral Dress", key="ab_product")
            product_type = st.text_input("Product Type", placeholder="e.g., Dress, Shoes, Bag", key="ab_type")
            color = st.text_input("Color", placeholder="e.g., Lavender, Navy Blue", key="ab_color")
            material = st.text_input("Material", placeholder="e.g., Silk, Cotton, Leather", key="ab_material")
            collection = st.text_input("Collection/Season", placeholder="e.g., Spring 2025", key="ab_collection")
        
        with col2:
            st.markdown("#### Test Configuration")
            num_variants = st.slider("Number of Variants to Generate", 2, 4, 3, 
                                     help="More variants = better testing, but takes longer")
            variation_type = st.selectbox(
                "What to Test/Vary",
                ["tone", "length", "cta", "style", "headline"],
                format_func=lambda x: {
                    "tone": "Tone (Formal vs Casual)",
                    "length": "Copy Length (Short vs Long)",
                    "cta": "Call-to-Action Style",
                    "style": "Visual Style",
                    "headline": "Headline Variants"
                }[x],
                help="Choose what aspect to test across variants"
            )
            style = st.selectbox("Base Style", ["Minimalist", "Bold", "Elegant", "Playful"], key="ab_style")
            platform = st.selectbox("Target Platform", ["Instagram", "Facebook", "Pinterest", "TikTok"], key="ab_platform")
        
        if st.button("🧪 Generate A/B Test Variants", use_container_width=True, type="primary"):
            if not all([product_name, product_type, color, material, collection]):
                st.error("⚠️ Please fill in all product fields")
            else:
                with st.spinner(f"🎨 Generating {num_variants} variants with AI..."):
                    try:
                        payload = {
                            "product": {
                                "name": product_name,
                                "type": product_type,
                                "color": color,
                                "material": material,
                                "collection": collection
                            },
                            "preferences": {
                                "style": style,
                                "theme": "Modern",
                                "tone": "Professional",
                                "target_audience": "Fashion lovers",
                                "platform": platform,
                                "tagline_max_words": 6
                            },
                            "num_variants": num_variants,
                            "variation_type": variation_type
                        }
                        
                        resp = requests.post(
                            "http://localhost:8000/api/generate-ab-variants",
                            json=payload,
                            headers={"Authorization": f"Bearer {st.session_state.token}"},
                            timeout=120
                        )
                        
                        if resp.status_code == 200:
                            data = resp.json()
                            variants = data.get('variants', [])
                            
                            st.success(f"✅ Generated {len(variants)} variants successfully!")
                            
                            st.markdown("### 📋 Generated Variants")
                            st.markdown("*Review each variant below. Click 'Save to Ads' to add them to your campaign.*")
                            
                            for idx, variant in enumerate(variants, 1):
                                with st.expander(f"✨ Variant {idx}: {variant.get('variant_name', f'Variant {idx}')}", expanded=(idx==1)):
                                    ad_text = variant.get('ad_text', {})
                                    
                                    col_a, col_b = st.columns([2, 1])
                                    
                                    with col_a:
                                        st.markdown(f"**📌 Headline:** {ad_text.get('headline', 'N/A')}")
                                        st.markdown(f"**✨ Tagline:** {ad_text.get('tagline', 'N/A')}")
                                        st.markdown(f"**📝 Body Copy:**\n{ad_text.get('body_copy', 'N/A')}")
                                        st.markdown(f"**🎯 Call-to-Action:** {ad_text.get('cta', 'Shop Now')}")
                                    
                                    with col_b:
                                        st.markdown("**🎨 Variant Details:**")
                                        st.caption(f"Variation: {variant.get('variation_applied', variation_type.title())}")
                                        st.caption(f"Word Count: {len(ad_text.get('body_copy', '').split())} words")
                                        
                                        if st.button(f"💾 Save Variant {idx}", key=f"save_variant_{idx}", use_container_width=True):
                                            st.info(f"Variant {idx} saved! (Feature coming soon)")
                        else:
                            error_detail = resp.json().get('detail', 'Unknown error')
                            st.error(f"❌ Generation failed: {error_detail}")
                            
                    except requests.exceptions.Timeout:
                        st.error("⏱️ Request timed out. The server might be busy. Please try again.")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
    
    # TAB 2: Compare existing ads
    with tab2:
        st.markdown("### 📊 Compare Existing Ad Performance")
        
        try:
            resp = requests.get(
                "http://localhost:8000/api/my-ads",
                headers={"Authorization": f"Bearer {st.session_state.token}"}
            )
            if resp.status_code == 200:
                ads_data = resp.json()
                ads = ads_data.get("ads", [])
                
                if len(ads) < 2:
                    st.warning("⚠️ You need at least 2 ads to run comparison tests. Create more ads first!")
                else:
                    st.markdown("*Select two ads to compare their performance metrics*")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**🅰️ Variant A:**")
                        ad_a = st.selectbox(
                            "Select first ad",
                            options=ads,
                            format_func=lambda x: f"Ad #{x.get('id')} (CTR: {x.get('ctr', 0):.1f}%)",
                            key="compare_ad_a"
                        )
                        
                        if ad_a:
                            if ad_a.get("image_b64"):
                                st.image(f"data:image/png;base64,{ad_a['image_b64']}", width=250)
                            
                            col_a1, col_a2, col_a3 = st.columns(3)
                            with col_a1:
                                st.metric("Views", f"{ad_a.get('views', 0):,}")
                            with col_a2:
                                st.metric("Clicks", f"{ad_a.get('clicks', 0):,}")
                            with col_a3:
                                st.metric("CTR", f"{ad_a.get('ctr', 0):.2f}%")
                            
                            st.caption(f"Created: {ad_a.get('created_at', 'N/A')[:10]}")
                    
                    with col2:
                        st.markdown("**🅱️ Variant B:**")
                        ad_b = st.selectbox(
                            "Select second ad",
                            options=ads,
                            format_func=lambda x: f"Ad #{x.get('id')} (CTR: {x.get('ctr', 0):.1f}%)",
                            key="compare_ad_b"
                        )
                        
                        if ad_b:
                            if ad_b.get("image_b64"):
                                st.image(f"data:image/png;base64,{ad_b['image_b64']}", width=250)
                            
                            col_b1, col_b2, col_b3 = st.columns(3)
                            with col_b1:
                                st.metric("Views", f"{ad_b.get('views', 0):,}")
                            with col_b2:
                                st.metric("Clicks", f"{ad_b.get('clicks', 0):,}")
                            with col_b3:
                                st.metric("CTR", f"{ad_b.get('ctr', 0):.2f}%")
                            
                            st.caption(f"Created: {ad_b.get('created_at', 'N/A')[:10]}")
                    
                    st.markdown("---")
                    
                    if st.button("📊 Run Statistical Comparison", use_container_width=True, type="primary"):
                        if ad_a.get('id') == ad_b.get('id'):
                            st.error("⚠️ Please select two different ads")
                        else:
                            ctr_a = ad_a.get('ctr', 0)
                            ctr_b = ad_b.get('ctr', 0)
                            views_a = ad_a.get('views', 0)
                            views_b = ad_b.get('views', 0)
                            clicks_a = ad_a.get('clicks', 0)
                            clicks_b = ad_b.get('clicks', 0)
                            
                            # Determine winner
                            if ctr_a > ctr_b:
                                winner = "🅰️ Variant A"
                                improvement = ((ctr_a - ctr_b) / ctr_b * 100) if ctr_b > 0 else 100
                            elif ctr_b > ctr_a:
                                winner = "🅱️ Variant B"
                                improvement = ((ctr_b - ctr_a) / ctr_a * 100) if ctr_a > 0 else 100
                            else:
                                winner = "Tie"
                                improvement = 0
                            
                            # Display results
                            st.markdown("### 🏆 Test Results")
                            
                            if winner != "Tie":
                                st.success(f"**Winner: {winner}**")
                                st.metric("Performance Improvement", f"+{improvement:.1f}%", delta=f"{abs(ctr_a - ctr_b):.2f}% CTR difference")
                            else:
                                st.info("📊 **Result: Statistical Tie** - Both variants performing equally")
                            
                            # Comparison chart
                            if PLOTLY_AVAILABLE:
                                import pandas as pd
                                
                                df_comparison = pd.DataFrame({
                                    'Variant': ['A', 'B'],
                                    'CTR (%)': [ctr_a, ctr_b],
                                    'Views': [views_a, views_b],
                                    'Clicks': [clicks_a, clicks_b],
                                    'Conversions': [ad_a.get('conversions', 0), ad_b.get('conversions', 0)]
                                })
                                
                                # CTR comparison bar chart
                                fig_ctr = px.bar(
                                    df_comparison, 
                                    x='Variant', 
                                    y='CTR (%)',
                                    title='Click-Through Rate Comparison',
                                    color='Variant',
                                    color_discrete_map={'A': '#667eea', 'B': '#f5576c'},
                                    text='CTR (%)'
                                )
                                fig_ctr.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
                                st.plotly_chart(fig_ctr, use_container_width=True)
                                
                                # Engagement funnel
                                fig_funnel = go.Figure()
                                fig_funnel.add_trace(go.Funnel(
                                    name='Variant A',
                                    y=['Views', 'Clicks', 'Conversions'],
                                    x=[views_a, clicks_a, ad_a.get('conversions', 0)],
                                    textinfo="value+percent initial",
                                    marker={"color": "#667eea"}
                                ))
                                fig_funnel.add_trace(go.Funnel(
                                    name='Variant B',
                                    y=['Views', 'Clicks', 'Conversions'],
                                    x=[views_b, clicks_b, ad_b.get('conversions', 0)],
                                    textinfo="value+percent initial",
                                    marker={"color": "#f5576c"}
                                ))
                                fig_funnel.update_layout(title="Engagement Funnel Comparison")
                                st.plotly_chart(fig_funnel, use_container_width=True)
                            
                            # Recommendations
                            st.markdown("### 💡 Recommendations")
                            if winner == "🅰️ Variant A":
                                st.info(f"✅ **Use Variant A** - It shows {improvement:.1f}% better performance. Consider applying its style to future campaigns.")
                            elif winner == "🅱️ Variant B":
                                st.info(f"✅ **Use Variant B** - It shows {improvement:.1f}% better performance. Consider applying its style to future campaigns.")
                            else:
                                st.info("🤔 **Continue Testing** - Both variants show similar performance. Try testing different variables.")
            
            else:
                st.error("❌ Failed to load ads for comparison")
                
        except Exception as e:
            st.error(f"❌ Error loading comparison data: {str(e)}")

# ==================== TEMPLATES ====================
elif page == "📁 Templates":
    st.markdown("## 📁 Ad Templates")
    st.markdown("Save and reuse successful ad configurations")
    
    tab1, tab2 = st.tabs(["My Templates", "Create Template"])
    
    with tab1:
        try:
            resp = requests.get(
                "http://localhost:8000/api/templates",
                headers={"Authorization": f"Bearer {st.session_state.token}"}
            )
            if resp.status_code == 200:
                templates = resp.json()
                if not templates:
                    st.info("No templates yet. Create your first template!")
                else:
                    for template in templates:
                        with st.expander(f"📋 {template['name']}"):
                            st.markdown(f"**Description:** {template['description']}")
                            st.markdown(f"**Created:** {template['created_at'][:10]}")
                            if st.button(f"Use Template", key=f"use_{template['id']}"):
                                st.info("Template loaded!")
            else:
                st.error("Failed to load templates")
        except Exception as e:
            st.error(f"Error: {str(e)}")
    
    with tab2:
        st.markdown("### Create New Template")
        template_name = st.text_input("Template Name")
        template_desc = st.text_area("Description")
        is_public = st.checkbox("Make this template public")
        product_name = st.text_input("Product Name", key="tmpl_product")
        style = st.selectbox("Style", ["Minimalist", "Bold", "Elegant"], key="tmpl_style")
        
        if st.button("💾 Save Template", use_container_width=True):
            if template_name and product_name:
                payload = {
                    "name": template_name,
                    "description": template_desc,
                    "product_template": {"name": product_name},
                    "preferences_template": {"style": style},
                    "is_public": is_public
                }
                resp = requests.post(
                    "http://localhost:8000/api/templates",
                    json=payload,
                    headers={"Authorization": f"Bearer {st.session_state.token}"}
                )
                if resp.status_code == 200:
                    st.success("Template saved!")
                    st.rerun()
                else:
                    st.error("Failed to save template")
            else:
                st.warning("Please fill in required fields")
