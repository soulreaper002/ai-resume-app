#!/usr/bin/env python3
"""
Job Description Web Scraper
A comprehensive tool to extract job information from various job posting websites.
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import time
import logging
from urllib.parse import urlparse, urljoin
from dataclasses import dataclass
from typing import Dict, List, Optional, Union
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class JobData:
    """Data class to structure job information"""
    title: str = ""
    company: str = ""
    location: str = ""
    job_type: str = ""
    experience_required: str = ""
    description: str = ""
    responsibilities: List[str] = None
    required_skills: List[str] = None
    preferred_skills: List[str] = None
    salary: str = ""
    url: str = ""
    
    def __post_init__(self):
        if self.responsibilities is None:
            self.responsibilities = []
        if self.required_skills is None:
            self.required_skills = []
        if self.preferred_skills is None:
            self.preferred_skills = []

class JobScraper:
    """Main scraper class for extracting job information"""
    
    def __init__(self, use_selenium=True):
        self.use_selenium = use_selenium
        self.driver = None
        
        # Setup requests session for fallback
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
        # Initialize Selenium driver if needed
        if self.use_selenium:
            self._setup_driver()
        
        # Common patterns for extracting information
        self.experience_patterns = [
            r'(\d+)[\+\-\s]*(?:to|-)?\s*(\d+)?\s*years?\s*(?:of\s*)?experience',
            r'experience[:\s]*(\d+)[\+\-\s]*(?:to|-)?\s*(\d+)?\s*years?',
            r'(\d+)[\+\-]\s*years?\s*experience',
            r'minimum\s*(\d+)\s*years?',
            r'at\s*least\s*(\d+)\s*years?',
        ]
        
        self.skill_keywords = [
            'python', 'java', 'javascript', 'react', 'angular', 'vue', 'node.js',
            'sql', 'mysql', 'postgresql', 'mongodb', 'redis',
            'aws', 'azure', 'gcp', 'docker', 'kubernetes',
            'machine learning', 'ai', 'data science', 'tensorflow', 'pytorch',
            'html', 'css', 'bootstrap', 'git', 'linux', 'windows',
            'project management', 'agile', 'scrum', 'communication',
            'leadership', 'teamwork', 'problem solving', 'chartered accountant',
            'audit', 'accounting', 'finance', 'taxation', 'compliance',
            'financial reporting', 'excel', 'tally', 'sap', 'quickbooks'
        ]

    def _setup_driver(self):
        """Setup Selenium WebDriver"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.implicitly_wait(10)
            logger.info("Selenium driver initialized successfully")
            
        except Exception as e:
            logger.warning(f"Failed to initialize Selenium driver: {e}")
            logger.info("Falling back to requests-only mode")
            self.use_selenium = False
            self.driver = None

    def __del__(self):
        """Cleanup driver on object destruction"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a web page using Selenium or requests"""
        try:
            logger.info(f"Fetching: {url}")
            
            # Try Selenium first for JavaScript-heavy sites
            if self.use_selenium and self.driver:
                return self._fetch_with_selenium(url)
            else:
                return self._fetch_with_requests(url)
                
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def _fetch_with_selenium(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch page using Selenium WebDriver"""
        try:
            self.driver.get(url)
            
            # Wait for content to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Additional wait for dynamic content
            time.sleep(3)
            
            # Get page source and parse
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            return soup
            
        except TimeoutException:
            logger.error(f"Timeout waiting for page to load: {url}")
            return None
        except WebDriverException as e:
            logger.error(f"WebDriver error: {e}")
            return None

    def _fetch_with_requests(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch page using requests (fallback method)"""
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            # Check if content is HTML
            content_type = response.headers.get('content-type', '').lower()
            if 'html' not in content_type:
                logger.warning(f"Non-HTML content detected: {content_type}")
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            return soup
            
        except requests.RequestException as e:
            logger.error(f"Requests error: {e}")
            return None

    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove HTML entities
        text = text.replace('&nbsp;', ' ').replace('&amp;', '&')
        text = text.replace('&lt;', '<').replace('&gt;', '>')
        
        return text

    def extract_experience(self, text: str) -> str:
        """Extract years of experience from text"""
        text = text.lower()
        
        for pattern in self.experience_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                groups = match.groups()
                if len(groups) >= 2 and groups[1]:
                    return f"{groups[0]}-{groups[1]} years"
                elif groups[0]:
                    return f"{groups[0]}+ years"
        
        # Look for entry level indicators
        if any(term in text for term in ['entry level', 'fresher', 'graduate', 'junior']):
            return "Entry Level"
        
        # Look for senior level indicators
        if any(term in text for term in ['senior', 'lead', 'principal', 'architect']):
            return "Senior Level (5+ years)"
        
        return "Not specified"

    def extract_skills(self, text: str) -> Dict[str, List[str]]:
        """Extract skills from text"""
        text = text.lower()
        found_skills = []
        
        for skill in self.skill_keywords:
            if skill.lower() in text:
                found_skills.append(skill)
        
        # Look for additional skills in common patterns
        skill_sections = re.findall(r'(?:skills|requirements|qualifications)[:\s]*([^\.]*)', text)
        additional_skills = []
        
        for section in skill_sections:
            # Extract words that might be skills
            words = re.findall(r'\b[A-Za-z][A-Za-z\.\+\#]{2,}\b', section)
            additional_skills.extend(words)
        
        return {
            'required_skills': found_skills,
            'additional_skills': list(set(additional_skills))[:10]  # Limit to 10
        }

    def extract_responsibilities(self, soup: BeautifulSoup, text: str) -> List[str]:
        """Extract job responsibilities from text"""
        responsibilities = []
        
        # Look for bullet points or list items
        lists = soup.find_all(['ul', 'ol'])
        for lst in lists:
            items = lst.find_all('li')
            for item in items:
                resp_text = self.clean_text(item.get_text())
                if len(resp_text) > 10 and any(word in resp_text.lower() 
                    for word in ['responsible', 'manage', 'develop', 'work', 'collaborate']):
                    responsibilities.append(resp_text)
        
        # Look for numbered responsibilities
        numbered_pattern = r'(\d+[\.\)]\s*[A-Z][^\.]*\.)'
        matches = re.findall(numbered_pattern, text)
        for match in matches:
            resp = self.clean_text(match)
            if len(resp) > 15:
                responsibilities.append(resp)
        
        return responsibilities[:8]  # Limit to 8 responsibilities

    def detect_job_site(self, url: str) -> str:
        """Detect the job site type for specialized parsing"""
        domain = urlparse(url).netloc.lower()
        
        if 'linkedin.com' in domain:
            return 'linkedin'
        elif 'indeed.com' in domain:
            return 'indeed'
        elif 'glassdoor.com' in domain:
            return 'glassdoor'
        elif 'naukri.com' in domain:
            return 'naukri'
        elif 'monster.com' in domain:
            return 'monster'
        else:
            return 'generic'

    def scrape_linkedin(self, soup: BeautifulSoup, url: str) -> JobData:
        """Specialized scraping for LinkedIn job posts"""
        job = JobData(url=url)
        
        # Title
        title_elem = soup.find('h1', class_='top-card-layout__title') or soup.find('h1')
        if title_elem:
            job.title = self.clean_text(title_elem.get_text())
        
        # Company
        company_elem = soup.find('a', class_='topcard__org-name-link') or soup.find('span', class_='topcard__flavor')
        if company_elem:
            job.company = self.clean_text(company_elem.get_text())
        
        # Description
        desc_elem = soup.find('div', class_='show-more-less-html__markup')
        if desc_elem:
            job.description = self.clean_text(desc_elem.get_text())
        
        return job

    def scrape_naukri(self, soup: BeautifulSoup, url: str) -> JobData:
        """Specialized scraping for Naukri.com job posts"""
        job = JobData(url=url)
        
        # Title - multiple possible selectors
        title_selectors = [
            'h1[class*="jd-header-title"]',
            '.jd-header-title',
            'h1.job-title',
            '.job-header h1',
            'h1'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                job.title = self.clean_text(title_elem.get_text())
                break
        
        # Company name
        company_selectors = [
            '.jd-header-comp-name',
            '.company-name',
            '[class*="comp-name"]',
            '.jd-header .company',
            'a[title*="company"]'
        ]
        
        for selector in company_selectors:
            company_elem = soup.select_one(selector)
            if company_elem:
                job.company = self.clean_text(company_elem.get_text())
                break
        
        # Experience
        exp_selectors = [
            '.jd-header-exp',
            '.experience',
            '[class*="exp"]',
            '.job-details .experience'
        ]
        
        for selector in exp_selectors:
            exp_elem = soup.select_one(selector)
            if exp_elem:
                exp_text = self.clean_text(exp_elem.get_text())
                if any(keyword in exp_text.lower() for keyword in ['year', 'exp', 'experience']):
                    job.experience_required = exp_text
                    break
        
        # Location
        location_selectors = [
            '.jd-header-location',
            '.location',
            '[class*="location"]',
            '.job-location'
        ]
        
        for selector in location_selectors:
            location_elem = soup.select_one(selector)
            if location_elem:
                job.location = self.clean_text(location_elem.get_text())
                break
        
        # Job description
        desc_selectors = [
            '.jd-desc',
            '.job-description',
            '.description',
            '[class*="job-desc"]',
            '.jd-desc-content'
        ]
        
        for selector in desc_selectors:
            desc_elem = soup.select_one(selector)
            if desc_elem:
                job.description = self.clean_text(desc_elem.get_text())
                break
        
        # If no specific description found, get all text content
        if not job.description:
            job.description = self.clean_text(soup.get_text())
        
        return job
        """Specialized scraping for Indeed job posts"""
        job = JobData(url=url)
        
        # Title
        title_elem = soup.find('h1', {'data-jk': True}) or soup.find('h1')
        if title_elem:
            job.title = self.clean_text(title_elem.get_text())
        
        # Company
        company_elem = soup.find('div', {'data-testid': 'inlineHeader-companyName'}) or soup.find('span', class_='companyName')
        if company_elem:
            job.company = self.clean_text(company_elem.get_text())
        
        # Description
        desc_elem = soup.find('div', id='jobDescriptionText') or soup.find('div', class_='jobsearch-jobDescriptionText')
        if desc_elem:
            job.description = self.clean_text(desc_elem.get_text())
        
        return job

    def scrape_generic(self, soup: BeautifulSoup, url: str) -> JobData:
        """Generic scraping for unknown job sites"""
        job = JobData(url=url)
        
        # Try to find title
        title_candidates = [
            soup.find('h1'),
            soup.find('title'),
            soup.find('h2'),
            soup.find(string=re.compile(r'job title|position', re.I))
        ]
        
        for candidate in title_candidates:
            if candidate:
                job.title = self.clean_text(candidate.get_text() if hasattr(candidate, 'get_text') else str(candidate))
                break
        
        # Get all text content
        full_text = soup.get_text()
        job.description = self.clean_text(full_text)
        
        return job

    def process_job_data(self, job: JobData) -> JobData:
        """Process and enhance job data"""
        full_text = job.description
        
        # Extract experience
        job.experience_required = self.extract_experience(full_text)
        
        # Extract skills
        skills_data = self.extract_skills(full_text)
        job.required_skills = skills_data['required_skills']
        
        # Create soup from description for responsibility extraction
        temp_soup = BeautifulSoup(job.description, 'html.parser')
        job.responsibilities = self.extract_responsibilities(temp_soup, full_text)
        
        return job

    def scrape_job(self, url: str) -> Optional[JobData]:
        """Main method to scrape a job posting"""
        soup = self.fetch_page(url)
        if not soup:
            return None
        
        site_type = self.detect_job_site(url)
        logger.info(f"Detected site type: {site_type}")
        
        # Use specialized scraper based on site
        if site_type == 'linkedin':
            job = self.scrape_linkedin(soup, url)
        elif site_type == 'indeed':
            job = self.scrape_indeed(soup, url)
        elif site_type == 'naukri':
            job = self.scrape_naukri(soup, url)
        else:
            job = self.scrape_generic(soup, url)
        
        # Process and enhance the job data
        job = self.process_job_data(job)
        
        return job

    def scrape_multiple_jobs(self, urls: List[str]) -> List[JobData]:
        """Scrape multiple job postings"""
        jobs = []
        
        for i, url in enumerate(urls, 1):
            logger.info(f"Processing job {i}/{len(urls)}")
            
            job = self.scrape_job(url)
            if job:
                jobs.append(job)
            
            # Be respectful with requests
            time.sleep(1)
        
        return jobs

    def export_to_csv(self, jobs: List[JobData], filename: str = 'job_data.csv'):
        """Export job data to CSV"""
        data = []
        for job in jobs:
            data.append({
                'Title': job.title,
                'Company': job.company,
                'Location': job.location,
                'Experience Required': job.experience_required,
                'Required Skills': ', '.join(job.required_skills),
                'Responsibilities': ' | '.join(job.responsibilities),
                'Description': job.description[:500] + '...' if len(job.description) > 500 else job.description,
                'URL': job.url
            })
        
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False)
        logger.info(f"Data exported to {filename}")
        return filename

    def export_to_json(self, jobs: List[JobData], filename: str = 'job_data.json'):
        """Export job data to JSON"""
        data = []
        for job in jobs:
            data.append({
                'title': job.title,
                'company': job.company,
                'location': job.location,
                'experience_required': job.experience_required,
                'required_skills': job.required_skills,
                'responsibilities': job.responsibilities,
                'description': job.description,
                'url': job.url
            })
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Data exported to {filename}")
        return filename


def main():
    """Example usage of the job scraper"""
    scraper = JobScraper()
    
    # Example URLs - replace with actual job posting URLs
    job_urls = [
        "https://example-job-site.com/job/1",
        "https://another-job-site.com/position/123"
    ]
    
    print("Job Description Scraper")
    print("=" * 50)
    
    # Option 1: Scrape single job
    print("\n1. Scrape single job URL")
    url = input("Enter job URL (or press Enter to skip): ").strip()
    
    if url:
        job = scraper.scrape_job(url)
        if job:
            print(f"\nJob Title: {job.title}")
            print(f"Company: {job.company}")
            print(f"Experience: {job.experience_required}")
            print(f"Skills: {', '.join(job.required_skills)}")
            print(f"Responsibilities: {len(job.responsibilities)} found")
            print(f"Description length: {len(job.description)} characters")
        else:
            print("Failed to scrape job data")
    
    # Option 2: Scrape multiple jobs
    print("\n2. Scrape multiple jobs")
    multiple_choice = input("Do you want to scrape multiple URLs? (y/n): ").lower()
    
    if multiple_choice == 'y':
        urls = []
        while True:
            url = input("Enter job URL (or press Enter to finish): ").strip()
            if not url:
                break
            urls.append(url)
        
        if urls:
            print(f"\nScraping {len(urls)} job postings...")
            jobs = scraper.scrape_multiple_jobs(urls)
            
            if jobs:
                # Export results
                csv_file = scraper.export_to_csv(jobs)
                json_file = scraper.export_to_json(jobs)
                
                print(f"\nSuccessfully scraped {len(jobs)} jobs!")
                print(f"Data exported to: {csv_file} and {json_file}")
                
                # Display summary
                print("\nSummary:")
                for i, job in enumerate(jobs, 1):
                    print(f"{i}. {job.title} at {job.company}")
            else:
                print("No jobs were successfully scraped")


if __name__ == "__main__":
    main()