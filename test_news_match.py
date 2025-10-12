#!/usr/bin/env python3
import json
from datetime import datetime, timedelta

# Load news data
with open('news_data/2marto30mar.json', 'r') as f:
    data = json.load(f)

events_by_date = {}
for day in data.get('days', []):
    date_str = day.get('date')
    events = day.get('events', [])
    if date_str:
        events_by_date[date_str] = events

# Test timestamp from CSV (first candle)
test_ts = datetime(2025, 3, 16, 18, 0)  # 18:00
duration = 48

print(f"Testing: {test_ts} + {duration}min")
print(f"Range: {test_ts} -> {test_ts + timedelta(minutes=duration)}")

# Check dates
dates_to_check = {test_ts.strftime('%Y-%m-%d')}
end_ts = test_ts + timedelta(minutes=duration)
if end_ts.date() != test_ts.date():
    dates_to_check.add(end_ts.strftime('%Y-%m-%d'))

print(f"Checking dates: {dates_to_check}")

# Find matching events
matching = []
for date_str in dates_to_check:
    events = events_by_date.get(date_str, [])
    print(f"\n{date_str}: {len(events)} events total")
    
    for event in events:
        time_24h = event.get('time_24h')
        if not time_24h:
            continue
        
        try:
            hour, minute = map(int, time_24h.split(':'))
            year, month, day = map(int, date_str.split('-'))
            event_ts = datetime(year, month, day, hour, minute)
            
            in_range = test_ts <= event_ts < end_ts
            print(f"  {time_24h} {event['currency']} {event['title'][:30]}: {in_range}")
            
            if in_range:
                matching.append(event)
        except Exception as e:
            print(f"  Error: {e}")

print(f"\n✅ Matched events: {len(matching)}")
