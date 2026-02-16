
import logging
import requests
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

class JobScraper(ABC):
    def __init__(self, name):
        self.name = name
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    @abstractmethod
    def scrape(self):
        """
        Scrape jobs from the source.
        Returns:
            List of job dictionaries:
            {
                'company': str,
                'role': str,
                'location': str,
                'posted_time': str,
                'salary': str,
                'url': str,
                'source': str,
                'id': str (unique identifier for deduplication)
            }
        """
        pass

    def filter_recent_jobs(self, jobs):
        """
        Filter jobs posted in the last 24 hours.
        This implementation assumes 'posted_time' can be parsed or is relative.
        For simplicity, scrapers should return recent jobs directly if possible.
        """
        # This is a placeholder as parsing relative time strings varies by site
        return jobs

    def normalize_location(self, location):
        """
        Standardize location strings.
        """
        if not location:
            return "Unknown"
        
        loc_lower = location.lower()
        if "remote" in loc_lower:
            if "india" in loc_lower:
                return "Remote — India"
            elif "asia" in loc_lower:
                return "Remote — Asia"
            elif "worldwide" in loc_lower:
                return "Remote — Worldwide"
            else:
                return "Remote"
        
        # Simple mapping for major Indian cities
        cities = ["Bangalore", "Bengaluru", "Hyderabad", "Mumbai", "Chennai", "Delhi", "Pune", "Gurgaon", "Noida"]
        for city in cities:
            if city.lower() in loc_lower:
                return city
        
        return location.title()

    def get_flag(self, location):
        if "remote" in location.lower():
            return "🌍"
        elif any(c in location.lower() for c in ["bangalore", "bengaluru", "hyderabad", "mumbai", "chennai", "delhi", "pune", "india"]):
            return "🇮🇳"
        return "📍"
        
