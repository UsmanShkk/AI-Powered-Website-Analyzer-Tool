

import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
import requests
import json
from typing import List, Dict, Any
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import google.generativeai as genai
import re
from urllib.parse import urljoin, urlparse
import time
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize and constants
load_dotenv(override=True)
api_key = os.getenv('GEMINI_API_KEY')

if api_key and len(api_key) > 10:
    print("API key looks good so far")
    genai.configure(api_key=api_key)
else:
    print("There might be a problem with your API key!")

class Website:
    """Enhanced Website utility class with better error handling"""

    def __init__(self, url):
        # Initialize all attributes with defaults first
        self.url = url
        self.domain = urlparse(url).netloc
        self.title = "Unknown Title"
        self.meta_description = ""
        self.keywords = ""
        self.text = ""
        self.links = []
        self.images = []
        self.status_code = None
        self.error = None
        self.body = None

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        try:
            logger.info(f"Scraping {url}...")
            response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            response.raise_for_status()

            self.body = response.content
            self.status_code = response.status_code

            soup = BeautifulSoup(self.body, 'html.parser')

            # Extract title
            if soup.title:
                self.title = soup.title.string.strip() if soup.title.string else "No title found"
            else:
                # Try to find title in h1 tags
                h1 = soup.find('h1')
                if h1:
                    self.title = h1.get_text(strip=True)
                else:
                    self.title = f"Website: {self.domain}"

            # Extract meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if not meta_desc:
                meta_desc = soup.find('meta', attrs={'property': 'og:description'})
            self.meta_description = meta_desc.get('content', '') if meta_desc else ''

            # Extract keywords
            meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
            self.keywords = meta_keywords.get('content', '') if meta_keywords else ''

            # Extract text content
            if soup.body:
                # Remove irrelevant elements
                for irrelevant in soup.body(["script", "style", "img", "input", "nav", "footer", "header"]):
                    irrelevant.decompose()
                self.text = soup.body.get_text(separator="\n", strip=True)
            else:
                self.text = soup.get_text(separator="\n", strip=True)

            # Extract all links with proper URL resolution
            links = []
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if href and not href.startswith('#'):  # Skip anchor links
                    try:
                        absolute_url = urljoin(url, href)
                        links.append({
                            'url': absolute_url,
                            'text': link.get_text(strip=True),
                            'title': link.get('title', '')
                        })
                    except Exception as e:
                        logger.warning(f"Error processing link {href}: {e}")
            self.links = links

            # Extract images
            images = []
            for img in soup.find_all('img', src=True):
                src = img.get('src')
                if src:
                    try:
                        absolute_url = urljoin(url, src)
                        images.append({
                            'url': absolute_url,
                            'alt': img.get('alt', ''),
                            'title': img.get('title', '')
                        })
                    except Exception as e:
                        logger.warning(f"Error processing image {src}: {e}")
            self.images = images

            logger.info(f"Successfully scraped {url}")

        except requests.exceptions.RequestException as e:
            error_msg = f"Error scraping {url}: {str(e)}"
            logger.error(error_msg)
            self.error = error_msg
            self.title = f"Error accessing {self.domain}"

        except Exception as e:
            error_msg = f"Unexpected error scraping {url}: {str(e)}"
            logger.error(error_msg)
            self.error = error_msg
            self.title = f"Error processing {self.domain}"

    def get_contents(self):
        """Get formatted content for analysis"""
        content = f"Webpage Title: {self.title}\n\n"

        if self.meta_description:
            content += f"Meta Description: {self.meta_description}\n\n"

        if self.error:
            content += f"Error: {self.error}\n\n"
            content += f"Note: Limited information available due to scraping restrictions.\n"
            content += f"Company appears to be: {self.domain}\n\n"
        else:
            content += f"Webpage Contents:\n{self.text[:3000]}...\n\n"

        return content

    def is_valid(self):
        """Check if the website was successfully scraped"""
        return self.error is None and self.text and len(self.text) > 100

