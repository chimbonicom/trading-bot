#!/usr/bin/env python3
"""
Performance Report Generator
Generates professional HTML performance reports for the Daily Open Bot
"""

from src.performance_analyzer import PerformanceAnalyzer
import sys

def main():
    print("📊 Daily Open Bot Performance Analyzer")
    print("=" * 60)
    print("🎯 Generate Professional Trading Reports")
    print("✅ HTML Performance Dashboard")
    print("✅ Trade Analysis & Statistics")
    print("✅ Daily Performance Breakdown")
    print("✅ Professional Visual Design")
    print("=" * 60)
    
    # Get days back from user input
    try:
        days_back = int(input("Enter number of days to analyze (default 30): ") or "30")
    except ValueError:
        days_back = 30
        
    print(f"\n📈 Analyzing last {days_back} days of trading...")
    
    try:
        analyzer = PerformanceAnalyzer()
        report_path = analyzer.generate_report(days_back)
        
        if report_path:
            print(f"\n🎉 Report generated successfully!")
            print(f"📁 Location: {report_path}")
            print("\n💡 To view the report:")
            print("1. Navigate to the reports folder")
            print("2. Open the HTML file in your web browser")
            print("3. Enjoy your professional trading analysis!")
            
    except Exception as e:
        print(f"\n❌ Error generating report: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
