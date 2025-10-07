#!/usr/bin/env python3
"""
ForexFactory Data Fetcher CLI
Fetch bulk economic calendar data
"""

import sys
import argparse
from pathlib import Path

try:
    from selenium_scraper import fetch_and_save_bulk, SELENIUM_AVAILABLE
except ImportError:
    from forexfactory.selenium_scraper import fetch_and_save_bulk, SELENIUM_AVAILABLE


def main():
    parser = argparse.ArgumentParser(
        description='Fetch ForexFactory economic calendar data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Fetch 40 weeks of data
  python3 -m forexfactory.cli --weeks 40
  
  # Fetch 10 weeks, save to custom file
  python3 -m forexfactory.cli --weeks 10 --output my_data.json
  
  # Fetch from specific date
  python3 -m forexfactory.cli --weeks 20 --from 2025-01-01
        '''
    )
    
    parser.add_argument(
        '-w', '--weeks',
        type=int,
        default=40,
        help='Number of weeks to fetch (default: 40)'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        default='forexfactory_data.json',
        help='Output JSON file (default: forexfactory_data.json)'
    )
    
    parser.add_argument(
        '-f', '--from',
        type=str,
        dest='from_date',
        help='Start date in YYYY-MM-DD format (default: 8 weeks ago)'
    )
    
    args = parser.parse_args()
    
    if not SELENIUM_AVAILABLE:
        print("❌ Selenium is not installed!")
        print("\n📦 Install with:")
        print("   pip install selenium")
        print("\n🌐 Also install ChromeDriver:")
        print("   Mac: brew install chromedriver")
        print("   Or download from: https://chromedriver.chromium.org/")
        sys.exit(1)
    
    print(f"{'='*60}")
    print(f"  ForexFactory Bulk Data Fetcher")
    print(f"{'='*60}")
    print(f"📅 Weeks to fetch: {args.weeks}")
    print(f"💾 Output file: {args.output}")
    if args.from_date:
        print(f"📆 Starting from: {args.from_date}")
    print(f"{'='*60}\n")
    
    try:
        fetch_and_save_bulk(num_weeks=args.weeks, output_file=args.output)
        print(f"\n{'='*60}")
        print(f"✅ SUCCESS! Data saved to: {args.output}")
        print(f"{'='*60}")
        print(f"\n💡 Next steps:")
        print(f"   1. Check the JSON file: cat {args.output}")
        print(f"   2. Use with app72_iou automatically (it will load from cache)")
        print(f"   3. Or manually update manual_data.py if needed")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print(f"\n💡 Troubleshooting:")
        print(f"   - Make sure Chrome/ChromeDriver is installed")
        print(f"   - Check your internet connection")
        print(f"   - Try with fewer weeks first: --weeks 1")
        sys.exit(1)


if __name__ == '__main__':
    main()
