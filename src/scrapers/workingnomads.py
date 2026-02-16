
import requests
from bs4 import BeautifulSoup
from .base import JobScraper
from datetime import datetime
import logging

class WorkingNomadsScraper(JobScraper):
    def __init__(self):
        super().__init__('WorkingNomads')
        self.url = "https://www.workingnomads.com/jobs?category=development,sysadmin&sort=newest"
        # Since Working Nomads might not have a clean RSS for exact filtering, we'll try parsing HTML or a known RSS
        # The RSS feed is simpler for recent checks.
        self.feed_url = "https://www.workingnomads.com/jobs/rss?category=development,sysadmin"

    def scrape(self):
        try:
            logging.info(f"Fetching jobs from {self.name}...")
            # For brevity, let's stick to RSS if it works easily
            response = requests.get(self.feed_url, headers=self.headers, timeout=15)
            # RSS processing similar to WWR
            # If RSS fails or is blocked, skip.
            
            # Actually, Working Nomads RSS often works.
            soup = BeautifulSoup(response.content, 'xml')
            items = soup.find_all('item')
            jobs = []
            
            # Their RSS date format: "Mon, 16 Feb 2026 12:00:00 +0000"
            from email.utils import parsedate_to_datetime
            
            cutoff_time = datetime.now() - timedelta(hours=24)

            for item in items:
                pub_date_data = item.find('pubDate')
                if not pub_date_data:
                    continue
                pub_date = parsedate_to_datetime(pub_date_data.text)
                if pub_date.replace(tzinfo=None) < cutoff_time:
                    continue
                
                title_elem = item.find('title')
                title = title_elem.text
                
                # Title format usually "Role @ Company"
                if " @ " in title:
                    role, company = title.rsplit(" @ ", 1)
                else:
                    role = title
                    company = "Unknown"
                
                link_elem = item.find('link')
                link = link_elem.text
                
                # Location isn't clearly in RSS title, often in description or just 'Remote'
                # Default to Remote
                location = "Remote"
                
                jobs.append({
                    'company': company,
                    'role': role,
                    'location': location,
                    'posted_time': "Recently",
                    'salary': "Not disclosed",
                    'url': link,
                    'source': 'WorkingNomads',
                    'id': link # Use URL as ID
                })

            logging.info(f"Found {len(jobs)} jobs from {self.name}")
            return jobs

        except Exception as e:
            logging.error(f"Error scraping WorkingNomads: {e}", exc_info=True)
            return []
