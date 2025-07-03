#!/usr/bin/env python3
"""
Debug script to test waypoint queries and show raw SQL
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseConnection
from datetime import datetime, timedelta
import pandas as pd

def debug_waypoint_queries():
    """Debug waypoint queries and show raw SQL"""
    print("🔍 Debugging Waypoint Queries")
    print("=" * 50)
    
    db = DatabaseConnection()
    connection = db.get_connection()
    
    if not connection:
        print("❌ Could not connect to database")
        return
    
    try:
        # Test 1: Check if fido1.fidoapi_waypoint_logs exists
        print("\n1. Testing fido1.fidoapi_waypoint_logs table...")
        try:
            test_query = "SELECT 1 FROM fido1.fidoapi_waypoint_logs LIMIT 1"
            result = pd.read_sql(test_query, connection)
            print("✅ fido1.fidoapi_waypoint_logs table is accessible")
        except Exception as e:
            print(f"❌ fido1.fidoapi_waypoint_logs table error: {e}")
        
        # Test 2: Check if fido_way.waypoints exists
        print("\n2. Testing fido_way.waypoints table...")
        try:
            test_query = "SELECT 1 FROM fido_way.waypoints LIMIT 1"
            result = pd.read_sql(test_query, connection)
            print("✅ fido_way.waypoints table is accessible")
        except Exception as e:
            print(f"❌ fido_way.waypoints table error: {e}")
        
        # Test 2.5: Check fido_way.waypoint_logs table structure
        print("\n2.5. Testing fido_way.waypoint_logs table structure...")
        try:
            test_query = "SELECT 1 FROM fido_way.waypoint_logs LIMIT 1"
            result = pd.read_sql(test_query, connection)
            print("✅ fido_way.waypoint_logs table is accessible")
            
            # Check table structure
            structure_query = "DESCRIBE fido_way.waypoint_logs"
            structure_result = pd.read_sql(structure_query, connection)
            print("Table structure:")
            print(structure_result)
            
            # Check sample data
            sample_query = "SELECT * FROM fido_way.waypoint_logs LIMIT 3"
            sample_result = pd.read_sql(sample_query, connection)
            print("Sample data:")
            print(sample_result)
            
        except Exception as e:
            print(f"❌ fido_way.waypoint_logs table error: {e}")
        
        # Test 3: Show raw SQL for top users by waypoints
        print("\n3. Raw SQL for get_top_users_by_waypoints...")
        start_date = datetime.now().date() - timedelta(days=7)
        end_date = datetime.now().date()
        
        date_filter = f"AND fwl.datetime BETWEEN '{start_date} 00:00:00' AND '{end_date} 23:59:59'"
        raw_query = f'''
            SELECT 
                fwl.user_id,
                fwl.user_name,
                u.email,
                COUNT(*) AS waypoint_count
            FROM fido1.fidoapi_waypoint_logs fwl
            LEFT JOIN fido1.users_portal u ON fwl.user_id = u.id
            WHERE fwl.user_id IS NOT NULL {date_filter}
            GROUP BY fwl.user_id, fwl.user_name, u.email
            ORDER BY waypoint_count DESC
            LIMIT 3
        '''
        print("Raw SQL Query:")
        print(raw_query)
        
        # Test 4: Execute the raw query
        print("\n4. Executing raw query...")
        try:
            result = pd.read_sql(raw_query, connection)
            print(f"✅ Query executed successfully")
            print(f"   - Found {len(result)} users")
            if not result.empty:
                print("   - Results:")
                print(result)
            else:
                print("   - No results found")
        except Exception as e:
            print(f"❌ Query execution error: {e}")
        
        # Test 5: Check what tables exist with 'waypoint' in the name
        print("\n5. Searching for waypoint-related tables...")
        try:
            tables_query = """
            SELECT TABLE_SCHEMA, TABLE_NAME 
            FROM information_schema.TABLES 
            WHERE TABLE_NAME LIKE '%waypoint%' 
            OR TABLE_NAME LIKE '%way%'
            ORDER BY TABLE_SCHEMA, TABLE_NAME
            """
            tables_result = pd.read_sql(tables_query, connection)
            print("Waypoint-related tables found:")
            if not tables_result.empty:
                for _, row in tables_result.iterrows():
                    print(f"   - {row['TABLE_SCHEMA']}.{row['TABLE_NAME']}")
            else:
                print("   - No waypoint-related tables found")
        except Exception as e:
            print(f"❌ Error searching for tables: {e}")
        
        # Test 6: Check if there's any data in fido1.fidoapi_waypoint_logs
        print("\n6. Checking data in fido1.fidoapi_waypoint_logs...")
        try:
            data_query = """
            SELECT 
                COUNT(*) as total_records,
                COUNT(DISTINCT user_id) as unique_users,
                MIN(datetime) as earliest_record,
                MAX(datetime) as latest_record
            FROM fido1.fidoapi_waypoint_logs
            """
            data_result = pd.read_sql(data_query, connection)
            print("Data summary:")
            print(data_result)
        except Exception as e:
            print(f"❌ Error checking data: {e}")
        
        # Test 7: Check recent waypoint activity
        print("\n7. Checking recent waypoint activity...")
        try:
            recent_query = """
            SELECT 
                COUNT(*) as recent_records,
                COUNT(DISTINCT user_id) as recent_users
            FROM fido1.fidoapi_waypoint_logs
            WHERE datetime >= NOW() - INTERVAL 7 DAY
            """
            recent_result = pd.read_sql(recent_query, connection)
            print("Recent activity (7 days):")
            print(recent_result)
        except Exception as e:
            print(f"❌ Error checking recent activity: {e}")
        
        # Test 8: Check log filters to see if Waypoint appears
        print("\n8. Testing get_log_filters()...")
        try:
            filter_options = db.get_log_filters()
            print(f"Log types available: {filter_options['log_types']}")
            if 'Waypoint' in filter_options['log_types']:
                print("✅ Waypoint appears in log types")
            else:
                print("❌ Waypoint does NOT appear in log types")
        except Exception as e:
            print(f"❌ Error getting log filters: {e}")
        
    except Exception as e:
        print(f"❌ General error: {e}")
    finally:
        if connection.is_connected():
            connection.close()

if __name__ == "__main__":
    debug_waypoint_queries() 