# =================== HELPER FUNCTIONS ===================
def safe_ai_call(prompt_parts, system_prompt="", json_response=False):
    """Safe wrapper for Gemini API calls with error handling"""
    try:
        generation_config = {}
        if json_response:
            generation_config["response_mime_type"] = "application/json"

        if system_prompt:
            messages = [
                {"role": "user", "parts": [system_prompt]},
                {"role": "model", "parts": ["I understand. I'll help you with this analysis."]},
                {"role": "user", "parts": prompt_parts}
            ]
        else:
            messages = [{"role": "user", "parts": prompt_parts}]

        response = genai.GenerativeModel('gemini-1.5-flash').generate_content(
            contents=messages,
            generation_config=generation_config
        )

        if json_response:
            return json.loads(response.text)
        else:
            return response.text

    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e}")
        return {"error": "Failed to parse AI response as JSON", "raw_response": response.text}
    except Exception as e:
        logger.error(f"AI API error: {e}")
        return f"Error: Unable to complete analysis - {str(e)}"

def create_fallback_analysis(url, domain):
    """Create basic analysis when website scraping fails"""
    return f"""# Website Analysis for {domain}

## Status
⚠️ **Limited Analysis Available**

The website {url} could not be fully accessed due to access restrictions (likely bot protection or rate limiting).

## Basic Information
- **Domain**: {domain}
- **URL**: {url}
- **Status**: Access restricted

## Recommendations

### For SEO Analysis:
1. **Accessibility**: Ensure your website is accessible to search engine crawlers
2. **Robots.txt**: Check if robots.txt is blocking legitimate crawlers
3. **Server Response**: Verify server responds correctly to requests
4. **CDN Settings**: If using a CDN, ensure it's configured properly

### For Content Strategy:
1. **Industry Research**: Research your industry's content trends
2. **Competitor Analysis**: Analyze accessible competitor websites
3. **Keyword Research**: Use tools like Google Keyword Planner
4. **Content Audit**: Manually review your website's content

### For Technical Improvements:
1. **Monitoring**: Set up website monitoring to detect access issues
2. **Performance**: Optimize page load speeds
3. **Mobile Optimization**: Ensure mobile-friendly design
4. **Security**: Review security settings that might block legitimate traffic

## Next Steps
1. Contact your web developer to review access restrictions
2. Check server logs for blocked requests
3. Consider adjusting security settings for better accessibility
4. Implement proper user-agent handling

*Note: This analysis is limited due to access restrictions. For a complete analysis, please ensure the website is accessible to automated tools.*
"""

# =================== COMPETITOR ANALYSIS ===================
def analyze_competitors(main_url, competitor_urls: List[str]):
    """Compare main website with competitors"""

    system_prompt = """You are a business analyst specializing in competitive analysis.
    Compare the main company website with competitor websites and provide insights on:
    - Unique value propositions
    - Service/product differences
    - Website quality and user experience
    - Content strategy differences
    - Competitive advantages and gaps

    If any websites couldn't be accessed, note this limitation and provide analysis based on available data.
    Respond in structured markdown format."""

    main_site = Website(main_url)
    competitor_data = []

    for comp_url in competitor_urls:
        comp_site = Website(comp_url)
        competitor_data.append({
            'url': comp_url,
            'title': comp_site.title,
            'content': comp_site.text[:2000] if comp_site.is_valid() else "Content not accessible",
            'accessible': comp_site.is_valid()
        })

    user_prompt = f"""Main Company Website:
    Title: {main_site.title}
    URL: {main_url}
    Accessible: {main_site.is_valid()}
    Content: {main_site.text[:2000] if main_site.is_valid() else "Content not accessible"}

    Competitor Websites:
    """

    for comp in competitor_data:
        user_prompt += f"\n\nCompetitor: {comp['title']} ({comp['url']})\n"
        user_prompt += f"Accessible: {comp['accessible']}\n"
        user_prompt += f"Content: {comp['content']}"

    return safe_ai_call([user_prompt], system_prompt)

