# backend/main.py
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict, Any
import asyncio
import uvicorn
from datetime import datetime
import json
import os
from urllib.parse import urlparse

# Import your website analyzer functions
from website_analyzer import (
    analyze_seo, 
    analyze_competitors, 
    generate_content_ideas,
    extract_contact_info, 
    comprehensive_audit, 
    generate_social_media_strategy,
    generate_email_campaigns, 
    create_brochure, 
    Website,
    analyze_website_complete  # Added this import
)

app = FastAPI(
    title="Website Analyzer API",
    description="AI-powered website analysis and marketing intelligence platform",
    version="1.0.0"
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173", 
        "http://localhost:8080",
        "http://localhost:5500",  # VS Code Live Server
        "http://localhost:5000",  # Python HTTP Server
        "http://127.0.0.1:5000",  # Alternative localhost
        "http://127.0.0.1:5500",  # Alternative VS Code
        "*"  # ⚠️ Only for development - remove in production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response validation
class URLRequest(BaseModel):
    url: str  # Changed from HttpUrl to str for flexibility
    
class CompetitorAnalysisRequest(BaseModel):
    main_url: str  # Changed from HttpUrl to str
    competitor_urls: List[str]  # Changed from List[HttpUrl] to List[str]
    
class ContentRequest(BaseModel):
    url: str  # Changed from HttpUrl to str
    content_type: str = "blog"
    
class SocialMediaRequest(BaseModel):
    url: str  # Changed from HttpUrl to str
    platforms: List[str] = ["LinkedIn", "Twitter", "Instagram"]
    
class EmailCampaignRequest(BaseModel):
    url: str  # Changed from HttpUrl to str
    campaign_type: str = "welcome_series"
    
class BrochureRequest(BaseModel):
    url: str  # Changed from HttpUrl to str
    company_name: Optional[str] = None
    humorous: bool = False

class AnalysisRequest(BaseModel):
    url: str
    analysis_type: str = "all"

class AnalysisResponse(BaseModel):
    success: bool
    data: Dict[Any, Any]
    message: str
    timestamp: datetime

# In-memory storage for demo (use Redis/Database in production)
analysis_cache = {}
analysis_jobs = {}

# Helper function to validate URL
def validate_url(url: str) -> str:
    """Validate and normalize URL"""
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url

# =================== API ENDPOINTS ===================

@app.get("/")
async def root():
    return {
        "message": "Website Analyzer API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "analysis": [
                "/analyze/seo",
                "/analyze/competitors", 
                "/analyze/content",
                "/analyze/contact", 
                "/analyze/audit",
                "/analyze/social",
                "/analyze/email",
                "/analyze/brochure",
                "/analyze/complete"
            ],
            "utility": [
                "/website/info",
                "/jobs/{job_id}",
                "/health"
            ]
        }
    }

