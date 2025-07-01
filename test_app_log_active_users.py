#!/usr/bin/env python3
import os
import pandas as pd
from database import DatabaseConnection

def test_app_log_active_users():
    """Test the new app_log-based active user tracking implementation"""
    db = DatabaseConnection()
    connection = db.get_connection()
    
    if not connection:
        print("❌ Could not connect to database")
        return
    
    try:
        print("🧪 Testing new app_log-based active user tracking...")
        
        # Test 1: Check if app_log table exists and has data
        print("\n🔍 Test 1: Checking app_log table structure and data...")
        query1 = """
        SELECT COUNT(*) as total_records,
               COUNT(DISTINCT user_id) as unique_users,
               MIN(timestamp) as earliest_record,
               MAX(timestamp) as latest_record
        FROM fido1.app_log
        """
        result1 = pd.read_sql(query1, connection)
        print(f"App log summary: {result1.iloc[0].to_dict()}")
        
        # Test 2: Check recent activity (last 14 days)
        print("\n🔍 Test 2: Checking recent activity (last 14 days)...")
        query2 = """
        SELECT COUNT(DISTINCT user_id) as active_users_14_days
        FROM fido1.app_log
        WHERE timestamp >= NOW() - INTERVAL 14 DAY
        AND user_id IS NOT NULL
        """
        result2 = pd.read_sql(query2, connection)
        print(f"Active users in last 14 days: {result2.iloc[0]['active_users_14_days']}")
        
        # Test 3: Check active users by company
        print("\n🔍 Test 3: Checking active users by company...")
        query3 = """
        SELECT 
            u.id AS user_id,
            u.name AS user_name,
            c.name AS company_name
        FROM fido1.users_portal u
        LEFT JOIN fido1.companies c ON u.company_id = c.id
        WHERE u.id IN (
            SELECT DISTINCT user_id
            FROM fido1.app_log
            WHERE timestamp >= NOW() - INTERVAL 14 DAY
            AND user_id IS NOT NULL
        )
        LIMIT 10
        """
        result3 = pd.read_sql(query3, connection)
        print(f"Sample active users by company: {len(result3)} users found")
        if not result3.empty:
            print(result3)
        
        # Test 4: Check active users by partner
        print("\n🔍 Test 4: Checking active users by partner...")
        query4 = """
        SELECT 
            u.id AS user_id,
            u.name AS user_name,
            c.name AS company_name,
            p.partner_name
        FROM fido1.users_portal u
        LEFT JOIN fido1.companies c ON u.company_id = c.id
        LEFT JOIN fido1.partners p ON c.partner_id = p.id
        WHERE u.id IN (
            SELECT DISTINCT user_id
            FROM fido1.app_log
            WHERE timestamp >= NOW() - INTERVAL 14 DAY
            AND user_id IS NOT NULL
        )
        LIMIT 10
        """
        result4 = pd.read_sql(query4, connection)
        print(f"Sample active users by partner: {len(result4)} users found")
        if not result4.empty:
            print(result4)
        
        # Test 5: Test the actual get_active_users_per_company method
        print("\n🔍 Test 5: Testing get_active_users_per_company method...")
        active_users_df = db.get_active_users_per_company()
        print(f"Active users per company/partner: {len(active_users_df)} entities found")
        if not active_users_df.empty:
            print(active_users_df)
        else:
            print("❌ No active users data returned")
        
        # Test 6: Compare with old logger_sessions method (for reference)
        print("\n🔍 Test 6: Comparing with old logger_sessions method...")
        query6 = """
        SELECT COUNT(DISTINCT user_id) as old_method_active_users
        FROM (
            SELECT deployed_by AS user_id
            FROM logger_sessions
            WHERE created >= CURDATE() - INTERVAL 14 DAY
            AND deployed_by IS NOT NULL
            UNION
            SELECT collected_by AS user_id
            FROM logger_sessions
            WHERE last_update >= CURDATE() - INTERVAL 14 DAY
            AND collected_by IS NOT NULL
        ) old_method
        """
        result6 = pd.read_sql(query6, connection)
        print(f"Old method active users: {result6.iloc[0]['old_method_active_users']}")
        
        print("\n✅ Testing completed!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
    finally:
        if connection.is_connected():
            connection.close()

if __name__ == "__main__":
    test_app_log_active_users() 