# =================== SEO ANALYSIS ===================
def analyze_seo(url):
    """Comprehensive SEO analysis of a website"""

    website = Website(url)

    if not website.is_valid():
        return create_fallback_analysis(url, website.domain) + "\n\n## SEO Specific Recommendations:\n- Ensure website is crawlable by search engines\n- Check robots.txt file\n- Verify server response codes\n- Test website accessibility from different locations"

    system_prompt = """You are an SEO expert. Analyze the website and provide recommendations on:
    - Title tag optimization
    - Meta description effectiveness
    - Content structure and headers
    - Keyword usage and density
    - Page loading insights (based on content size)
    - Mobile-friendliness indicators
    - Content quality and readability
    Provide actionable SEO recommendations in markdown format."""

    user_prompt = f"""Analyze this website for SEO:
    URL: {url}
    Title: {website.title}
    Meta Description: {website.meta_description}
    Keywords: {website.keywords}
    Content Length: {len(website.text)} characters
    Number of Images: {len(website.images)}
    Number of Links: {len(website.links)}

    Page Content:
    {website.text[:3000]}"""

    return safe_ai_call([user_prompt], system_prompt)

# =================== CONTENT STRATEGY ===================
def generate_content_ideas(url, content_type="blog"):
    """Generate content marketing ideas based on website analysis"""

    website = Website(url)

    system_prompt = f"""You are a content marketing strategist. Based on the website analysis,
    generate 10 {content_type} content ideas that would:
    - Attract the target audience
    - Showcase company expertise
    - Drive organic traffic
    - Support business goals
    - Be engaging and shareable

    For each idea, provide:
    - Title
    - Brief description
    - Target audience
    - Expected outcome

    If website content is limited, use the domain name and any available information to make educated assumptions about the business.
    Respond in structured markdown format."""

    user_prompt = f"""Generate {content_type} content ideas for this company:
    Company: {website.title}
    URL: {url}
    Description: {website.meta_description}
    Domain: {website.domain}

    Available Business Context:
    {website.text[:2000] if website.is_valid() else f"Limited access to {website.domain} - please infer business type from domain name"}"""

    return safe_ai_call([user_prompt], system_prompt)

# =================== LEAD GENERATION ===================
def extract_contact_info(url):
    """Extract and organize contact information from website"""

    website = Website(url)

    system_prompt = """You are a lead generation specialist. Extract and organize all contact information from the website including:
    - Email addresses
    - Phone numbers
    - Physical addresses
    - Social media profiles
    - Contact forms
    - Key personnel names and roles

    Also identify potential lead magnets like:
    - Free downloads
    - Newsletter signups
    - Free trials
    - Consultation offers

    If website content is limited, note this limitation and provide general recommendations for lead generation.
    Respond in structured JSON format."""

    user_prompt = f"""Extract contact information and lead magnets from:
    URL: {url}
    Title: {website.title}
    Domain: {website.domain}
    Accessible: {website.is_valid()}
    Content: {website.text[:2000] if website.is_valid() else "Limited access"}

    Links found: {[link['text'] + ' -> ' + link['url'] for link in website.links[:20]]}"""

    return safe_ai_call([user_prompt], system_prompt, json_response=True)

