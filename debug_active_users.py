#!/usr/bin/env python3
import os
import pandas as pd
from database import DatabaseConnection

def debug_active_users():
    db = DatabaseConnection()
    connection = db.get_connection()
    
    if not connection:
        print("❌ Could not connect to database")
        return
    
    try:
        # Check users with partner_id = 32
        print("🔍 Checking users with partner_id = 32...")
        query1 = "SELECT COUNT(*) as total_users FROM users_portal WHERE partner_id = 32"
        result1 = pd.read_sql(query1, connection)
        print(f"Total users with partner_id = 32: {result1.iloc[0]['total_users']}")
        
        # Check if these users have any app_log entries
        print("\n🔍 Checking app_log entries for users with partner_id = 32...")
        query2 = """
        SELECT u.id, u.partner_id, al.user_id, al.action, al.timestamp 
        FROM users_portal u 
        LEFT JOIN fido1.app_log al ON al.user_id = u.id 
        WHERE u.partner_id = 32 
        LIMIT 10
        """
        result2 = pd.read_sql(query2, connection)
        print(f"App log entries found: {len(result2)}")
        if not result2.empty:
            print(result2)
        
        # Check recent activity (last 14 days) from app_log
        print("\n🔍 Checking recent activity (last 14 days) from app_log...")
        query3 = """
        SELECT u.id, u.partner_id, al.user_id, al.action, al.timestamp 
        FROM users_portal u 
        INNER JOIN fido1.app_log al ON al.user_id = u.id 
        WHERE u.partner_id = 32 
        AND al.timestamp >= NOW() - INTERVAL 14 DAY
        """
        result3 = pd.read_sql(query3, connection)
        print(f"Recent activity found: {len(result3)}")
        if not result3.empty:
            print(result3)
        
        # Check the actual active users query for partner_id = 32 (using app_log)
        print("\n🔍 Running the active users query for partner_id = 32 (using app_log)...")
        query4 = """
        SELECT 
          p.partner_name as entity_name,
          'Partner' as entity_type,
          lr.number_of_licenses,
          COUNT(DISTINCT u.id) AS active_users,
          ROUND(COUNT(DISTINCT u.id) / lr.number_of_licenses, 2) AS utilization_ratio
        FROM license_records lr
        JOIN partners p ON lr.partner_id = p.id
        LEFT JOIN users_portal u ON u.partner_id = p.id
        INNER JOIN (
            SELECT DISTINCT user_id
            FROM fido1.app_log
            WHERE timestamp >= NOW() - INTERVAL 14 DAY
            AND user_id IS NOT NULL
        ) recent_activity ON recent_activity.user_id = u.id
        WHERE lr.partner_id = 32
        GROUP BY lr.id, p.partner_name, lr.number_of_licenses
        """
        result4 = pd.read_sql(query4, connection)
        print(f"Active users query result: {len(result4)} rows")
        if not result4.empty:
            print(result4)
        else:
            print("❌ No results from active users query")
            
            # Check if there are any license records for partner_id = 32
            query5 = "SELECT COUNT(*) as license_count FROM license_records WHERE partner_id = 32"
            result5 = pd.read_sql(query5, connection)
            print(f"License records for partner_id = 32: {result5.iloc[0]['license_count']}")
            
            # Check if partner_id = 32 exists in partners table
            query6 = "SELECT partner_name FROM partners WHERE id = 32"
            result6 = pd.read_sql(query6, connection)
            if not result6.empty:
                print(f"Partner name: {result6.iloc[0]['partner_name']}")
            else:
                print("❌ Partner with id = 32 not found in partners table")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if connection.is_connected():
            connection.close()

if __name__ == "__main__":
    debug_active_users() 