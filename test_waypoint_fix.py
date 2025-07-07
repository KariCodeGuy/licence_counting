#!/usr/bin/env python3
"""
Test script to verify the waypoint logs fix
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseConnection
from datetime import datetime, timedelta
import pandas as pd

def test_waypoint_fix():
    """Test the waypoint logs fix"""
    print("🔍 Testing Waypoint Logs Fix")
    print("=" * 50)
    
    db = DatabaseConnection()
    
    # Test 1: Check if waypoint table is accessible
    print("\n1. Testing waypoint table accessibility...")
    try:
        connection = db.get_connection()
        test_cursor = connection.cursor()
        test_cursor.execute("SELECT 1 FROM fido_way.waypoint_logs LIMIT 1")
        _ = test_cursor.fetchall()  # Fetch the result to avoid 'Unread result found'
        test_cursor.close()
        print("✅ fido_way.waypoint_logs table is accessible")
    except Exception as e:
        print(f"❌ fido_way.waypoint_logs table error: {e}")
        return
    
    # Test 2: Test get_waypoint_logs method
    print("\n2. Testing get_waypoint_logs() method...")
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7)
        
        waypoint_logs = db.get_waypoint_logs(
            start_date=start_date,
            end_date=end_date
        )
        print(f"✅ get_waypoint_logs() executed successfully")
        if not waypoint_logs.empty:
            print(f"   - Found {len(waypoint_logs)} waypoint log entries")
            print(f"   - Date range: {start_date} to {end_date}")
            print(f"   - Sample data:")
            print(waypoint_logs.head(3))
        else:
            print("   - No waypoint logs found for the specified date range")
    except Exception as e:
        print(f"❌ Error in get_waypoint_logs(): {e}")
    
    # Test 3: Test get_top_users_by_waypoints method
    print("\n3. Testing get_top_users_by_waypoints() method...")
    try:
        top_users = db.get_top_users_by_waypoints(
            start_date=start_date,
            end_date=end_date
        )
        print(f"✅ get_top_users_by_waypoints() executed successfully")
        if not top_users.empty:
            print(f"   - Found {len(top_users)} top users")
            print(f"   - Top users:")
            for idx, row in top_users.iterrows():
                print(f"   - #{idx+1}: {row['user_name']} ({row['waypoint_count']} waypoints)")
        else:
            print("   - No waypoint activity found for top users")
    except Exception as e:
        print(f"❌ Error in get_top_users_by_waypoints(): {e}")
    
    # Test 4: Test log filters
    print("\n4. Testing get_log_filters()...")
    try:
        filter_options = db.get_log_filters()
        print(f"✅ get_log_filters() executed successfully")
        print(f"   - Available log types: {filter_options['log_types']}")
        if 'Waypoint' in filter_options['log_types']:
            print("✅ Waypoint appears in available log types")
        else:
            print("❌ Waypoint does NOT appear in available log types")
    except Exception as e:
        print(f"❌ Error in get_log_filters(): {e}")
    
    # Test 5: Test unified logs with waypoint filter
    print("\n5. Testing unified logs with waypoint filter...")
    try:
        unified_logs = db.get_unified_logs(
            start_date=start_date,
            end_date=end_date,
            log_type="Waypoint"
        )
        print(f"✅ Unified logs with waypoint filter executed successfully")
        if not unified_logs.empty:
            print(f"   - Found {len(unified_logs)} unified waypoint log entries")
            print(f"   - Log sources: {unified_logs['log_source'].value_counts().to_dict()}")
        else:
            print("   - No unified waypoint logs found")
    except Exception as e:
        print(f"❌ Error in unified logs with waypoint filter: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Waypoint Logs Fix Testing Complete!")
    print("\nTo test in the dashboard:")
    print("1. Run: streamlit run app.py")
    print("2. Select 'System Logs' from the dashboard dropdown")
    print("3. Select 'Waypoint' from the Log Source dropdown")
    print("4. Check if waypoint data appears")

if __name__ == "__main__":
    test_waypoint_fix() 