# =================== WEBSITE AUDIT ===================
def comprehensive_audit(url):
    """Perform a comprehensive website audit"""

    website = Website(url)

    if not website.is_valid():
        return create_fallback_analysis(url, website.domain) + "\n\n## Audit Specific Recommendations:\n- Fix website accessibility issues\n- Ensure proper server configuration\n- Review security settings\n- Test from multiple locations and devices"

    system_prompt = """You are a website auditor. Provide a comprehensive audit covering:

    **Technical Aspects:**
    - Page structure and navigation
    - Content organization
    - User experience issues

    **Business Aspects:**
    - Clear value proposition
    - Call-to-action effectiveness
    - Trust signals and credibility
    - Conversion optimization opportunities

    **Content Quality:**
    - Message clarity
    - Professional presentation
    - Completeness of information

    **Recommendations:**
    - Priority improvements
    - Quick wins
    - Long-term strategies

    Rate each section 1-10 and provide actionable recommendations."""

    user_prompt = f"""Audit this website comprehensively:
    URL: {url}
    Title: {website.title}
    Meta Description: {website.meta_description}
    Content Length: {len(website.text)} characters
    Number of Pages Linked: {len([l for l in website.links if website.domain in l['url']])}
    External Links: {len([l for l in website.links if website.domain not in l['url']])}

    Content:
    {website.text[:4000]}

    Navigation/Links:
    {[link['text'] for link in website.links[:15]]}"""

    return safe_ai_call([user_prompt], system_prompt)

# =================== SOCIAL MEDIA STRATEGY ===================
def generate_social_media_strategy(url, platforms=["LinkedIn", "Twitter", "Instagram"]):
    """Generate social media strategy based on website"""

    website = Website(url)

    system_prompt = f"""You are a social media strategist. Based on the website analysis, create a social media strategy for {', '.join(platforms)}:

    For each platform, provide:
    - Content themes and topics
    - Posting frequency recommendations
    - Content format suggestions (text, images, videos)
    - Engagement strategies
    - Hashtag recommendations
    - Key performance indicators

    Also suggest:
    - Cross-platform content repurposing
    - Community building tactics
    - Influencer collaboration opportunities

    If website content is limited, use the domain name to infer business type and create appropriate strategies.
    Tailor recommendations to each platform's unique audience and features."""

    user_prompt = f"""Create social media strategy for:
    Company: {website.title}
    URL: {url}
    Domain: {website.domain}
    Business Description: {website.meta_description}

    Target Platforms: {platforms}

    Available Business Context:
    {website.text[:2000] if website.is_valid() else f"Limited access to {website.domain} - please infer business type from domain name"}"""

    return safe_ai_call([user_prompt], system_prompt)

# =================== EMAIL CAMPAIGN GENERATOR ===================
def generate_email_campaigns(url, campaign_type="welcome_series"):
    """Generate email marketing campaigns"""

    website = Website(url)

    system_prompt = f"""You are an email marketing specialist. Create a {campaign_type} email campaign based on the website analysis:

    Provide:
    - Email sequence outline (3-5 emails)
    - Subject lines for each email
    - Email content structure
    - Call-to-action recommendations
    - Personalization opportunities
    - A/B testing suggestions

    Campaign types available: welcome_series, nurture_sequence, product_launch, re_engagement

    If website content is limited, use the domain name to infer business type and create appropriate campaigns.
    Make emails engaging, valuable, and aligned with the company's brand voice."""

    user_prompt = f"""Create {campaign_type} email campaign for:
    Company: {website.title}
    URL: {url}
    Domain: {website.domain}
    Business: {website.meta_description}

    Available Company Information:
    {website.text[:2000] if website.is_valid() else f"Limited access to {website.domain} - please infer business type from domain name"}"""

    return safe_ai_call([user_prompt], system_prompt)