@app.post("/analyze/seo", response_model=AnalysisResponse)
async def analyze_website_seo(request: URLRequest):
    """Perform SEO analysis on a website"""
    try:
        url_str = validate_url(request.url)
        
        # Check cache first
        cache_key = f"seo_{url_str}"
        if cache_key in analysis_cache:
            return AnalysisResponse(
                success=True,
                data=analysis_cache[cache_key],
                message="SEO analysis retrieved from cache",
                timestamp=datetime.now()
            )
        
        # Perform analysis
        result = analyze_seo(url_str)
        
        # Cache result
        analysis_data = {"analysis": result, "type": "seo", "url": url_str}
        analysis_cache[cache_key] = analysis_data
        
        return AnalysisResponse(
            success=True,
            data=analysis_data,
            message="SEO analysis completed successfully",
            timestamp=datetime.now()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SEO analysis failed: {str(e)}")

@app.post("/analyze/competitors", response_model=AnalysisResponse)
async def analyze_website_competitors(request: CompetitorAnalysisRequest):
    """Analyze competitors"""
    try:
        main_url = validate_url(request.main_url)
        competitor_urls = [validate_url(url) for url in request.competitor_urls]
        
        result = analyze_competitors(main_url, competitor_urls)
        
        return AnalysisResponse(
            success=True,
            data={
                "analysis": result, 
                "type": "competitors",
                "main_url": main_url,
                "competitor_urls": competitor_urls
            },
            message="Competitor analysis completed successfully",
            timestamp=datetime.now()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Competitor analysis failed: {str(e)}")

@app.post("/analyze/content", response_model=AnalysisResponse)
async def generate_website_content(request: ContentRequest):
    """Generate content ideas"""
    try:
        url_str = validate_url(request.url)
        result = generate_content_ideas(url_str, request.content_type)
        
        return AnalysisResponse(
            success=True,
            data={
                "analysis": result, 
                "type": "content", 
                "content_type": request.content_type,
                "url": url_str
            },
            message="Content ideas generated successfully",
            timestamp=datetime.now()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Content generation failed: {str(e)}")

@app.post("/analyze/contact", response_model=AnalysisResponse)
async def extract_website_contacts(request: URLRequest):
    """Extract contact information"""
    try:
        url_str = validate_url(request.url)
        result = extract_contact_info(url_str)
        
        return AnalysisResponse(
            success=True,
            data={"analysis": result, "type": "contact", "url": url_str},
            message="Contact information extracted successfully",
            timestamp=datetime.now()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Contact extraction failed: {str(e)}")

@app.post("/analyze/audit", response_model=AnalysisResponse)
async def audit_website(request: URLRequest):
    """Comprehensive website audit"""
    try:
        url_str = validate_url(request.url)
        result = comprehensive_audit(url_str)
        
        return AnalysisResponse(
            success=True,
            data={"analysis": result, "type": "audit", "url": url_str},
            message="Website audit completed successfully",
            timestamp=datetime.now()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Website audit failed: {str(e)}")

@app.post("/analyze/social", response_model=AnalysisResponse)
async def generate_social_strategy(request: SocialMediaRequest):
    """Generate social media strategy"""
    try:
        url_str = validate_url(request.url)
        result = generate_social_media_strategy(url_str, request.platforms)
        
        return AnalysisResponse(
            success=True,
            data={
                "analysis": result, 
                "type": "social", 
                "platforms": request.platforms,
                "url": url_str
            },
            message="Social media strategy generated successfully",
            timestamp=datetime.now()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Social media strategy failed: {str(e)}")

@app.post("/analyze/email", response_model=AnalysisResponse)
async def generate_email_strategy(request: EmailCampaignRequest):
    """Generate email campaign"""
    try:
        url_str = validate_url(request.url)
        result = generate_email_campaigns(url_str, request.campaign_type)
        
        return AnalysisResponse(
            success=True,
            data={
                "analysis": result, 
                "type": "email", 
                "campaign_type": request.campaign_type,
                "url": url_str
            },
            message="Email campaign generated successfully",
            timestamp=datetime.now()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email campaign generation failed: {str(e)}")

@app.post("/analyze/brochure", response_model=AnalysisResponse)
async def create_website_brochure(request: BrochureRequest):
    """Create company brochure"""
    try:
        url_str = validate_url(request.url)
        
        if request.company_name:
            result = create_brochure(request.company_name, url_str, request.humorous)
        else:
            # Auto-extract company name from URL
            domain = urlparse(url_str).netloc
            company_name = domain.replace('www.', '').split('.')[0].title()
            result = create_brochure(company_name, url_str, request.humorous)
        
        return AnalysisResponse(
            success=True,
            data={
                "analysis": result, 
                "type": "brochure", 
                "humorous": request.humorous,
                "url": url_str
            },
            message="Company brochure created successfully",
            timestamp=datetime.now()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Brochure creation failed: {str(e)}")

@app.post("/analyze/complete")
async def complete_website_analysis(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks
):
    """Run complete analysis (async background job)"""
    try:
        url_str = validate_url(request.url)
        job_id = f"job_{int(datetime.now().timestamp() * 1000)}"  # More unique job ID
        
        # Initialize job status
        analysis_jobs[job_id] = {
            "status": "running",
            "progress": 0,
            "results": {},
            "started_at": datetime.now().isoformat(),
            "url": url_str,
            "analysis_type": request.analysis_type
        }
        
        # Run analysis in background
        background_tasks.add_task(run_complete_analysis, job_id, url_str, request.analysis_type)
        
        return {
            "job_id": job_id,
            "status": "started",
            "message": "Complete analysis started. Use /jobs/{job_id} to check progress",
            "estimated_time": "3-8 minutes",
            "url": url_str,
            "analysis_type": request.analysis_type
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start analysis: {str(e)}")

@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get analysis job status"""
    if job_id not in analysis_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = analysis_jobs[job_id]
    
    # Convert datetime objects to strings for JSON serialization
    if isinstance(job.get("started_at"), datetime):
        job["started_at"] = job["started_at"].isoformat()
    if isinstance(job.get("completed_at"), datetime):
        job["completed_at"] = job["completed_at"].isoformat()
    
    return job

async def run_complete_analysis(job_id: str, url: str, analysis_type: str = "all"):
    """Background task for complete analysis"""
    try:
        job = analysis_jobs[job_id]
        
        if analysis_type == "all":
            # Use the analyze_website_complete function from website_analyzer.py
            results = analyze_website_complete(url, "all")
            job["results"] = results
            job["progress"] = 100
        else:
            # Run specific analysis
            analysis_functions = {
                "seo": lambda: analyze_seo(url),
                "audit": lambda: comprehensive_audit(url),
                "content": lambda: generate_content_ideas(url),
                "social": lambda: generate_social_media_strategy(url),
                "contact": lambda: extract_contact_info(url),
                "email": lambda: generate_email_campaigns(url),
                "brochure": lambda: create_brochure("Company", url)
            }
            
            if analysis_type in analysis_functions:
                result = analysis_functions[analysis_type]()
                job["results"][analysis_type] = result
                job["progress"] = 100
            else:
                raise ValueError(f"Invalid analysis type: {analysis_type}")
        
        job["status"] = "completed"
        job["completed_at"] = datetime.now().isoformat()
        
    except Exception as e:
        analysis_jobs[job_id]["status"] = "failed"
        analysis_jobs[job_id]["error"] = str(e)
        analysis_jobs[job_id]["completed_at"] = datetime.now().isoformat()

# =================== UTILITY ENDPOINTS ===================

@app.get("/website/info")
async def get_website_info(url: str):
    """Get basic website information"""
    try:
        url = validate_url(url)
        website = Website(url)
        return {
            "success": True,
            "data": {
                "title": website.title,
                "meta_description": website.meta_description,
                "keywords": website.keywords,
                "domain": website.domain,
                "links_count": len(website.links),
                "images_count": len(website.images),
                "content_length": len(website.text),
                "status_code": website.status_code
            },
            "url": url
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch website info: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "timestamp": datetime.now().isoformat(),
        "service": "Website Analyzer API",
        "version": "1.0.0"
    }

@app.get("/jobs")
async def list_jobs():
    """List all analysis jobs"""
    return {
        "total_jobs": len(analysis_jobs),
        "jobs": list(analysis_jobs.keys()),
        "cache_size": len(analysis_cache)
    }

# =================== ERROR HANDLERS ===================

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {"error": "Endpoint not found", "available_endpoints": [
        "/", "/analyze/seo", "/analyze/competitors", "/analyze/content",
        "/analyze/contact", "/analyze/audit", "/analyze/social", 
        "/analyze/email", "/analyze/brochure", "/analyze/complete",
        "/website/info", "/health", "/jobs"
    ]}

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return {"error": "Internal server error", "message": str(exc)}

# =================== RUN SERVER ===================
if __name__ == "__main__":
    print("🚀 Starting Website Analyzer API...")
    print("📊 Available endpoints:")
    print("   - SEO Analysis: POST /analyze/seo")
    print("   - Competitor Analysis: POST /analyze/competitors")
    print("   - Content Ideas: POST /analyze/content")
    print("   - Contact Info: POST /analyze/contact")
    print("   - Website Audit: POST /analyze/audit")
    print("   - Social Media Strategy: POST /analyze/social")
    print("   - Email Campaigns: POST /analyze/email")
    print("   - Company Brochure: POST /analyze/brochure")
    print("   - Complete Analysis: POST /analyze/complete")
    print("   - Website Info: GET /website/info")
    print("   - Health Check: GET /health")
    print("=" * 50)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )