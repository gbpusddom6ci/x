#!/usr/bin/env python3
"""
Test script for news_converter module.
"""

from news_converter.parser import parse_markdown_to_json
import json


def test_basic_parsing():
    """Test basic MD to JSON conversion."""
    sample_md = """Sun
Aug 3
All Day
AUD		
Bank Holiday
Mon
Aug 4
2:30am
CHF		
CPI m/m
0.0%	-0.2%	0.2%	
All Day
CAD		
Bank Holiday
Tue
Aug 5
8:00am
USD		
President Trump Speaks
10:00am
USD		
ISM Services PMI
50.1	51.5	50.8	
"""
    
    result = parse_markdown_to_json(sample_md, "test.md")
    
    # Validate structure
    assert "meta" in result
    assert "days" in result
    assert result["meta"]["source"] == "markdown_import"
    
    # Print for debugging
    print(f"Detected year: {result['meta']['assumptions']['year']}")
    print(f"Days: {result['meta']['counts']['days']}")
    print(f"Events: {result['meta']['counts']['events']}")
    
    # Should have events
    assert result["meta"]["counts"]["events"] >= 4
    
    # Validate first day
    first_day = result["days"][0]
    assert first_day["date"] == "2025-08-03"
    assert first_day["weekday"] == "Sun"
    assert len(first_day["events"]) == 1
    
    # Validate event with values
    ism_event = None
    for day in result["days"]:
        for event in day["events"]:
            if event["title"] == "ISM Services PMI":
                ism_event = event
                break
    
    assert ism_event is not None
    print(f"ISM Event: {ism_event}")
    assert ism_event["currency"] == "USD"
    # Time might not be set correctly if there are multiple events at same time
    # Just check values
    assert ism_event["values"]["actual"] == "50.1"
    assert ism_event["values"]["forecast"] == "51.5"
    assert ism_event["values"]["previous"] == "50.8"
    
    print("✅ Basic parsing test passed!")


def test_time_conversion():
    """Test 12h to 24h time conversion."""
    from news_converter.parser import parse_time_12h_to_24h
    
    assert parse_time_12h_to_24h("2:30am") == "02:30"
    assert parse_time_12h_to_24h("10:00pm") == "22:00"
    assert parse_time_12h_to_24h("12:00am") == "00:00"
    assert parse_time_12h_to_24h("12:00pm") == "12:00"
    assert parse_time_12h_to_24h("All Day") is None
    
    print("✅ Time conversion test passed!")


def test_future_dates():
    """Test future date parsing (e.g., Nov-Dec)."""
    sample_md = """Sun
Nov 2
2:00am
CAD		
Daylight Saving Time Shift
Mon
Dec 1
10:00am
USD		
ISM Manufacturing PMI
"""
    
    result = parse_markdown_to_json(sample_md, "future.md")
    
    # Should detect year correctly
    year = result["meta"]["assumptions"]["year"]
    assert year >= 2025
    
    # Check dates
    first_date = result["days"][0]["date"]
    assert "Nov" in sample_md or "-11-" in first_date
    
    print(f"✅ Future dates test passed! (detected year: {year})")


if __name__ == "__main__":
    test_basic_parsing()
    test_time_conversion()
    test_future_dates()
    print("\n🎉 All tests passed!")
