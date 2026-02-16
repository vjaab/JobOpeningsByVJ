
import requests
from bs4 import BeautifulSoup
from .base import JobScraper
from datetime import datetime, timedelta
import logging
from email.utils import parsedate_to_datetime

class WeWorkRemotelyScraper(JobScraper):
    def __init__(self):
        super().__init__('WeWorkRemotely')
        self.feed_url = "https://weworkremotely.com/remote-jobs.rss"

    def scrape(self):
        try:
            logging.info(f"Fetching jobs from {self.name}...")
            response = requests.get(self.feed_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'xml')
            items = soup.find_all('item')
            jobs = []
            
            cutoff_time = datetime.now() - timedelta(hours=24)

            for item in items:
                pub_date_elem = item.find('pubDate')
                if not pub_date_elem:
                    continue
                pub_date_str = pub_date_elem.text

                pub_date = parsedate_to_datetime(pub_date_str)
                # Convert to naive or offset-aware comparison
                if pub_date.replace(tzinfo=None) < cutoff_time:
                    continue
                
                title_elem = item.find('title')
                title_text = title_elem.text if title_elem else "Unknown Role"
                
                link_elem = item.find('link')
                link = link_elem.text if link_elem else ""
                
                guid_elem = item.find('guid')
                guid = guid_elem.text if guid_elem else link

                # Extract company and role
                # Format is usually "Company: Role" or "Role: Company"
                # For WWR it's often "Company: Role"
                parts = title_text.split(':')
                if len(parts) >= 2:
                    company = parts[0].strip()
                    role = ':'.join(parts[1:]).strip()
                else:
                    role = title_text
                    company = "Unknown"

                # Filter by role keywords
                role_lower = role.lower()
                relevant_keywords = ['developer', 'software', 'engineer', 'devops', 'sre', 'backend', 'frontend', 'full stack', 'qa', 'tester']
                if not any(k in role_lower for k in relevant_keywords):
                    continue

                jobs.append({
                    'company': company,
                    'role': role,
                    'location': 'Remote', # WWR is mostly remote
                    'posted_time': "Recently",
                    'salary': "Not disclosed", # Usually not in RSS title
                    'url': link,
                    'source': 'WeWorkRemotely',
                    'id': guid
                })

            logging.info(f"Found {len(jobs)} jobs from {self.name}")
            return jobs

        except Exception as e:
            logging.error(f"Error scraping WeWorkRemotely: {e}", exc_info=True)
            return []
