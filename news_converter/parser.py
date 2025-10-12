"""
News data parser: Converts markdown format to JSON format for news_data/
"""

import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple


def parse_time_to_24h(time_str: str) -> Optional[str]:
    """
    Convert time like '9:30pm' or 'All Day' to 24h format.
    Returns None for 'All Day'.
    """
    time_str = time_str.strip()
    
    if time_str.lower() in ['all day', 'allday']:
        return None
    
    # Match format like "9:30pm" or "12:30am"
    match = re.match(r'(\d{1,2}):(\d{2})(am|pm)', time_str.lower())
    if not match:
        return None
    
    hour = int(match.group(1))
    minute = int(match.group(2))
    period = match.group(3)
    
    # Convert to 24h
    if period == 'pm' and hour != 12:
        hour += 12
    elif period == 'am' and hour == 12:
        hour = 0
    
    return f"{hour:02d}:{minute:02d}"


def parse_weekday(line: str) -> Optional[str]:
    """Check if line is a weekday (Sun, Mon, ...)"""
    days = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat']
    if line.strip().lower() in days:
        return line.strip().capitalize()
    return None


def parse_date(line: str, current_year: int = 2025) -> Optional[Tuple[str, str]]:
    """
    Parse date line like 'Mar 30' or 'Apr 1'.
    Returns (date_str, weekday) or None.
    """
    # Match "Mar 30" or "Apr 1"
    match = re.match(r'([A-Za-z]{3})\s+(\d{1,2})', line.strip())
    if not match:
        return None
    
    month_str = match.group(1)
    day = int(match.group(2))
    
    month_map = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    
    month = month_map.get(month_str.lower())
    if not month:
        return None
    
    try:
        date_obj = datetime(current_year, month, day)
        date_str = date_obj.strftime('%Y-%m-%d')
        weekday = date_obj.strftime('%a')
        return (date_str, weekday)
    except ValueError:
        return None


def parse_values(line: str) -> Dict[str, Optional[str]]:
    """
    Parse values line like '50.5\t50.4\t50.2' or '0.3%\t0.3%\t0.4%'.
    Returns dict with actual, forecast, previous.
    
    Handles future dates (Tentative):
    - 3 values: actual, forecast, previous (normal)
    - 2 values: forecast, previous (actual=null for future)
    - 1 value: forecast (actual=null, previous=null for future)
    """
    parts = [p.strip() for p in re.split(r'\t+', line.strip()) if p.strip()]
    
    result = {
        'actual': None,
        'forecast': None,
        'previous': None
    }
    
    if len(parts) == 1:
        # Could be actual (past) or forecast (future)
        # Assume forecast for now
        result['forecast'] = parts[0]
    elif len(parts) == 2:
        # Future dates: forecast, previous (actual not yet happened)
        result['forecast'] = parts[0]
        result['previous'] = parts[1]
    elif len(parts) >= 3:
        # Normal: actual, forecast, previous
        result['actual'] = parts[0]
        result['forecast'] = parts[1]
        result['previous'] = parts[2]
    
    return result


def parse_markdown_to_json(md_content: str, year: int = 2025) -> Dict[str, Any]:
    """
    Parse markdown format to JSON format compatible with news_data/.
    
    Returns:
        {
            'meta': {...},
            'days': [
                {
                    'date': '2025-03-30',
                    'weekday': 'Sun',
                    'events': [...]
                },
                ...
            ]
        }
    """
    lines = md_content.strip().split('\n')
    
    days_dict: Dict[str, Dict[str, Any]] = {}
    current_date = None
    current_weekday = None
    current_time = None
    current_currency = None
    current_title = None
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if not line:
            i += 1
            continue
        
        # Check weekday
        weekday = parse_weekday(line)
        if weekday:
            i += 1
            continue
        
        # Check date
        date_result = parse_date(line, year)
        if date_result:
            current_date, current_weekday = date_result
            if current_date not in days_dict:
                days_dict[current_date] = {
                    'date': current_date,
                    'weekday': current_weekday,
                    'events': []
                }
            i += 1
            continue
        
        # Check time
        time_24h = parse_time_to_24h(line)
        if time_24h is not None or line.lower() in ['all day', 'allday']:
            current_time = time_24h
            i += 1
            continue
        
        # Check currency (3 uppercase letters)
        if re.match(r'^[A-Z]{3}$', line):
            current_currency = line
            i += 1
            continue
        
        # Check if it's a title (not tabs, not values)
        if current_currency and current_time is not None and not re.search(r'\t', line):
            current_title = line
            i += 1
            
            # Next line should be values (or might be missing for future dates)
            values = None
            if i < len(lines):
                values_line = lines[i].strip()
                if re.search(r'\t', values_line) or re.match(r'^[\d\.%MKB\s]+$', values_line):
                    values = parse_values(values_line)
                    i += 1
            
            # If no values found, create event with TBD (for future dates)
            if values is None:
                values = {
                    'actual': 'TBD',
                    'forecast': None,
                    'previous': None
                }
            
            # Create event
            if current_date:
                event = {
                    'date': current_date,
                    'weekday': current_weekday,
                    'time_label': None,  # We don't have this
                    'time_24h': current_time,
                    'currency': current_currency,
                    'title': current_title,
                    'values': values
                }
                days_dict[current_date]['events'].append(event)
            
            current_title = None
            current_currency = None
            continue
        
        i += 1
    
    # Convert to list and sort
    days_list = sorted(days_dict.values(), key=lambda x: x['date'])
    
    # Calculate stats
    total_events = sum(len(day['events']) for day in days_list)
    date_range = f"{days_list[0]['date']} -> {days_list[-1]['date']}" if days_list else "N/A"
    
    return {
        'meta': {
            'source': 'markdown_converter',
            'year': year,
            'total_days': len(days_list),
            'total_events': total_events,
            'date_range': date_range
        },
        'days': days_list
    }
