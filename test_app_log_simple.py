#!/usr/bin/env python3
import mysql.connector
import pandas as pd
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_app_log_queries():
    """Test app_log queries without Streamlit dependencies"""
    
    # Get database connection details from environment
    host = os.getenv('DB_HOST')
    user = os.getenv('DB_USER')
    password = os.getenv('DB_PASSWORD')
    database = os.getenv('DB_NAME')
    port = int(os.getenv('DB_PORT', 3306))
    
    if not all([host, user, password, database]):
        print("❌ Database environment variables not found")
        print("Please set DB_HOST, DB_USER, DB_PASSWORD, DB_NAME in .env file")
        return
    
    try:
        # Connect to database
        connection = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port
        )
        
        print("✅ Connected to database successfully")
        
        # Test 1: Check app_log table structure
        print("\n🔍 Test 1: Checking app_log table structure...")
        query1 = """
        DESCRIBE fido1.app_log
        """
        result1 = pd.read_sql(query1, connection)
        print("App log table structure:")
        print(result1)
        
        # Test 2: Check app_log data summary
        print("\n🔍 Test 2: Checking app_log data summary...")
        query2 = """
        SELECT 
            COUNT(*) as total_records,
            COUNT(DISTINCT user_id) as unique_users,
            MIN(timestamp) as earliest_record,
            MAX(timestamp) as latest_record
        FROM fido1.app_log
        """
        result2 = pd.read_sql(query2, connection)
        print("App log summary:")
        print(result2)
        
        # Test 3: Check recent activity (last 14 days)
        print("\n🔍 Test 3: Checking recent activity (last 14 days)...")
        query3 = """
        SELECT 
            COUNT(DISTINCT user_id) as active_users_14_days,
            COUNT(*) as total_activities_14_days
        FROM fido1.app_log
        WHERE timestamp >= NOW() - INTERVAL 14 DAY
        AND user_id IS NOT NULL
        """
        result3 = pd.read_sql(query3, connection)
        print("Recent activity (14 days):")
        print(result3)
        
        # Test 4: Sample active users with company info
        print("\n🔍 Test 4: Sample active users with company info...")
        query4 = """
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
        LIMIT 5
        """
        result4 = pd.read_sql(query4, connection)
        print("Sample active users:")
        print(result4)
        
        # Test 5: Sample active users with partner info
        print("\n🔍 Test 5: Sample active users with partner info...")
        query5 = """
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
        LIMIT 5
        """
        result5 = pd.read_sql(query5, connection)
        print("Sample active users with partner info:")
        print(result5)
        
        # Test 6: Compare with old logger_sessions method
        print("\n🔍 Test 6: Comparing with old logger_sessions method...")
        query6 = """
        SELECT 
            (SELECT COUNT(DISTINCT user_id) 
             FROM fido1.app_log 
             WHERE timestamp >= NOW() - INTERVAL 14 DAY 
             AND user_id IS NOT NULL) as new_method_active_users,
            (SELECT COUNT(DISTINCT user_id) 
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
             ) old_method) as old_method_active_users
        """
        result6 = pd.read_sql(query6, connection)
        print("Comparison with old method:")
        print(result6)
        
        print("\n✅ All tests completed successfully!")
        
    except mysql.connector.Error as err:
        print(f"❌ Database error: {err}")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if 'connection' in locals() and connection.is_connected():
            connection.close()

if __name__ == "__main__":
    test_app_log_queries() 