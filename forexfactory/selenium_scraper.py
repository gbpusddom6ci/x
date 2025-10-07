"""
ForexFactory Selenium Scraper
Uses headless browser to bypass anti-bot protection
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("⚠️  Selenium not installed. Run: pip install selenium")


class SeleniumForexFactoryScraper:
    """ForexFactory scraper using Selenium"""
    
    BASE_URL = "https://www.forexfactory.com/calendar"
    CACHE_DIR = Path(__file__).parent / "cache"
    
    def __init__(self, headless: bool = True):
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium not installed. Run: pip install selenium")
        
        self.headless = headless
        self.driver = None
        self.CACHE_DIR.mkdir(exist_ok=True)
    
    def _init_driver(self):
        """Initialize Chrome driver"""
        if self.driver:
            return
        
        options = Options()
        if self.headless:
            options.add_argument('--headless=new')
        
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Try to use Chrome
        try:
            self.driver = webdriver.Chrome(options=options)
        except Exception as e:
            print(f"⚠️  Chrome driver failed: {e}")
            print("💡 Trying Safari...")
            try:
                self.driver = webdriver.Safari()
            except Exception as e2:
                print(f"❌ Safari failed too: {e2}")
                raise Exception("No webdriver available. Install chromedriver or use Safari.")
    
    def _get_cache_path(self, start_date: str, end_date: str) -> Path:
        """Get cache file path for date range"""
        return self.CACHE_DIR / f"ff_{start_date}_{end_date}.json"
    
    def _load_from_cache(self, start_date: str, end_date: str) -> Optional[List[Dict]]:
        """Load events from cache if available"""
        cache_path = self._get_cache_path(start_date, end_date)
        
        if cache_path.exists():
            # Check if cache is less than 7 days old
            cache_age = time.time() - cache_path.stat().st_mtime
            if cache_age < 7 * 24 * 3600:  # 7 days
                with open(cache_path, 'r') as f:
                    data = json.load(f)
                print(f"✅ Loaded from cache: {cache_path.name}")
                return data
        
        return None
    
    def _save_to_cache(self, events: List[Dict], start_date: str, end_date: str):
        """Save events to cache"""
        cache_path = self._get_cache_path(start_date, end_date)
        
        # Convert datetime to string for JSON
        events_json = []
        for event in events:
            event_copy = event.copy()
            if event_copy.get('datetime'):
                event_copy['datetime'] = event_copy['datetime'].isoformat()
            events_json.append(event_copy)
        
        with open(cache_path, 'w') as f:
            json.dump(events_json, f, indent=2)
        
        print(f"💾 Saved to cache: {cache_path.name}")
    
    def get_calendar(self, start_date: str, end_date: str) -> List[Dict]:
        """
        Get economic calendar for date range using Selenium
        
        Args:
            start_date: YYYY-MM-DD
            end_date: YYYY-MM-DD
            
        Returns:
            List of event dictionaries
        """
        # Check cache first
        cached = self._load_from_cache(start_date, end_date)
        if cached:
            return self._restore_datetime(cached)
        
        # Initialize driver
        self._init_driver()
        
        try:
            # Navigate to calendar with date
            url = f"{self.BASE_URL}?week={start_date}"
            print(f"🌐 Fetching: {url}")
            self.driver.get(url)
            
            # Wait for table to load
            wait = WebDriverWait(self.driver, 20)
            table = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "calendar__table"))
            )
            
            # Small delay to ensure full load
            time.sleep(2)
            
            # Parse the table
            events = self._parse_table(start_date, end_date)
            
            # Save to cache
            if events:
                self._save_to_cache(events, start_date, end_date)
            
            return events
            
        except Exception as e:
            print(f"❌ Error fetching calendar: {e}")
            return []
    
    def _restore_datetime(self, events: List[Dict]) -> List[Dict]:
        """Restore datetime objects from cached JSON"""
        restored = []
        for event in events:
            event_copy = event.copy()
            if event_copy.get('datetime'):
                event_copy['datetime'] = datetime.fromisoformat(event_copy['datetime'])
            restored.append(event_copy)
        return restored
    
    def _parse_table(self, start_date: str, end_date: str) -> List[Dict]:
        """Parse calendar table"""
        events = []
        current_date = None
        
        rows = self.driver.find_elements(By.CSS_SELECTOR, "tr.calendar__row")
        
        for row in rows:
            try:
                # Date
                date_cell = row.find_elements(By.CSS_SELECTOR, "td.calendar__date")
                if date_cell and date_cell[0].text.strip():
                    current_date = date_cell[0].text.strip()
                
                if not current_date:
                    continue
                
                # Time
                time_cells = row.find_elements(By.CSS_SELECTOR, "td.calendar__time")
                time_str = time_cells[0].text.strip() if time_cells else ''
                
                if not time_str or time_str in ['Tentative', 'All Day', 'Day']:
                    continue
                
                # Currency
                currency_cells = row.find_elements(By.CSS_SELECTOR, "td.calendar__currency")
                currency = currency_cells[0].text.strip() if currency_cells else ''
                
                # Impact
                impact = ''
                impact_cells = row.find_elements(By.CSS_SELECTOR, "td.calendar__impact span")
                if impact_cells:
                    classes = impact_cells[0].get_attribute('class')
                    if 'red' in classes:
                        impact = 'High'
                    elif 'ora' in classes or 'orange' in classes:
                        impact = 'Medium'
                    elif 'yel' in classes or 'yellow' in classes:
                        impact = 'Low'
                
                # Event name
                event_cells = row.find_elements(By.CSS_SELECTOR, "td.calendar__event")
                event_name = event_cells[0].text.strip() if event_cells else ''
                
                if not event_name:
                    continue
                
                # Actual, Forecast, Previous
                actual_cells = row.find_elements(By.CSS_SELECTOR, "td.calendar__actual")
                actual = actual_cells[0].text.strip() if actual_cells else ''
                
                forecast_cells = row.find_elements(By.CSS_SELECTOR, "td.calendar__forecast")
                forecast = forecast_cells[0].text.strip() if forecast_cells else ''
                
                previous_cells = row.find_elements(By.CSS_SELECTOR, "td.calendar__previous")
                previous = previous_cells[0].text.strip() if previous_cells else ''
                
                # Parse datetime
                event_dt = self._parse_datetime(current_date, time_str)
                
                # Filter: only Mid/High impact
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
    
    def _parse_datetime(self, date_str: str, time_str: str) -> Optional[datetime]:
        """Parse ForexFactory datetime to UTC-4"""
        try:
            # ForexFactory format: "MonDD" like "Jun09"
            year = datetime.now().year
            
            # Clean date string
            date_clean = date_str.replace(' ', '')
            
            # Parse date
            dt_date = datetime.strptime(f"{date_clean}{year}", '%b%d%Y')
            
            # Parse time (12-hour format)
            time_clean = time_str.lower().replace(' ', '')
            dt_time = datetime.strptime(time_clean, '%I:%M%p')
            
            # Combine
            combined = datetime(
                dt_date.year,
                dt_date.month,
                dt_date.day,
                dt_time.hour,
                dt_time.minute
            )
            
            # ForexFactory uses EST/EDT, convert to UTC-4
            # For simplicity, assuming EST (UTC-5) + 1 hour = UTC-4
            # More accurate: use pytz
            import pytz
            est = pytz.timezone('US/Eastern')
            utc4 = pytz.timezone('Etc/GMT+4')
            
            combined_est = est.localize(combined)
            combined_utc4 = combined_est.astimezone(utc4)
            
            return combined_utc4.replace(tzinfo=None)  # Naive datetime in UTC-4
            
        except Exception as e:
            return None
    
    def get_bulk_weeks(self, num_weeks: int = 40, from_date: Optional[str] = None) -> List[Dict]:
        """
        Fetch multiple weeks of data
        
        Args:
            num_weeks: Number of weeks to fetch
            from_date: Start date (YYYY-MM-DD), default is 8 weeks ago
            
        Returns:
            All events from all weeks
        """
        if from_date:
            start = datetime.strptime(from_date, '%Y-%m-%d')
        else:
            # Start from 8 weeks ago (to cover historical data)
            start = datetime.now() - timedelta(weeks=8)
        
        all_events = []
        
        for week in range(num_weeks):
            week_start = start + timedelta(weeks=week)
            week_end = week_start + timedelta(days=6)
            
            start_str = week_start.strftime('%Y-%m-%d')
            end_str = week_end.strftime('%Y-%m-%d')
            
            print(f"\n📅 Week {week + 1}/{num_weeks}: {start_str} to {end_str}")
            
            events = self.get_calendar(start_str, end_str)
            all_events.extend(events)
            
            print(f"   Found {len(events)} mid/high impact events")
            
            # Rate limiting - be nice
            if week < num_weeks - 1:  # Don't wait after last week
                time.sleep(3)
        
        return all_events
    
    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def fetch_and_save_bulk(num_weeks: int = 40, output_file: str = 'forexfactory_data.json'):
    """
    Convenience function to fetch bulk data and save to JSON
    
    Args:
        num_weeks: Number of weeks to fetch
        output_file: Output JSON file path
    """
    if not SELENIUM_AVAILABLE:
        print("❌ Selenium not installed. Run: pip install selenium")
        return
    
    print(f"🚀 Fetching {num_weeks} weeks of ForexFactory data...")
    
    with SeleniumForexFactoryScraper() as scraper:
        events = scraper.get_bulk_weeks(num_weeks)
    
    # Save to JSON
    events_json = []
    for event in events:
        event_copy = event.copy()
        if event_copy.get('datetime'):
            event_copy['datetime'] = event_copy['datetime'].isoformat()
        events_json.append(event_copy)
    
    with open(output_file, 'w') as f:
        json.dump(events_json, f, indent=2)
    
    print(f"\n✅ Saved {len(events)} events to {output_file}")
    print(f"💡 Use this data in your app by loading: json.load(open('{output_file}'))")
