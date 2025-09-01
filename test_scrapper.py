#!/usr/bin/env python3
"""
Test script specifically for Naukri.com job scraping
"""

from job_scraper import JobScraper
import json

def test_naukri_scraping():
    """Test scraping the specific Naukri URL"""
    
    # Your specific URL
    naukri_url = "https://www.naukri.com/job-listings-require-chartered-accountant-for-audit-firm-in-oman-exova-consulting-oman-0-to-5-years-010925004158?src=seo_srp&sid=17567350929323324&xp=1&px=1"
    
    print("Testing Naukri.com job scraping...")
    print("=" * 60)
    print(f"URL: {naukri_url}")
    print()
    
    # Initialize scraper with Selenium support
    scraper = JobScraper(use_selenium=True)
    
    try:
        # Scrape the job
        job = scraper.scrape_job(naukri_url)
        
        if job:
            print("✅ Successfully scraped job data!")
            print("-" * 40)
            print(f"Title: {job.title}")
            print(f"Company: {job.company}")
            print(f"Location: {job.location}")
            print(f"Experience Required: {job.experience_required}")
            print(f"Skills Found: {', '.join(job.required_skills)}")
            print(f"Number of Responsibilities: {len(job.responsibilities)}")
            
            if job.responsibilities:
                print("\nResponsibilities:")
                for i, resp in enumerate(job.responsibilities[:3], 1):
                    print(f"{i}. {resp}")
            
            print(f"\nDescription Preview: {job.description[:200]}...")
            
            # Export to files
            scraper.export_to_json([job], "naukri_job.json")
            scraper.export_to_csv([job], "naukri_job.csv")
            
            print("\n📄 Data exported to 'naukri_job.json' and 'naukri_job.csv'")
            
        else:
            print("❌ Failed to scrape job data")
            print("This might be due to:")
            print("1. Site blocking automated access")
            print("2. Changed website structure")
            print("3. Network issues")
            print("4. Missing ChromeDriver for Selenium")
            
    except Exception as e:
        print(f"❌ Error occurred: {e}")
        print("\nTroubleshooting steps:")
        print("1. Install ChromeDriver: https://chromedriver.chromium.org/")
        print("2. Make sure Chrome browser is installed")
        print("3. Check internet connection")
        print("4. Try running without Selenium (requests only)")

def test_without_selenium():
    """Test with requests only (no JavaScript support)"""
    print("\n" + "=" * 60)
    print("Testing with requests only (fallback method)...")
    
    naukri_url = "https://www.naukri.com/job-listings-require-chartered-accountant-for-audit-firm-in-oman-exova-consulting-oman-0-to-5-years-010925004158?src=seo_srp&sid=17567350929323324&xp=1&px=1"
    
    # Initialize scraper without Selenium
    scraper = JobScraper(use_selenium=False)
    
    try:
        job = scraper.scrape_job(naukri_url)
        
        if job:
            print("✅ Successfully scraped with requests!")
            print(f"Title: {job.title}")
            print(f"Company: {job.company}")
            print(f"Description length: {len(job.description)} characters")
        else:
            print("❌ Requests method also failed")
            
    except Exception as e:
        print(f"❌ Requests method error: {e}")

if __name__ == "__main__":
    # Test with Selenium first
    test_naukri_scraping()
    
    # Test without Selenium as fallback
    test_without_selenium()
    
    print("\n" + "=" * 60)
    print("Installation Notes:")
    print("1. pip install -r requirements.txt")
    print("2. Download ChromeDriver from: https://chromedriver.chromium.org/")
    print("3. Add ChromeDriver to your PATH or place in project folder")
    print("4. Alternative: Use requests-only mode if Selenium fails")