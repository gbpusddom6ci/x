"""
Markdown news format parser for ForexFactory-style news data.
Converts from markdown format to JSON structure.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple


WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
}


@dataclass
class NewsEvent:
    """Single news event."""
    date: str  # YYYY-MM-DD
    weekday: str
    currency: str
    title: str
    time_label: str
    time_24h: Optional[str]
    values: Dict[str, Optional[str]]


@dataclass
class DayEvents:
    """Events for a single day."""
    date: str  # YYYY-MM-DD
    weekday: str
    events: List[NewsEvent]


def parse_time_12h_to_24h(time_str: str) -> Optional[str]:
    """
    Convert 12-hour format to 24-hour format.
    Examples: "2:30am" -> "02:30", "10:00pm" -> "22:00"
    """
    time_str = time_str.strip().lower()
    
    if time_str in ["all day", "tentative", "day 1", "day 2", "day 3"]:
        return None
    
    # Match patterns like "2:30am", "10:00pm"
    match = re.match(r'(\d{1,2}):(\d{2})(am|pm)', time_str)
    if not match:
        return None
    
    hour = int(match.group(1))
    minute = match.group(2)
    period = match.group(3)
    
    # Convert to 24-hour
    if period == "pm" and hour != 12:
        hour += 12
    elif period == "am" and hour == 12:
        hour = 0
    
    return f"{hour:02d}:{minute}"


def infer_year_from_date_range(first_month: str, last_month: str) -> int:
    """
    Infer the year based on the date range in the markdown.
    Strategy:
    - If data spans Nov-Jan (crosses year), assume it's current year
    - If first month is 2+ months in the past, assume next year
    - If first month is in the future (2+ months ahead), assume current year
    - Otherwise, use current year
    """
    now = datetime.now()
    current_year = now.year
    current_month = now.month
    
    first_month_num = MONTHS.get(first_month, 1)
    last_month_num = MONTHS.get(last_month, 12)
    
    # Check if data crosses year boundary (e.g., Nov -> Jan)
    if first_month_num > last_month_num:
        # Crosses year, use current year for the earlier months
        return current_year
    
    # Calculate distance from current month
    distance_to_first = first_month_num - current_month
    
    # If data starts 3+ months in the past, likely next year's data
    if distance_to_first < -2:
        return current_year + 1
    # If data starts 3+ months in the future, use current year
    elif distance_to_first > 2:
        return current_year
    # Data is within a reasonable range of current month
    else:
        return current_year


def parse_markdown_to_json(md_content: str, filename: str = "unknown") -> Dict[str, Any]:
    """
    Parse markdown news format to JSON structure.
    
    Args:
        md_content: The markdown content as string
        filename: Source filename for metadata
        
    Returns:
        Dictionary with meta and days structure
    """
    lines = md_content.strip().split('\n')
    
    current_weekday = None
    current_date = None
    current_time_label = None
    current_time_24h = None
    
    days_dict: Dict[str, DayEvents] = {}
    events_list: List[NewsEvent] = []
    
    # Track months for year inference
    months_seen = []
    
    i = 0
    while i < len(lines):
        line_raw = lines[i]
        line = line_raw.strip()
        
        # Skip empty lines
        if not line:
            i += 1
            continue
        
        # Check if it's a weekday line
        if line in WEEKDAYS:
            current_weekday = line
            i += 1
            continue
        
        # Check if it's a date line (e.g., "Aug 3")
        # But not "Day 1", "Day 2", etc.
        date_match = re.match(r'([A-Z][a-z]{2})\s+(\d{1,2})$', line)
        if date_match and date_match.group(1) in MONTHS:
            month_str = date_match.group(1)
            day = int(date_match.group(2))
            
            if month_str not in months_seen:
                months_seen.append(month_str)
            
            # We'll set the full date later once we know the year
            current_date = (month_str, day)
            i += 1
            continue
        
        # Check if it's a time label
        time_match = re.match(r'^(\d{1,2}:\d{2}[ap]m|All Day|Tentative|Day \d+)$', line, re.IGNORECASE)
        if time_match:
            current_time_label = time_match.group(1)
            current_time_24h = parse_time_12h_to_24h(current_time_label)
            i += 1
            continue
        
        # Check if it's a currency line (3 capital letters, possibly with tabs/spaces after)
        # Use the raw line to detect tabs
        currency_match = re.match(r'^([A-Z]{3})[\s\t]+', line_raw)
        if currency_match:
            currency = currency_match.group(1)
            i += 1
            
            # Next line should be the title
            if i < len(lines):
                title = lines[i].strip()
                i += 1
                
                # Next line might have values (3 tab-separated values)
                values = {"actual": None, "forecast": None, "previous": None}
                if i < len(lines):
                    value_line = lines[i].strip()
                    # Check if this line is actually a time label (not a value)
                    is_time_label = re.match(r'^(\d{1,2}:\d{2}[ap]m|All Day|Tentative|Day \d+)$', value_line, re.IGNORECASE)
                    # Check if it's a currency line (next event)
                    is_currency = re.match(r'^([A-Z]{3})[\s\t]+', lines[i] if i < len(lines) else "")
                    
                    if value_line and not value_line in WEEKDAYS and not re.match(r'([A-Z][a-z]{2})\s+(\d{1,2})$', value_line) and not is_time_label and not is_currency:
                        # Parse values
                        parts = [p.strip() for p in value_line.split('\t') if p.strip()]
                        if len(parts) == 3:
                            values["actual"] = parts[0]
                            values["forecast"] = parts[1]
                            values["previous"] = parts[2]
                        elif len(parts) == 2:
                            # Two values: interpret as (actual, previous)
                            values["actual"] = parts[0]
                            values["forecast"] = None
                            values["previous"] = parts[1]
                        elif len(parts) == 1:
                            values["actual"] = parts[0]
                        
                        i += 1
                
                # Create event
                if current_date and current_weekday:
                    # We'll finalize the date string later
                    event = NewsEvent(
                        date=f"{current_date[0]}-{current_date[1]}",  # Temporary
                        weekday=current_weekday,
                        currency=currency,
                        title=title,
                        time_label=current_time_label or "All Day",
                        time_24h=current_time_24h,
                        values=values
                    )
                    events_list.append(event)
            continue
        
        # If nothing matched, move to next line
        i += 1
    
    # Infer year from the month range
    if months_seen:
        year = infer_year_from_date_range(months_seen[0], months_seen[-1])
    else:
        year = datetime.now().year
    
    # Convert events to proper date strings and group by date
    for event in events_list:
        month_str, day = event.date.split('-')
        month_num = MONTHS[month_str]
        date_str = f"{year}-{month_num:02d}-{int(day):02d}"
        event.date = date_str
        
        if date_str not in days_dict:
            days_dict[date_str] = DayEvents(date=date_str, weekday=event.weekday, events=[])
        
        days_dict[date_str].events.append(event)
    
    # Sort days by date
    sorted_dates = sorted(days_dict.keys())
    
    # Build final structure
    days_output = []
    for date_str in sorted_dates:
        day_data = days_dict[date_str]
        days_output.append({
            "date": day_data.date,
            "weekday": day_data.weekday,
            "events": [
                {
                    "date": e.date,
                    "weekday": e.weekday,
                    "currency": e.currency,
                    "title": e.title,
                    "time_label": e.time_label,
                    "time_24h": e.time_24h,
                    "values": e.values
                }
                for e in day_data.events
            ]
        })
    
    total_events = sum(len(day["events"]) for day in days_output)
    
    # Build meta section
    meta = {
        "source": "markdown_import",
        "source_file": filename,
        "assumptions": {
            "year": year,
            "time_zone": "UTC-4",
            "value_columns_order": ["actual", "forecast", "previous"],
            "two_value_rule": "When only two values are present, interpret as (actual, previous)."
        },
        "counts": {
            "days": len(days_output),
            "events": total_events
        }
    }
    
    return {
        "meta": meta,
        "days": days_output
    }
