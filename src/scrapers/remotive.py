
import requests
from .base import JobScraper
from datetime import datetime, timedelta
import logging

class RemotiveScraper(JobScraper):
    def __init__(self):
        super().__init__('Remotive')
        self.api_url = "https://remotive.com/api/remote-jobs"

    def scrape(self):
        try:
            logging.info(f"Fetching jobs from {self.name}...")
            response = requests.get(self.api_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # Remotive returns {'0-legal-notice': ..., 'jobs': [...]}
            jobs_data = data.get('jobs', [])
            
            jobs = []
            cutoff_time = datetime.now() - timedelta(hours=24)

            for item in jobs_data:
                # Remotive provides 'publication_date' usually in ISO format
                date_str = item.get('publication_date', '')
                try:
                    job_date = datetime.strptime(date_str.split('T')[0], "%Y-%m-%d")
                    if job_date < cutoff_time:
                        continue
                except ValueError:
                    continue

                title = item.get('title', 'Unknown Role')
                company = item.get('company_name', 'Unknown Company')
                location = item.get('candidate_required_location', 'Remote')
                url = item.get('url', '')
                tags = item.get('tags', [])
                category = item.get('category', '').lower()
                
                # Filter by role/category
                relevant_categories = ['software development', 'qa', 'devops / sysadmin', 'data']
                if category not in relevant_categories:
                    # check title just in case
                    if not any(role in title.lower() for role in ['developer', 'engineer', 'sre', 'devops', 'tester']):
                        continue

                jobs.append({
                    'company': company,
                    'role': title,
                    'location': self.normalize_location(location),
                    'posted_time': "Recently",
                    'salary': item.get('salary', 'Not disclosed'),
                    'url': url,
                    'source': 'Remotive',
                    'id': str(item.get('id', url))
                })

            logging.info(f"Found {len(jobs)} jobs from {self.name}")
            return jobs

        except Exception as e:
            logging.error(f"Error scraping Remotive: {e}", exc_info=True)
            return []
