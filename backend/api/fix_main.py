# Run this Python script in your backend/api directory to fix main.py

import re

# Read the current main.py
with open('main.py', 'r') as f:
    content = f.read()

# Define all replacements (in order of importance)
replacements = [
    # 1. Ad text extraction
    ("ad_json = ad_json.get('ad_json', '')", "ad_text = str(ad_json)"),
    
    # 2. Ad creation - change ad_json= parameter to ad_text=
    ("ad_json=ad_json,", "ad_text=ad_text,"),
    ("ad_json=str(ad_json)", "ad_text=str(ad_json)"),
    ("ad_json=str(variant_ad_json)", "ad_text=str(variant_ad_json)"),
    
    # 3. Response JSON keys  
    ('"ad_json": ad_json,', '"ad_text": str(ad_json),'),
    ('"ad_json": ad.ad_json,', '"ad_text": ad.ad_text,'),
    
    # 4. Request parsing
    ('request.get("ad_json"', 'request.get("ad_text"'),
    
    # 5. Ad field access
    ("eval(ad.ad_json)", "eval(ad.ad_text)"),
    ("ad.ad_json =", "ad.ad_text ="),
    
    # 6. Database queries/filters
    ("models.Ad.ad_json.contains", "models.Ad.ad_text.contains"),
    
    # 7. Function parameters
    ("create_ad_composite(ad_json", "create_ad_composite(ad_text"),
]

print("Starting replacements...")
print("=" * 70)

# Apply all replacements
for find, replace in replacements:
    old_content = content
    content = content.replace(find, replace)
    if old_content != content:
        count = old_content.count(find)
        print(f"✅ Replaced '{find}' → '{replace}' ({count} occurrence(s))")
    else:
        print(f"⚠️  No matches found for: '{find}'")

print("=" * 70)

# Write the fixed file
with open('main.py', 'w') as f:
    f.write(content)

print("✅ File saved successfully!")
print("\n🚀 Next steps:")
print("1. Delete the database: rm ads.db")
print("2. Restart backend: python -m backend.api.main")
print("3. Test with frontend")
