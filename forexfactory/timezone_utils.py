"""
Timezone utilities for ForexFactory
ForexFactory uses EST/EDT, we need UTC-4
"""

from datetime import datetime, timedelta
import pytz


def convert_to_utc4(dt: datetime) -> datetime:
    """
    Convert datetime to UTC-4 timezone
    
    Args:
        dt: Input datetime (can be naive or aware)
        
    Returns:
        Datetime in UTC-4
    """
    utc4 = pytz.timezone('Etc/GMT+4')  # Note: GMT+4 is UTC-4
    
    if dt.tzinfo is None:
        # Naive datetime - assume it's already in the source timezone
        return utc4.localize(dt)
    else:
        # Aware datetime - convert to UTC-4
        return dt.astimezone(utc4)


def est_to_utc4(est_time_str: str, date_str: str, year: int = 2025) -> datetime:
    """
    Convert ForexFactory EST time to UTC-4
    
    Args:
        est_time_str: Time string like "8:30am" or "2:00pm"
        date_str: Date string like "Jun09" or "Jun 9"
        year: Year (default 2025)
        
    Returns:
        Datetime object in UTC-4
    """
    est = pytz.timezone('US/Eastern')
    
    # Parse the time
    try:
        time_obj = datetime.strptime(est_time_str.strip().lower(), '%I:%M%p')
    except ValueError:
        try:
            time_obj = datetime.strptime(est_time_str.strip().lower(), '%I:%M %p')
        except ValueError:
            # If parsing fails, return None or raise
            return None
    
    # Parse the date (ForexFactory format: "Jun09" or "Jun 9")
    date_clean = date_str.replace(' ', '')
    try:
        date_obj = datetime.strptime(f"{date_clean}{year}", '%b%d%Y')
    except ValueError:
        return None
    
    # Combine date and time
    combined = datetime(
        date_obj.year,
        date_obj.month,
        date_obj.day,
        time_obj.hour,
        time_obj.minute
    )
    
    # Localize to EST
    est_dt = est.localize(combined)
    
    # Convert to UTC-4
    return convert_to_utc4(est_dt)


def time_range_overlaps(start1: datetime, end1: datetime, start2: datetime, end2: datetime) -> bool:
    """
    Check if two time ranges overlap
    
    Args:
        start1, end1: First time range
        start2, end2: Second time range
        
    Returns:
        True if ranges overlap, False otherwise
    """
    return start1 <= end2 and end1 >= start2
