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
        
        # Check if these users have any logger sessions
        print("\n🔍 Checking logger sessions for users with partner_id = 32...")
        query2 = """
        SELECT u.id, u.partner_id, ls.deployed_by, ls.collected_by, ls.created, ls.last_update 
        FROM users_portal u 
        LEFT JOIN logger_sessions ls ON (ls.deployed_by = u.id OR ls.collected_by = u.id) 
        WHERE u.partner_id = 32 
        LIMIT 10
        """
        result2 = pd.read_sql(query2, connection)
        print(f"Logger sessions found: {len(result2)}")
        if not result2.empty:
            print(result2)
        
        # Check recent activity (last 14 days)
        print("\n🔍 Checking recent activity (last 14 days)...")
        query3 = """
        SELECT u.id, u.partner_id, ls.deployed_by, ls.collected_by, ls.created, ls.last_update 
        FROM users_portal u 
        INNER JOIN logger_sessions ls ON (ls.deployed_by = u.id OR ls.collected_by = u.id) 
        WHERE u.partner_id = 32 
        AND (ls.created >= CURDATE() - INTERVAL 14 DAY OR ls.last_update >= CURDATE() - INTERVAL 14 DAY)
        """
        result3 = pd.read_sql(query3, connection)
        print(f"Recent activity found: {len(result3)}")
        if not result3.empty:
            print(result3)
        
        # Check the actual active users query for partner_id = 32
        print("\n🔍 Running the active users query for partner_id = 32...")
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
        LEFT JOIN (
            SELECT DISTINCT deployed_by AS user_id
            FROM logger_sessions
            WHERE created >= CURDATE() - INTERVAL 14 DAY
            AND deployed_by IS NOT NULL
            UNION
            SELECT DISTINCT collected_by AS user_id
            FROM logger_sessions
            WHERE last_update >= CURDATE() - INTERVAL 14 DAY
            AND collected_by IS NOT NULL
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