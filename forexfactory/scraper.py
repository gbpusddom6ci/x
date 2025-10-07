"""
ForexFactory Economic Calendar Scraper
Real-time scraping of economic calendar events
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time
import re
from .timezone_utils import est_to_utc4, convert_to_utc4


class ForexFactoryCalendar:
    """ForexFactory economic calendar scraper"""
    
    BASE_URL = "https://www.forexfactory.com/calendar"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.forexfactory.com/',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Cache-Control': 'max-age=0',
        })
        self.cache = {}
    
    def get_calendar(self, start_date: str, end_date: str) -> List[Dict]:
        """
        Get economic calendar events for date range
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            List of event dictionaries
        """
        # Check cache
        cache_key = f"{start_date}_{end_date}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Try different URL formats
        url_formats = [
            f"{self.BASE_URL}?week={start_date}",
            f"{self.BASE_URL}",  # No params - gets current week
            f"{self.BASE_URL}.php?week={start_date}",
        ]
        
        for url in url_formats:
            try:
                # Add some delay to avoid rate limiting
                time.sleep(2)
                
                response = self.session.get(url, timeout=20, allow_redirects=True)
                
                if response.status_code == 200:
                    events = self._parse_calendar_html(response.text)
                    
                    # Filter by date range
                    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                    
                    filtered_events = [
                        e for e in events
                        if e.get('datetime') and start_dt <= e['datetime'] <= end_dt + timedelta(days=1)
                    ]
                    
                    # Cache results
                    self.cache[cache_key] = filtered_events
                    
                    return filtered_events
                else:
                    print(f"HTTP {response.status_code} for {url}")
                    continue
                    
            except Exception as e:
                print(f"Error with {url}: {e}")
                continue
        
        # If all attempts fail
        print(f"⚠️  Could not fetch ForexFactory data for {start_date} - {end_date}")
        print(f"⚠️  This might be due to anti-bot protection or site changes.")
        print(f"⚠️  Consider using manual CSV export or wait and retry.")
        return []
    
    def _parse_calendar_html(self, html: str) -> List[Dict]:
        """Parse ForexFactory calendar HTML"""
        
        soup = BeautifulSoup(html, 'lxml')
        events = []
        current_date = None
        
        # Find calendar table
        calendar_table = soup.find('table', class_='calendar__table')
        
        if not calendar_table:
            print("Warning: Calendar table not found")
            return []
        
        rows = calendar_table.find_all('tr', class_='calendar__row')
        
        for row in rows:
            try:
                # Date cell
                date_cell = row.find('td', class_='calendar__cell calendar__date')
                if date_cell:
                    date_text = date_cell.get_text(strip=True)
                    if date_text:
                        current_date = date_text
                
                if not current_date:
                    continue
                
                # Time
                time_cell = row.find('td', class_='calendar__cell calendar__time')
                time_str = time_cell.get_text(strip=True) if time_cell else ''
                
                # Skip if no time (tentative events)
                if not time_str or time_str == 'Tentative' or time_str == 'All Day':
                    continue
                
                # Currency
                currency_cell = row.find('td', class_='calendar__cell calendar__currency')
                currency = currency_cell.get_text(strip=True) if currency_cell else ''
                
                # Impact
                impact_cell = row.find('td', class_='calendar__cell calendar__impact')
                impact = ''
                if impact_cell:
                    impact_span = impact_cell.find('span', class_=re.compile('icon--ff-impact'))
                    if impact_span:
                        if 'icon--ff-impact-red' in impact_span.get('class', []):
                            impact = 'High'
                        elif 'icon--ff-impact-ora' in impact_span.get('class', []):
                            impact = 'Medium'
                        elif 'icon--ff-impact-yel' in impact_span.get('class', []):
                            impact = 'Low'
                
                # Event name
                event_cell = row.find('td', class_='calendar__cell calendar__event')
                event_name = event_cell.get_text(strip=True) if event_cell else ''
                
                # Skip if no event name
                if not event_name:
                    continue
                
                # Actual, Forecast, Previous
                actual_cell = row.find('td', class_='calendar__cell calendar__actual')
                actual = actual_cell.get_text(strip=True) if actual_cell else ''
                
                forecast_cell = row.find('td', class_='calendar__cell calendar__forecast')
                forecast = forecast_cell.get_text(strip=True) if forecast_cell else ''
                
                previous_cell = row.find('td', class_='calendar__cell calendar__previous')
                previous = previous_cell.get_text(strip=True) if previous_cell else ''
                
                # Parse datetime (convert EST to UTC-4)
                event_dt = None
                if time_str and current_date:
                    year = datetime.now().year
                    event_dt = est_to_utc4(time_str, current_date, year)
                
                # Only add mid and high impact events
                if impact in ['Medium', 'High']:
                    events.append({
                        'date': current_date,
                        'time': time_str,
                        'datetime': event_dt,
                        'currency': currency,
                        'impact': impact,
                        'event': event_name,
                        'actual': actual,
                        'forecast': forecast,
                        'previous': previous
                    })
            
            except Exception as e:
                # Skip problematic rows
                continue
        
        return events
    
    def get_events_in_range(self, start_dt: datetime, end_dt: datetime, min_date: str, max_date: str) -> List[Dict]:
        """
        Get events within a specific datetime range
        
        Args:
            start_dt: Start datetime (UTC-4)
            end_dt: End datetime (UTC-4)
            min_date: Minimum date to fetch (YYYY-MM-DD)
            max_date: Maximum date to fetch (YYYY-MM-DD)
            
        Returns:
            List of events that fall within the time range
        """
        all_events = self.get_calendar(min_date, max_date)
        
        matching_events = []
        for event in all_events:
            if event.get('datetime'):
                # Check if event time is within the candle range
                if start_dt <= event['datetime'] <= end_dt:
                    matching_events.append(event)
        
        return matching_events


def get_calendar_for_date_range(start_date: str, end_date: str) -> List[Dict]:
    """
    Convenience function to get calendar events
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        
    Returns:
        List of event dictionaries
    """
    scraper = ForexFactoryCalendar()
    return scraper.get_calendar(start_date, end_date)
