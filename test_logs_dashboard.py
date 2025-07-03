#!/usr/bin/env python3
"""
Test script for the new Unified Logs Dashboard functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseConnection
from datetime import datetime, timedelta
import pandas as pd

def test_logs_functionality():
    """Test the new logs dashboard functionality"""
    print("🧪 Testing Unified Logs Dashboard Functionality")
    print("=" * 50)
    
    db = DatabaseConnection()
    
    # Test 1: Get filter options
    print("\n1. Testing get_log_filters()...")
    try:
        filter_options = db.get_log_filters()
        print(f"✅ Filter options loaded successfully")
        print(f"   - Users: {len(filter_options['users'])}")
        print(f"   - Companies: {len(filter_options['companies'])}")
        print(f"   - Partners: {len(filter_options['partners'])}")
        print(f"   - Log types: {filter_options['log_types']}")
    except Exception as e:
        print(f"❌ Error getting filter options: {e}")
    
    # Test 2: Get top waypoints today
    print("\n2. Testing get_top_waypoints_today()...")
    try:
        top_waypoints = db.get_top_waypoints_today()
        print(f"✅ Top waypoints loaded successfully")
        if not top_waypoints.empty:
            print(f"   - Found {len(top_waypoints)} active waypoints today")
            for idx, row in top_waypoints.iterrows():
                print(f"   - #{idx+1}: {row['waypoint_name']} ({row['actions_today']} actions)")
        else:
            print("   - No waypoint activity recorded today")
    except Exception as e:
        print(f"❌ Error getting top waypoints: {e}")
    
    # Test 3: Get top sessions today
    print("\n3. Testing get_top_sessions_today()...")
    try:
        top_sessions = db.get_top_sessions_today()
        print(f"✅ Top sessions loaded successfully")
        if not top_sessions.empty:
            print(f"   - Found {len(top_sessions)} active sessions today")
            for idx, row in top_sessions.iterrows():
                print(f"   - #{idx+1}: Session {row['session_id']} ({row['activity_count']} activities)")
        else:
            print("   - No session activity recorded today")
    except Exception as e:
        print(f"❌ Error getting top sessions: {e}")
    
    # Test 4: Get unified logs (last 7 days)
    print("\n4. Testing get_unified_logs()...")
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7)
        
        logs_df = db.get_unified_logs(
            start_date=start_date,
            end_date=end_date
        )
        print(f"✅ Unified logs loaded successfully")
        if not logs_df.empty:
            print(f"   - Found {len(logs_df)} log entries")
            print(f"   - Date range: {start_date} to {end_date}")
            print(f"   - Log sources: {logs_df['log_source'].value_counts().to_dict()}")
            print(f"   - Unique users: {logs_df['user_name'].nunique()}")
        else:
            print("   - No logs found for the specified date range")
    except Exception as e:
        print(f"❌ Error getting unified logs: {e}")
    
    # Test 5: Test with specific filters
    print("\n5. Testing get_unified_logs() with filters...")
    try:
        # Get first available company and partner for testing
        filter_options = db.get_log_filters()
        
        if filter_options['companies']:
            test_company_id = filter_options['companies'][0]['id']
            logs_filtered = db.get_unified_logs(
                start_date=start_date,
                end_date=end_date,
                company_id=test_company_id,
                log_type="App"
            )
            print(f"✅ Filtered logs loaded successfully")
            print(f"   - Company filter: {filter_options['companies'][0]['name']}")
            print(f"   - Log type filter: App")
            print(f"   - Found {len(logs_filtered)} filtered log entries")
        else:
            print("   - No companies available for filter testing")
    except Exception as e:
        print(f"❌ Error getting filtered logs: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Logs Dashboard Testing Complete!")
    print("\nTo view the dashboard:")
    print("1. Run: streamlit run app.py")
    print("2. Select 'System Logs' from the dashboard dropdown")
    print("3. Use the filters to explore the logs")

if __name__ == "__main__":
    test_logs_functionality() 