# =================== MAIN AGENTIC FUNCTION ===================
def analyze_website_complete(url, analysis_type="all"):
    """Main agentic function that orchestrates different analyses"""

    print(f"🚀 Starting comprehensive analysis of {url}")
    print("=" * 60)

    analyses = {
        "seo": lambda: analyze_seo(url),
        "audit": lambda: comprehensive_audit(url),
        "content": lambda: generate_content_ideas(url),
        "social": lambda: generate_social_media_strategy(url),
        "leads": lambda: extract_contact_info(url),
        "email": lambda: generate_email_campaigns(url),
        "brochure": lambda: create_brochure_from_url(url)
    }

    results = {}

    if analysis_type == "all":
        for name, func in analyses.items():
            print(f"\n📊 Running {name.upper()} analysis...")
            print("-" * 40)
            try:
                results[name] = func()
                print(f"✅ {name.upper()} analysis completed")
                time.sleep(2)  # Rate limiting
            except Exception as e:
                error_msg = f"Error in {name} analysis: {str(e)}"
                logger.error(error_msg)
                results[name] = error_msg
    else:
        if analysis_type in analyses:
            print(f"\n📊 Running {analysis_type.upper()} analysis...")
            print("-" * 40)
            try:
                results[analysis_type] = analyses[analysis_type]()
                print(f"✅ {analysis_type.upper()} analysis completed")
            except Exception as e:
                error_msg = f"Error in {analysis_type} analysis: {str(e)}"
                logger.error(error_msg)
                results[analysis_type] = error_msg
        else:
            print(f"Available analyses: {list(analyses.keys())}")
            return {"error": f"Invalid analysis type. Available: {list(analyses.keys())}"}

    return results

def create_brochure_from_url(url):
    """Helper function for brochure creation"""
    website = Website(url)
    domain = website.domain
    company_name = domain.replace('www.', '').split('.')[0].title()
    return create_brochure(company_name, url)

# Original brochure functions (preserved with error handling)
def get_links(url):
    website = Website(url)

    if not website.is_valid():
        return {"error": f"Could not access website: {website.error}"}

    link_system_prompt = """You are provided with a list of links found on a webpage.
    You are able to decide which of the links would be most relevant to include in a brochure about the company,
    such as links to an About page, or a Company page, or Careers/Jobs pages.
    You should respond in JSON as in this example:
    {
        "links": [
            {"type": "about page", "url": "https://full.url/goes/here/about"},
            {"type": "careers page", "url": "https://another.full.url/careers"}
        ]
    }
    """

    user_prompt = f"Here is the list of links on the website of {website.url} - "
    user_prompt += "please decide which of these are relevant web links for a brochure about the company. "
    user_prompt += "Links:\n" + "\n".join([link['url'] for link in website.links])

    return safe_ai_call([user_prompt], link_system_prompt, json_response=True)

def create_brochure(company_name, url, humorous=False):
    """Create a company brochure based on website content"""

    website = Website(url)

    system_prompt = """You are an assistant that analyzes the contents of several relevant pages from a company website
    and creates a short brochure about the company for prospective customers, investors and recruits. Respond in markdown.
    Include details of company culture, customers and careers/jobs if you have the information.

    If website content is limited, use the domain name and company name to create a professional brochure template."""

    if humorous:
        system_prompt = system_prompt.replace("short brochure", "short humorous, entertaining, jokey brochure")

    user_prompt = f"""Company: {company_name}
    URL: {url}
    Domain: {website.domain}
    Title: {website.title}
    Accessible: {website.is_valid()}
    Content: {website.text[:3000] if website.is_valid() else f"Limited access to {website.domain} - please create a professional brochure template based on the company name and domain"}"""

    return safe_ai_call([user_prompt], system_prompt)

# =================== EXAMPLE USAGE ===================
if __name__ == "__main__":
    # Example: Test with different URLs
    urls_to_test = [
        "https://anthropic.com"
    ]

    for url in urls_to_test:
        print(f"\n{'='*60}")
        print(f"Testing: {url}")
        print(f"{'='*60}")

        # Test individual analyses
        print("\n📧 Email Campaign:")
        email_result = generate_email_campaigns(url, "welcome_series")
        print(email_result[:500] + "..." if len(str(email_result)) > 500 else email_result)

        print("\n📱 Social Media Strategy:")
        social_result = generate_social_media_strategy(url)
        print(social_result[:500] + "..." if len(str(social_result)) > 500 else social_result)

        print("\n🔍 SEO Analysis:")
        seo_result = analyze_seo(url)
        print(seo_result[:500] + "..." if len(str(seo_result)) > 500 else seo_result)

        time.sleep(3)  # Rate limiting between URLs
