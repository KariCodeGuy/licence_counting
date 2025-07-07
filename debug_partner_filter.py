#!/usr/bin/env python3
"""
Debug script to test partner filtering specifically
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseConnection
from datetime import datetime, timedelta
import pandas as pd

def debug_partner_filter():
    """Debug partner filtering"""
    print("🔍 Debugging Partner Filtering")
    print("=" * 50)
    
    db = DatabaseConnection()
    
    # Test 1: Get all partners to find Detection Services
    print("\n1. Getting all partners...")
    try:
        filter_options = db.get_log_filters()
        print(f"Available partners:")
        for partner in filter_options['partners']:
            print(f"   - {partner['name']} (ID: {partner['id']})")
        
        # Find Detection Services
        detection_services = None
        for partner in filter_options['partners']:
            if 'detection' in partner['name'].lower() or 'detection services' in partner['name'].lower():
                detection_services = partner
                break
        
        if detection_services:
            print(f"\nFound Detection Services: {detection_services['name']} (ID: {detection_services['id']})")
        else:
            print("\n❌ Detection Services not found in partners list")
            return
    except Exception as e:
        print(f"❌ Error getting partners: {e}")
        return
    
    # Test 2: Test top performers without partner filter
    print("\n2. Testing top performers without partner filter...")
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7)
        
        top_sessions_unfiltered = db.get_top_users_by_sessions(
            start_date=start_date,
            end_date=end_date
        )
        top_waypoints_unfiltered = db.get_top_users_by_waypoints(
            start_date=start_date,
            end_date=end_date
        )
        
        print(f"✅ Top sessions (unfiltered): {len(top_sessions_unfiltered)} users")
        if not top_sessions_unfiltered.empty:
            for idx, row in top_sessions_unfiltered.iterrows():
                print(f"   - #{idx+1}: {row['user_name']} ({row['session_count']} sessions)")
        
        print(f"✅ Top waypoints (unfiltered): {len(top_waypoints_unfiltered)} users")
        if not top_waypoints_unfiltered.empty:
            for idx, row in top_waypoints_unfiltered.iterrows():
                print(f"   - #{idx+1}: {row['user_name']} ({row['waypoint_count']} waypoints)")
    except Exception as e:
        print(f"❌ Error in unfiltered test: {e}")
    
    # Test 3: Test top performers with Detection Services partner filter
    print(f"\n3. Testing top performers with Detection Services partner filter (ID: {detection_services['id']})...")
    try:
        top_sessions_filtered = db.get_top_users_by_sessions(
            start_date=start_date,
            end_date=end_date,
            partner_id=detection_services['id']
        )
        top_waypoints_filtered = db.get_top_users_by_waypoints(
            start_date=start_date,
            end_date=end_date,
            partner_id=detection_services['id']
        )
        
        print(f"✅ Top sessions (Detection Services filtered): {len(top_sessions_filtered)} users")
        if not top_sessions_filtered.empty:
            for idx, row in top_sessions_filtered.iterrows():
                print(f"   - #{idx+1}: {row['user_name']} ({row['session_count']} sessions)")
        else:
            print("   - No session activity found for Detection Services")
        
        print(f"✅ Top waypoints (Detection Services filtered): {len(top_waypoints_filtered)} users")
        if not top_waypoints_filtered.empty:
            for idx, row in top_waypoints_filtered.iterrows():
                print(f"   - #{idx+1}: {row['user_name']} ({row['waypoint_count']} waypoints)")
        else:
            print("   - No waypoint activity found for Detection Services")
    except Exception as e:
        print(f"❌ Error in partner filtered test: {e}")
    
    # Test 4: Check if there are any users associated with Detection Services
    print(f"\n4. Checking users associated with Detection Services...")
    try:
        connection = db.get_connection()
        if connection:
            # Check app_log for Detection Services users
            app_query = f'''
            SELECT DISTINCT 
                u.id,
                CONCAT(u.first_name, ' ', u.last_name) as user_name,
                u.email,
                u.partner_id
            FROM fido1.app_log al
            LEFT JOIN fido1.users_portal u ON al.user_id = u.id
            WHERE u.partner_id = {detection_services['id']}
            AND al.timestamp >= '{start_date} 00:00:00'
            LIMIT 10
            '''
            app_users = pd.read_sql(app_query, connection)
            print(f"✅ App users for Detection Services: {len(app_users)} users")
            if not app_users.empty:
                for _, row in app_users.iterrows():
                    print(f"   - {row['user_name']} ({row['email']})")
            
            # Check waypoint_logs for Detection Services users
            waypoint_query = f'''
            SELECT DISTINCT 
                u.id,
                CONCAT(u.first_name, ' ', u.last_name) as user_name,
                u.email,
                u.partner_id
            FROM fido_way.waypoint_logs wl
            LEFT JOIN fido1.users_portal u ON wl.user_id = u.id
            WHERE u.partner_id = {detection_services['id']}
            AND wl.datetime >= '{start_date} 00:00:00'
            LIMIT 10
            '''
            waypoint_users = pd.read_sql(waypoint_query, connection)
            print(f"✅ Waypoint users for Detection Services: {len(waypoint_users)} users")
            if not waypoint_users.empty:
                for _, row in waypoint_users.iterrows():
                    print(f"   - {row['user_name']} ({row['email']})")
            
            connection.close()
    except Exception as e:
        print(f"❌ Error checking Detection Services users: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Partner Filter Debug Complete!")

if __name__ == "__main__":
    debug_partner_filter() 