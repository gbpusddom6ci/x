#!/usr/bin/env python3
"""
CLI tool for checking IOU news
Usage: python -m app72_iou.cli input.csv [output.csv]
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app72_iou.news_checker import process_iou_csv


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m app72_iou.cli <input.csv> [output.csv] [candle_minutes]")
        print("\nExample:")
        print("  python -m app72_iou.cli ornek.csv ornek_with_news.csv 72")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    candle_minutes = int(sys.argv[3]) if len(sys.argv) > 3 else 72
    
    if not os.path.exists(input_path):
        print(f"Error: File not found: {input_path}")
        sys.exit(1)
    
    print(f"Processing {input_path}...")
    print(f"Candle duration: {candle_minutes} minutes")
    print("-" * 60)
    
    results = process_iou_csv(input_path, output_path, candle_minutes)
    
    print("-" * 60)
    print(f"✓ Processed {len(results)} rows")
    
    if output_path:
        print(f"✓ Output saved to: {output_path}")


if __name__ == '__main__':
    main()
