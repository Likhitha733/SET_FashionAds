from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    ads = relationship("Ad", back_populates="owner")
    templates = relationship("Template", back_populates="owner")


class Ad(Base):
    __tablename__ = "ads"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # ✅ UNIFIED: Use ONLY ad_text everywhere (no ad_json!)
    ad_text = Column(Text)  # ✅ SINGLE FIELD for all ad data
    
    product = Column(String, nullable=True)
    preferences = Column(String, nullable=True)
    prompt = Column(String, nullable=True)
    style = Column(String, nullable=True)
    image_b64 = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # Analytics
    views = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    conversions = Column(Integer, default=0)
    last_metrics_update = Column(DateTime, default=datetime.utcnow)
    
    # A/B Testing
    variant_name = Column(String, default="A")
    parent_ad_id = Column(Integer, nullable=True)
    
    reference_image = Column(Text, nullable=True)
    
    owner = relationship("User", back_populates="ads")


class Template(Base):
    __tablename__ = "templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(String)
    product_template = Column(String)
    preferences_template = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_public = Column(Boolean, default=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    owner = relationship("User", back_populates="templates")


class AdVersion(Base):
    __tablename__ = "ad_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    ad_id = Column(Integer, ForeignKey("ads.id"))
    version_number = Column(Integer)
    ad_text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(String, nullable=True)


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"
    
    id = Column(Integer, primary_key=True, index=True)
    ad_id = Column(Integer, ForeignKey("ads.id"), index=True)
    event_type = Column(String)  # "view", "click", "conversion"
    user_id = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
