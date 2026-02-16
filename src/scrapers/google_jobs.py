
from serpapi import GoogleSearch
from .base import JobScraper
import os
import logging
from src.utils.config import SERPAPI_KEY

class GoogleJobsScraper(JobScraper):
    def __init__(self):
        super().__init__('GoogleJobs (SerpApi)')
        self.api_key = SERPAPI_KEY

    def scrape(self):
        if not self.api_key:
            logging.warning("No SERPAPI_KEY found. Skipping Google Jobs scraping.")
            return []

        try:
            logging.info(f"Fetching jobs from {self.name}...")
            jobs = []
            
            # Search queries for India
            queries = [
                "Software Engineer jobs in India",
                "DevOps jobs in India",
                "QA Engineer jobs in India"
            ]

            for query in queries:
                params = {
                    "engine": "google_jobs",
                    "q": query,
                    "hl": "en",
                    "api_key": self.api_key,
                    "chips": "date_posted:today" # Only today/recent
                }

                search = GoogleSearch(params)
                results = search.get_dict()
                jobs_results = results.get("jobs_results", [])

                for job in jobs_results:
                    title = job.get("title", "Unknown Role")
                    company = job.get("company_name", "Unknown Company")
                    location = job.get("location", "India")
                    salary = job.get("salary", "Not disclosed")
                    
                    # Google Jobs doesn't always give a direct link clearly, 
                    # often buried in `related_links` or `apply_options`.
                    # We'll take the first apply option if available.
                    apply_options = job.get("apply_options", [])
                    url = apply_options[0].get("link") if apply_options else "https://www.google.com/search?q=" + query.replace(" ", "+") # Fallback to search
                    
                    job_id = job.get("job_id", "")

                    if not job_id:
                        continue

                    jobs.append({
                        'company': company,
                        'role': title,
                        'location': self.normalize_location(location),
                        'posted_time': job.get("detected_extensions", {}).get("posted_at", "Recently"),
                        'salary': salary,
                        'url': url,
                        'source': 'Google Jobs', # Aggregates LinkedIn, Naukri etc.
                        'id': job_id
                    })
            
            logging.info(f"Found {len(jobs)} jobs from {self.name}")
            return jobs

        except Exception as e:
            logging.error(f"Error scraping Google Jobs: {e}", exc_info=True)
            return []
