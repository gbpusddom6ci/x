"""
IOU News Checker
Checks ForexFactory news events for each offset in IOU output
"""

import csv
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from forexfactory.scraper import ForexFactoryCalendar
from forexfactory.manual_data import get_manual_events

try:
    from forexfactory.selenium_scraper import SeleniumForexFactoryScraper
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


def parse_iou_timestamp(timestamp_str: str, year: int = 2025) -> datetime:
    """
    Parse IOU timestamp format: "06-09 08:24" -> datetime
    
    Args:
        timestamp_str: Timestamp string from IOU CSV
        year: Year to use (default 2025)
        
    Returns:
        Datetime object
    """
    try:
        # Format: "06-09 08:24" -> month-day hour:minute
        dt = datetime.strptime(f"{year}-{timestamp_str}", "%Y-%m-%d %H:%M")
        return dt
    except ValueError as e:
        print(f"Error parsing timestamp '{timestamp_str}': {e}")
        return None


def calculate_candle_range(start_dt: datetime, candle_minutes: int = 72) -> Tuple[datetime, datetime]:
    """
    Calculate candle time range
    
    Args:
        start_dt: Candle start time
        candle_minutes: Candle duration in minutes (default 72)
        
    Returns:
        Tuple of (start_time, end_time)
    """
    end_dt = start_dt + timedelta(minutes=candle_minutes)
    return start_dt, end_dt


def format_news_events(events: List[Dict]) -> str:
    """
    Format news events for output
    
    Args:
        events: List of event dictionaries
        
    Returns:
        Formatted string
    """
    if not events:
        return "-"
    
    formatted = []
    for event in events:
        impact = event.get('impact', 'N/A')
        event_name = event.get('event', 'Unknown')
        time_str = event.get('time', '')
        currency = event.get('currency', '')
        
        # Short format: [IMPACT] Currency Event @ Time
        formatted.append(f"[{impact.upper()[:3]}] {currency} {event_name} @ {time_str}")
    
    return " | ".join(formatted)


def check_iou_news(iou_csv_path: str, output_csv_path: str = None, candle_minutes: int = 72, year: int = 2025, use_manual_data: bool = False, use_selenium: bool = True) -> List[Dict]:
    """
    Check ForexFactory news for IOU CSV file
    
    Args:
        iou_csv_path: Path to IOU CSV file
        output_csv_path: Path to save output CSV (optional)
        candle_minutes: Candle duration in minutes (default 72)
        year: Year for date parsing (default 2025)
        
    Returns:
        List of processed rows with news information
    """
    # Read IOU CSV (supports both comma and tab delimiters)
    rows = []
    with open(iou_csv_path, 'r', encoding='utf-8') as f:
        # Skip empty lines at the beginning
        lines = [line for line in f.readlines() if line.strip()]
        
        if not lines:
            print("Empty file")
            return []
        
        # Detect delimiter from first non-empty line
        delimiter = '\t' if '\t' in lines[0] else ','
        
        # Parse CSV
        import io
        csv_content = io.StringIO(''.join(lines))
        reader = csv.DictReader(csv_content, delimiter=delimiter)
        
        for row in reader:
            # Skip empty rows
            if not row.get('Timestamp') or not row['Timestamp'].strip():
                continue
            rows.append(row)
    
    if not rows:
        print("No data found in CSV")
        return []
    
    # Determine date range for ForexFactory
    timestamps = []
    for row in rows:
        ts = parse_iou_timestamp(row['Timestamp'], year)
        if ts:
            timestamps.append(ts)
    
    if not timestamps:
        print("No valid timestamps found")
        return []
    
    min_date = min(timestamps).strftime('%Y-%m-%d')
    max_date = (max(timestamps) + timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Choose data source
    all_events = []
    
    if use_manual_data:
        print(f"📝 Using manual ForexFactory data (edit forexfactory/manual_data.py to add events)")
        all_events = get_manual_events()
    elif use_selenium and SELENIUM_AVAILABLE:
        print(f"🌐 Using Selenium scraper for {min_date} to {max_date}...")
        try:
            with SeleniumForexFactoryScraper() as scraper:
                all_events = scraper.get_calendar(min_date, max_date)
        except Exception as e:
            print(f"⚠️  Selenium failed: {e}")
            print("   Falling back to requests scraper...")
            use_selenium = False
    
    # Fallback to requests scraper
    if not all_events and not use_manual_data:
        print(f"📡 Trying requests-based scraper...")
        ff_scraper = ForexFactoryCalendar()
        all_events = ff_scraper.get_calendar(min_date, max_date)
    
    # Final fallback to manual data
    if not all_events:
        print("⚠️  All scraping methods failed, using manual data...")
        all_events = get_manual_events()
    
    # Process each row
    results = []
    for row in rows:
        timestamp_str = row.get('Timestamp', '')
        
        # Parse timestamp
        candle_start = parse_iou_timestamp(timestamp_str, year)
        
        if not candle_start:
            row['News'] = 'ERROR: Invalid timestamp'
            results.append(row)
            continue
        
        # Calculate candle range
        candle_start_dt, candle_end_dt = calculate_candle_range(candle_start, candle_minutes)
        
        # Filter events in this range
        matching_events = []
        for event in all_events:
            event_dt = event.get('datetime')
            if event_dt and candle_start_dt <= event_dt <= candle_end_dt:
                matching_events.append(event)
        
        # Format news
        news_str = format_news_events(matching_events)
        row['News'] = news_str
        
        results.append(row)
        
        print(f"Ofs={row.get('Ofs', '?'):>2} | {timestamp_str} -> {candle_end_dt.strftime('%H:%M')} | {news_str}")
    
    # Save to output CSV if specified
    if output_csv_path:
        save_results_to_csv(results, output_csv_path)
        print(f"\nResults saved to: {output_csv_path}")
    
    return results


def save_results_to_csv(results: List[Dict], output_path: str):
    """Save results to CSV file"""
    if not results:
        return
    
    # Get all fieldnames (original + News)
    fieldnames = list(results[0].keys())
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def process_iou_csv(input_path: str, output_path: str = None, candle_minutes: int = 72):
    """
    Convenience function to process IOU CSV
    
    Args:
        input_path: Input CSV path
        output_path: Output CSV path (default: input_with_news.csv)
        candle_minutes: Candle duration (default 72)
    """
    if output_path is None:
        base_name = os.path.splitext(input_path)[0]
        output_path = f"{base_name}_with_news.csv"
    
    return check_iou_news(input_path, output_path, candle_minutes)
