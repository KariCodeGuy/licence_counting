import mysql.connector
import pandas as pd
import os
from dotenv import load_dotenv
import datetime
from sqlalchemy.orm import sessionmaker
from models import engine, LicenseRecord, Company, Partner, LicenseProductCode, UserPortal, LoggerSession
import streamlit as st

# Load environment variables
load_dotenv()

# Create a new session
Session = sessionmaker(bind=engine)

class DatabaseConnection:
    """Database connection handler for MySQL"""
    
    def __init__(self):
        self.host = st.secrets["database"]["host"]
        self.user = st.secrets["database"]["user"]
        self.password = st.secrets["database"]["password"]
        self.database = st.secrets["database"]["name"]
        self.port = int(st.secrets["database"].get("port", 3306))
        self.session = Session()
        
    def get_connection(self):
        """Establish database connection"""
        try:
            connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port
            )
            return connection
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            return None
    
    def fetch_license_data(self, start_date=None, end_date=None):
        """Fetch license data from your existing database schema"""
        try:
            query = self.session.query(
                LicenseRecord, 
                Company.company_name.label('company_name'),
                Partner.partner_name.label('partner_name'),
                LicenseProductCode.code.label('product_code'),
                LicenseProductCode.label.label('product_label')
            )
            query = query.outerjoin(Company, LicenseRecord.company_id == Company.id)
            query = query.outerjoin(Partner, LicenseRecord.partner_id == Partner.id)
            query = query.outerjoin(LicenseProductCode, LicenseRecord.product_code_id == LicenseProductCode.id)
            if start_date:
                query = query.filter(LicenseRecord.start_date >= start_date)
            if end_date:
                query = query.filter(LicenseRecord.start_date <= end_date)
            licenses = query.all()
            
            # Convert list of tuples to DataFrame
            data = []
            for license_record, company_name, partner_name, product_code, product_label in licenses:
                row = license_record.__dict__.copy()
                row.pop('_sa_instance_state', None)  # Remove SQLAlchemy state
                
                # Set the entity name based on whether it's a company or partner license
                if company_name:
                    row['company'] = company_name
                    row['partner'] = None
                    row['entity_type'] = 'Company'
                elif partner_name:
                    row['company'] = None  # Leave company empty for partner licenses
                    row['partner'] = partner_name
                    row['entity_type'] = 'Partner'
                else:
                    row['company'] = 'Unknown'
                    row['partner'] = None
                    row['entity_type'] = 'Unknown'
                
                # Add product code information
                row['product_code'] = product_code
                row['product_label'] = product_label
                    
                data.append(row)
            
            df = pd.DataFrame(data)
            return df
            
        except Exception as e:
            print(f"Error fetching data: {e}")
            return pd.DataFrame()
        finally:
            self.session.close()
            
    def insert_license(self, license_data):
        """Insert new license record into license_records table"""
        try:
            new_license = LicenseRecord(**license_data)
            self.session.add(new_license)
            self.session.commit()
            return True
        except Exception as e:
            print(f"Error inserting data: {e}")
            self.session.rollback()
            return False
            
    def get_active_companies(self):
        """Fetch active companies from database"""
        connection = self.get_connection()
        if not connection:
            return []
        
        try:
            cursor = connection.cursor(dictionary=True)
            query = "SELECT id, company_name FROM companies WHERE active = 1"
            cursor.execute(query)
            companies = cursor.fetchall()
            return companies
        except Exception as e:
            print(f"Error fetching companies: {e}")
            return []
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def get_active_partners(self):
        """Fetch active partners from database"""
        connection = self.get_connection()
        if not connection:
            return []
        
        try:
            cursor = connection.cursor(dictionary=True)
            query = "SELECT id, partner_name AS name FROM partners"
            cursor.execute(query)
            partners = cursor.fetchall()
            return partners
        except Exception as e:
            print(f"Error fetching partners: {e}")
            return []
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def get_product_codes(self):
        """Fetch product codes from database"""
        connection = self.get_connection()
        if not connection:
            return []
        
        try:
            cursor = connection.cursor(dictionary=True)
            query = "SELECT id, code, label FROM license_product_codes ORDER BY code"
            cursor.execute(query)
            product_codes = cursor.fetchall()
            return product_codes
        except Exception as e:
            print(f"Error fetching product codes: {e}")
            return []
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def get_product_code_by_code(self, code):
        """Fetch a specific product code by its code value"""
        connection = self.get_connection()
        if not connection:
            return None
        
        try:
            cursor = connection.cursor(dictionary=True)
            query = "SELECT id, code, label FROM license_product_codes WHERE code = %s"
            cursor.execute(query, (code,))
            result = cursor.fetchone()
            return result
        except Exception as e:
            print(f"Error fetching product code: {e}")
            return None
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def update_license(self, license_id, license_data):
        """Update existing license record in license_records table"""
        try:
            license_record = self.session.query(LicenseRecord).filter_by(id=license_id).first()
            if not license_record:
                print("License record not found.")
                return False
            for key, value in license_data.items():
                setattr(license_record, key, value)
            self.session.commit()
            return True
        except Exception as e:
            print(f"Error updating license: {e}")
            self.session.rollback()
            return False

    def delete_license(self, license_id):
        """Delete existing license record from license_records table"""
        try:
            license_record = self.session.query(LicenseRecord).filter_by(id=license_id).first()
            if not license_record:
                print("License record not found.")
                return False
            self.session.delete(license_record)
            self.session.commit()
            return True
        except Exception as e:
            print(f"Error deleting license: {e}")
            self.session.rollback()
            return False

    def close(self):
        self.session.close()

    def get_active_users_per_company(self):
        """Fetch active users per company or partner based on the last 14 days of activity from fido1.app_log table"""
        connection = self.get_connection()
        if not connection:
            return pd.DataFrame()
        
        try:
            # Get active users for company and partner licenses using fido1.app_log table
            query = '''
            SELECT 
              c.company_name as entity_name,
              'Company' as entity_type,
              lr.number_of_licenses,
              COUNT(DISTINCT u.id) AS active_users,
              ROUND(COUNT(DISTINCT u.id) / lr.number_of_licenses, 2) AS utilization_ratio
            FROM license_records lr
            JOIN companies c ON lr.company_id = c.id
            LEFT JOIN users_portal u ON u.company_id = c.id
            INNER JOIN (
                SELECT DISTINCT user_id
                FROM fido1.app_log
                WHERE timestamp >= NOW() - INTERVAL 14 DAY
                AND user_id IS NOT NULL
            ) recent_activity ON recent_activity.user_id = u.id
            WHERE lr.company_id IS NOT NULL
            GROUP BY lr.id, c.company_name, lr.number_of_licenses
            
            UNION ALL
            
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
            WHERE lr.partner_id IS NOT NULL
            GROUP BY lr.id, p.partner_name, lr.number_of_licenses
            '''
            
            df = pd.read_sql(query, connection)
            return df
        
        except Exception as e:
            print(f"Error fetching active users per company/partner: {e}")
            return pd.DataFrame()
        finally:
            if connection.is_connected():
                connection.close()

    def get_user_count_from_portal(self):
        """Fetch user count per company and partner from users_portal table"""
        connection = self.get_connection()
        if not connection:
            return pd.DataFrame()
        
        try:
            # Get user counts for both company and partner licenses
            query = '''
            SELECT 
                c.company_name as entity_name,
                'Company' as entity_type,
                COUNT(u.id) as user_count
            FROM users_portal u
            JOIN companies c ON u.company_id = c.id
            WHERE u.active = 1
            GROUP BY c.id, c.company_name
            
            UNION ALL
            
            SELECT 
                p.partner_name as entity_name,
                'Partner' as entity_type,
                COUNT(u.id) as user_count
            FROM users_portal u
            JOIN partners p ON u.partner_id = p.id
            WHERE u.active = 1
            GROUP BY p.id, p.partner_name
            '''
            
            df = pd.read_sql(query, connection)
            return df
            
        except Exception as e:
            print(f"Error fetching user count from portal: {e}")
            return pd.DataFrame()
        finally:
            if connection.is_connected():
                connection.close()

    def get_active_relay_devices(self, user_role=None, user_company_id=None, user_partner_id=None):
        """Fetch active relay devices by user, company and partner based on 14-day activity"""
        connection = self.get_connection()
        if not connection:
            return pd.DataFrame()
        
        try:
            # Build role-based filtering
            role_filter = ""
            if user_role == "Company User" and user_company_id:
                role_filter = f"AND u.company_id = {user_company_id}"
            elif user_role == "Partner Admin" and user_partner_id:
                role_filter = f"AND (c.partner_id = {user_partner_id} OR u.partner_id = {user_partner_id})"
            # Admin role sees all data, so no additional filter needed
            
            # Use the corrected query with user-level granularity
            query = f'''
            SELECT 
                u.id AS user_id,
                CONCAT(u.first_name, ' ', u.last_name) AS user_name,
                u.email,
                c.company_name,
                COALESCE(p_from_company.partner_name, p_direct.partner_name) AS partner_name,
                COUNT(DISTINCT ram.relay_id) AS active_relay_devices
            FROM fido1.relay_activity_monitor ram
            LEFT JOIN fido1.logger_sessions ls ON ram.session_id = ls.session_id
            LEFT JOIN fido1.users_portal u ON ls.deployed_by = u.id
            LEFT JOIN fido1.companies c ON u.company_id = c.id
            LEFT JOIN fido1.partners p_from_company ON c.partner_id = p_from_company.id
            LEFT JOIN fido1.partners p_direct ON u.partner_id = p_direct.id
            WHERE ram.create_time >= CURDATE() - INTERVAL 14 DAY
            {role_filter}
            GROUP BY u.id, u.first_name, u.last_name, u.email, c.company_name, partner_name
            ORDER BY active_relay_devices DESC
            '''
            
            df = pd.read_sql(query, connection)
            return df
            
        except Exception as e:
            print(f"Error fetching active relay devices: {e}")
            return pd.DataFrame()
        finally:
            if connection.is_connected():
                connection.close()

    def get_unified_logs(self, start_date=None, end_date=None, user_id=None, company_id=None, partner_id=None, log_type=None):
        """Fetch unified logs from portal_logs, app_log, and fidoapi_waypoint_logs tables"""
        connection = self.get_connection()
        if not connection:
            return pd.DataFrame()
        
        try:
            # Build date filter for each table type
            portal_date_filter = ""
            app_date_filter = ""
            waypoint_date_filter = ""
            
            if start_date and end_date:
                portal_date_filter = f"AND CONCAT(pl.date, ' ', pl.time) BETWEEN '{start_date} 00:00:00' AND '{end_date} 23:59:59'"
                app_date_filter = f"AND al.timestamp BETWEEN '{start_date} 00:00:00' AND '{end_date} 23:59:59'"
                waypoint_date_filter = f"AND fwl.datetime BETWEEN '{start_date} 00:00:00' AND '{end_date} 23:59:59'"
            elif start_date:
                portal_date_filter = f"AND CONCAT(pl.date, ' ', pl.time) >= '{start_date} 00:00:00'"
                app_date_filter = f"AND al.timestamp >= '{start_date} 00:00:00'"
                waypoint_date_filter = f"AND fwl.datetime >= '{start_date} 00:00:00'"
            elif end_date:
                portal_date_filter = f"AND CONCAT(pl.date, ' ', pl.time) <= '{end_date} 23:59:59'"
                app_date_filter = f"AND al.timestamp <= '{end_date} 23:59:59'"
                waypoint_date_filter = f"AND fwl.datetime <= '{end_date} 23:59:59'"
            
            # Build company filter
            portal_company_filter = ""
            app_company_filter = ""
            waypoint_company_filter = ""
            if company_id:
                portal_company_filter = f"AND pl.company_id = {company_id}"
                app_company_filter = f"AND u.company_id = {company_id}"
                waypoint_company_filter = f"AND u.company_id = {company_id}"
            
            # Build partner filter
            portal_partner_filter = ""
            app_partner_filter = ""
            waypoint_partner_filter = ""
            if partner_id:
                portal_partner_filter = f"AND pl.partner_id = {partner_id}"
                app_partner_filter = f"AND u.partner_id = {partner_id}"
                waypoint_partner_filter = f"AND u.partner_id = {partner_id}"
            
            # Build user filter (only for app and waypoint logs)
            app_user_filter = ""
            waypoint_user_filter = ""
            if user_id:
                app_user_filter = f"AND al.user_id = {user_id}"
                waypoint_user_filter = f"AND fwl.user_id = {user_id}"
            
            # Build log type filter
            log_type_filter = ""
            if log_type:
                if log_type == "Portal":
                    log_type_filter = "AND log_source = 'portal_logs'"
                elif log_type == "App":
                    log_type_filter = "AND log_source = 'app_log'"
                elif log_type == "Waypoint":
                    log_type_filter = "AND log_source = 'fidoapi_waypoint_logs'"
            
            # Build the query dynamically based on available tables and log type filter
            union_parts = []
            
            # Always include Portal Logs (if not specifically filtered out)
            if not log_type or log_type == "Portal":
                portal_query = f'''
                SELECT 
                    CONCAT(pl.date, ' ', pl.time) as datetime,
                    pl.name as user_name,
                    pl.email as user_email,
                    pl.action,
                    pl.status,
                    pl.notes,
                    'portal_logs' as log_source,
                    c.company_name,
                    p.partner_name,
                    NULL as session_id,
                    NULL as waypoint_id,
                    NULL as waypoint_name,
                    pl.object_data,
                    JSON_OBJECT('company_id', pl.company_id, 'partner_id', pl.partner_id, 'branch_id', pl.branch_id) as metadata
                FROM fido1.portal_logs pl
                LEFT JOIN fido1.companies c ON pl.company_id = c.id
                LEFT JOIN fido1.partners p ON pl.partner_id = p.id
                WHERE 1=1 {portal_date_filter} {portal_company_filter} {portal_partner_filter}
                '''
                union_parts.append(portal_query)
            
            # Always include App Logs (if not specifically filtered out)
            if not log_type or log_type == "App":
                app_query = f'''
                SELECT 
                    al.timestamp as datetime,
                    CONCAT(u.first_name, ' ', u.last_name) as user_name,
                    u.email as user_email,
                    al.action,
                    al.status,
                    al.notes,
                    'app_log' as log_source,
                    c.company_name,
                    p.partner_name,
                    al.session_id,
                    al.waypoint_id,
                    NULL as waypoint_name,
                    NULL as object_data,
                    JSON_OBJECT('user_id', al.user_id, 'dma_id', al.dma_id) as metadata
                FROM fido1.app_log al
                LEFT JOIN fido1.users_portal u ON al.user_id = u.id
                LEFT JOIN fido1.companies c ON u.company_id = c.id
                LEFT JOIN fido1.partners p ON u.partner_id = p.id
                WHERE 1=1 {app_date_filter} {app_user_filter} {app_company_filter} {app_partner_filter}
                '''
                union_parts.append(app_query)
            
            # Try to include Waypoint Logs (if not specifically filtered out and table is accessible)
            if not log_type or log_type == "Waypoint":
                try:
                    # Test if waypoint table is accessible
                    test_cursor = connection.cursor()
                    test_cursor.execute("SELECT 1 FROM fido1.fidoapi_waypoint_logs LIMIT 1")
                    test_cursor.close()
                    
                    # If we get here, the table is accessible
                    waypoint_query = f'''
                    SELECT 
                        fwl.datetime,
                        fwl.user_name,
                        NULL as user_email,
                        fwl.changed_to_status_name as action,
                        'completed' as status,
                        CONCAT('Waypoint: ', fwl.waypoint_name) as notes,
                        'fidoapi_waypoint_logs' as log_source,
                        c.company_name,
                        p.partner_name,
                        NULL as session_id,
                        fwl.waypoint_id,
                        fwl.waypoint_name,
                        NULL as object_data,
                        JSON_OBJECT('user_id', fwl.user_id) as metadata
                    FROM fido1.fidoapi_waypoint_logs fwl
                    LEFT JOIN fido1.users_portal u ON fwl.user_id = u.id
                    LEFT JOIN fido1.companies c ON u.company_id = c.id
                    LEFT JOIN fido1.partners p ON u.partner_id = p.id
                    WHERE 1=1 {waypoint_date_filter} {waypoint_user_filter} {waypoint_company_filter} {waypoint_partner_filter}
                    '''
                    union_parts.append(waypoint_query)
                except Exception:
                    # Table not accessible, skip waypoint logs
                    pass
            
            if not union_parts:
                return pd.DataFrame()
            
            # Combine all accessible parts
            query = f'''
            SELECT 
                datetime as timestamp,
                user_name,
                user_email,
                action,
                status,
                notes,
                log_source,
                company_name,
                partner_name,
                session_id,
                waypoint_id,
                waypoint_name,
                object_data,
                metadata
            FROM (
                {' UNION ALL '.join(union_parts)}
            ) unified_logs
            WHERE 1=1 {log_type_filter}
            ORDER BY datetime DESC
            '''
            
            df = pd.read_sql(query, connection)
            return df
            
        except Exception as e:
            print(f"Error fetching unified logs: {e}")
            return pd.DataFrame()
        finally:
            if connection.is_connected():
                connection.close()

    def get_top_waypoints_today(self):
        """Get top 3 most active waypoints worked on today"""
        connection = self.get_connection()
        if not connection:
            return pd.DataFrame()
        
        try:
            # First check if the table is accessible
            test_cursor = connection.cursor()
            test_cursor.execute("SELECT 1 FROM fido1.fidoapi_waypoint_logs LIMIT 1")
            test_cursor.close()
            
            # If we get here, the table is accessible
            query = '''
            SELECT 
                waypoint_id, 
                waypoint_name, 
                COUNT(*) AS actions_today
            FROM fido1.fidoapi_waypoint_logs
            WHERE DATE(datetime) = CURRENT_DATE
            GROUP BY waypoint_id, waypoint_name
            ORDER BY actions_today DESC
            LIMIT 3
            '''
            
            df = pd.read_sql(query, connection)
            return df
            
        except Exception as e:
            # Table not accessible, return empty DataFrame
            return pd.DataFrame()
        finally:
            if connection.is_connected():
                connection.close()

    def get_top_sessions_today(self):
        """Get top 3 sessions with most activity today"""
        connection = self.get_connection()
        if not connection:
            return pd.DataFrame()
        
        try:
            query = '''
            SELECT 
                session_id, 
                COUNT(*) AS activity_count,
                MIN(timestamp) as first_activity,
                MAX(timestamp) as last_activity
            FROM fido1.app_log
            WHERE DATE(timestamp) = CURRENT_DATE
            AND session_id IS NOT NULL
            GROUP BY session_id
            ORDER BY activity_count DESC
            LIMIT 3
            '''
            
            df = pd.read_sql(query, connection)
            return df
            
        except Exception as e:
            print(f"Error fetching top sessions: {e}")
            return pd.DataFrame()
        finally:
            if connection.is_connected():
                connection.close()

    def get_log_filters(self):
        """Get available filter options for logs"""
        connection = self.get_connection()
        if not connection:
            return {
                'users': [],
                'companies': [],
                'partners': [],
                'log_types': ['Portal', 'App']
            }
        
        try:
            # Get unique users
            users_query = '''
            SELECT DISTINCT 
                u.id,
                CONCAT(u.first_name, ' ', u.last_name) as user_name,
                u.email
            FROM fido1.users_portal u
            WHERE u.active = 1
            ORDER BY user_name
            '''
            users_df = pd.read_sql(users_query, connection)
            users = [{'id': row['id'], 'name': row['user_name'], 'email': row['email']} 
                    for _, row in users_df.iterrows()]
            
            # Get companies
            companies_query = '''
            SELECT id, company_name 
            FROM fido1.companies 
            WHERE active = 1 
            ORDER BY company_name
            '''
            companies_df = pd.read_sql(companies_query, connection)
            companies = [{'id': row['id'], 'name': row['company_name']} 
                        for _, row in companies_df.iterrows()]
            
            # Get partners
            partners_query = '''
            SELECT id, partner_name 
            FROM fido1.partners 
            ORDER BY partner_name
            '''
            partners_df = pd.read_sql(partners_query, connection)
            partners = [{'id': row['id'], 'name': row['partner_name']} 
                       for _, row in partners_df.iterrows()]
            
            # Determine available log types based on table accessibility
            log_types = ['Portal', 'App']
            
            # Check if waypoint table is accessible
            try:
                test_cursor = connection.cursor()
                test_cursor.execute("SELECT 1 FROM fido1.fidoapi_waypoint_logs LIMIT 1")
                test_cursor.close()
                log_types.append('Waypoint')
            except Exception:
                # Waypoint table not accessible, skip it
                pass
            
            return {
                'users': users,
                'companies': companies,
                'partners': partners,
                'log_types': log_types
            }
            
        except Exception as e:
            print(f"Error fetching log filters: {e}")
            return {
                'users': [],
                'companies': [],
                'partners': [],
                'log_types': ['Portal', 'App']
            }
        finally:
            if connection.is_connected():
                connection.close()

# Example usage for when you're ready to switch from mock data:
"""
# In your app.py, replace the generate_mock_data() function with:

from database import DatabaseConnection

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_license_data():
    db = DatabaseConnection()
    df = db.fetch_license_data()
    return df if df is not None else pd.DataFrame()
""" 