#!/usr/bin/env python3
"""
Test script to verify that top performers respond to filters
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseConnection
from datetime import datetime, timedelta
import pandas as pd

def test_filtered_performers():
    """Test that top performers respond to filters"""
    print("🔍 Testing Filtered Top Performers")
    print("=" * 50)
    
    db = DatabaseConnection()
    
    # Test 1: Get top performers without filters (last 7 days)
    print("\n1. Testing top performers without filters (last 7 days)...")
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7)
        
        top_sessions = db.get_top_users_by_sessions(
            start_date=start_date,
            end_date=end_date
        )
        top_waypoints = db.get_top_users_by_waypoints(
            start_date=start_date,
            end_date=end_date
        )
        
        print(f"✅ Top sessions (unfiltered): {len(top_sessions)} users")
        if not top_sessions.empty:
            for idx, row in top_sessions.iterrows():
                print(f"   - #{idx+1}: {row['user_name']} ({row['session_count']} sessions)")
        
        print(f"✅ Top waypoints (unfiltered): {len(top_waypoints)} users")
        if not top_waypoints.empty:
            for idx, row in top_waypoints.iterrows():
                print(f"   - #{idx+1}: {row['user_name']} ({row['waypoint_count']} waypoints)")
    except Exception as e:
        print(f"❌ Error in unfiltered test: {e}")
    
    # Test 2: Get top performers with date filter (last 3 days)
    print("\n2. Testing top performers with date filter (last 3 days)...")
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=3)
        
        top_sessions_filtered = db.get_top_users_by_sessions(
            start_date=start_date,
            end_date=end_date
        )
        top_waypoints_filtered = db.get_top_users_by_waypoints(
            start_date=start_date,
            end_date=end_date
        )
        
        print(f"✅ Top sessions (3 days): {len(top_sessions_filtered)} users")
        if not top_sessions_filtered.empty:
            for idx, row in top_sessions_filtered.iterrows():
                print(f"   - #{idx+1}: {row['user_name']} ({row['session_count']} sessions)")
        
        print(f"✅ Top waypoints (3 days): {len(top_waypoints_filtered)} users")
        if not top_waypoints_filtered.empty:
            for idx, row in top_waypoints_filtered.iterrows():
                print(f"   - #{idx+1}: {row['user_name']} ({row['waypoint_count']} waypoints)")
    except Exception as e:
        print(f"❌ Error in date filtered test: {e}")
    
    # Test 3: Get filter options to test with specific user/company
    print("\n3. Testing with specific filters...")
    try:
        filter_options = db.get_log_filters()
        
        if filter_options['users']:
            test_user = filter_options['users'][0]
            print(f"Testing with user: {test_user['name']} (ID: {test_user['id']})")
            
            top_sessions_user = db.get_top_users_by_sessions(
                start_date=start_date,
                end_date=end_date,
                user_id=test_user['id']
            )
            
            print(f"✅ Top sessions (user filtered): {len(top_sessions_user)} users")
            if not top_sessions_user.empty:
                for idx, row in top_sessions_user.iterrows():
                    print(f"   - #{idx+1}: {row['user_name']} ({row['session_count']} sessions)")
        
        if filter_options['companies']:
            test_company = filter_options['companies'][0]
            print(f"Testing with company: {test_company['name']} (ID: {test_company['id']})")
            
            top_waypoints_company = db.get_top_users_by_waypoints(
                start_date=start_date,
                end_date=end_date,
                company_id=test_company['id']
            )
            
            print(f"✅ Top waypoints (company filtered): {len(top_waypoints_company)} users")
            if not top_waypoints_company.empty:
                for idx, row in top_waypoints_company.iterrows():
                    print(f"   - #{idx+1}: {row['user_name']} ({row['waypoint_count']} waypoints)")
    except Exception as e:
        print(f"❌ Error in specific filter test: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Filtered Top Performers Testing Complete!")
    print("\nThe top performers should now respond to:")
    print("- Date range filters")
    print("- User filters") 
    print("- Company filters")
    print("- Partner filters")

if __name__ == "__main__":
    test_filtered_performers() 