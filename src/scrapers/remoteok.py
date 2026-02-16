
import requests
from .base import JobScraper
from datetime import datetime, timedelta
import logging

class RemoteOKScraper(JobScraper):
    def __init__(self):
        super().__init__('RemoteOK')
        self.api_url = "https://remoteok.com/api"

    def scrape(self):
        try:
            logging.info(f"Fetching jobs from {self.name}...")
            response = requests.get(self.api_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            jobs = []
            # Skip the first item as it's often legal text
            if len(data) > 0 and 'legal' in data[0]:
                data = data[1:]

            cutoff_time = datetime.now() - timedelta(hours=24)

            for item in data:
                # Check date
                date_str = item.get('date', '')
                try:
                    # RemoteOK returns ISO format sometimes, or relative
                    # For API, 'date' is usually ISO 8601
                    job_date = datetime.strptime(date_str.split('T')[0], "%Y-%m-%d")
                    if job_date < cutoff_time:
                        continue
                except ValueError:
                    # Fallback or skip if date parsing fails
                    logging.warning(f"Could not parse date: {date_str}")
                    continue

                title = item.get('position', 'Unknown Role')
                company = item.get('company', 'Unknown Company')
                location = item.get('location', 'Remote')
                url = item.get('url', '')
                tags = item.get('tags', [])
                
                # Check for relevant tags
                relevant_tags = {'dev', 'engineer', 'developer', 'backend', 'frontend', 'full stack', 'sre', 'devops', 'qa', 'test'}
                if not any(tag.lower() in relevant_tags for tag in tags) and \
                   not any(role in title.lower() for role in ['developer', 'engineer', 'sre', 'devops', 'tester']):
                    continue

                jobs.append({
                    'company': company,
                    'role': title,
                    'location': self.normalize_location(location),
                    'posted_time': "Recently", # Since we filter by date
                    'salary': item.get('salary_min', '') + " - " + item.get('salary_max', '') if item.get('salary_max') else "Not disclosed",
                    'url': url,
                    'source': 'RemoteOK',
                    'id': item.get('id', url)
                })

            logging.info(f"Found {len(jobs)} jobs from {self.name}")
            return jobs

        except Exception as e:
            logging.error(f"Error scraping RemoteOK: {e}", exc_info=True)
            return []
