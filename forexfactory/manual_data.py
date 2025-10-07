"""
Manual ForexFactory Data Entry
For use when scraping is blocked by anti-bot protection
"""

from datetime import datetime
from typing import List, Dict


def get_manual_events() -> List[Dict]:
    """
    Manually entered ForexFactory events
    Update this list with actual calendar data from ForexFactory.com
    
    Returns:
        List of event dictionaries
    """
    # Example events - REPLACE WITH ACTUAL DATA FROM FOREXFACTORY
    events = [
        # June 9, 2025 examples
        {
            'date': 'Jun09',
            'time': '8:30am',
            'datetime': datetime(2025, 6, 9, 8, 30),
            'currency': 'USD',
            'impact': 'High',
            'event': 'Non-Farm Employment Change',
            'actual': '',
            'forecast': '190K',
            'previous': '177K'
        },
        {
            'date': 'Jun09',
            'time': '8:30am',
            'datetime': datetime(2025, 6, 9, 8, 30),
            'currency': 'USD',
            'impact': 'High',
            'event': 'Unemployment Rate',
            'actual': '',
            'forecast': '4.0%',
            'previous': '4.1%'
        },
        {
            'date': 'Jun09',
            'time': '10:00am',
            'datetime': datetime(2025, 6, 9, 10, 0),
            'currency': 'USD',
            'impact': 'Medium',
            'event': 'Wholesale Inventories',
            'actual': '',
            'forecast': '0.2%',
            'previous': '0.1%'
        },
        # June 11, 2025 examples
        {
            'date': 'Jun11',
            'time': '8:30am',
            'datetime': datetime(2025, 6, 11, 8, 30),
            'currency': 'USD',
            'impact': 'High',
            'event': 'Core CPI',
            'actual': '',
            'forecast': '0.3%',
            'previous': '0.3%'
        },
        {
            'date': 'Jun11',
            'time': '2:00pm',
            'datetime': datetime(2025, 6, 11, 14, 0),
            'currency': 'USD',
            'impact': 'High',
            'event': 'FOMC Statement',
            'actual': '',
            'forecast': '',
            'previous': ''
        },
        {
            'date': 'Jun11',
            'time': '2:30pm',
            'datetime': datetime(2025, 6, 11, 14, 30),
            'currency': 'USD',
            'impact': 'High',
            'event': 'FOMC Press Conference',
            'actual': '',
            'forecast': '',
            'previous': ''
        },
        # June 12, 2025 examples
        {
            'date': 'Jun12',
            'time': '8:30am',
            'datetime': datetime(2025, 6, 12, 8, 30),
            'currency': 'USD',
            'impact': 'Medium',
            'event': 'Core PPI',
            'actual': '',
            'forecast': '0.2%',
            'previous': '0.5%'
        },
        # June 19, 2025 examples
        {
            'date': 'Jun19',
            'time': '2:00pm',
            'datetime': datetime(2025, 6, 19, 14, 0),
            'currency': 'USD',
            'impact': 'Medium',
            'event': 'Existing Home Sales',
            'actual': '',
            'forecast': '4.15M',
            'previous': '4.14M'
        },
    ]
    
    return events


def load_from_csv(csv_path: str) -> List[Dict]:
    """
    Load manually exported ForexFactory CSV
    
    CSV format:
    Date,Time,Currency,Impact,Event,Actual,Forecast,Previous
    
    Args:
        csv_path: Path to CSV file
        
    Returns:
        List of event dictionaries
    """
    import csv
    from datetime import datetime
    
    events = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Parse datetime
            date_str = row.get('Date', '')
            time_str = row.get('Time', '')
            
            try:
                dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %I:%M%p")
            except:
                dt = None
            
            events.append({
                'date': date_str,
                'time': time_str,
                'datetime': dt,
                'currency': row.get('Currency', ''),
                'impact': row.get('Impact', ''),
                'event': row.get('Event', ''),
                'actual': row.get('Actual', ''),
                'forecast': row.get('Forecast', ''),
                'previous': row.get('Previous', '')
            })
    
    return events
