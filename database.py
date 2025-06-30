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
        """Fetch active users per company or partner based on the last 14 days of activity"""
        connection = self.get_connection()
        if not connection:
            return pd.DataFrame()
        
        try:
            # Get active users for company and partner licenses
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
        """Fetch active relay devices by company and partner based on 14-day activity"""
        connection = self.get_connection()
        if not connection:
            return pd.DataFrame()
        
        try:
            # Build role-based filtering
            role_filter = ""
            if user_role == "Company User" and user_company_id:
                role_filter = f"AND u.company_id = {user_company_id}"
            elif user_role == "Partner Admin" and user_partner_id:
                role_filter = f"AND u.partner_id = {user_partner_id}"
            # Admin role sees all data, so no additional filter needed
            
            # Query for company-based relay devices
            company_query = f'''
            SELECT 
                u.company_id,
                c.company_name as entity_name,
                'Company' as entity_type,
                COUNT(DISTINCT ram.relay_id) AS active_relay_devices
            FROM fido1.relay_activity_monitor ram
            JOIN fido1.logger_sessions ls ON ram.session_id = ls.session_id
            JOIN fido1.users_portal u ON ls.deployed_by = u.id
            JOIN fido1.companies c ON u.company_id = c.id
            WHERE ram.create_time >= CURDATE() - INTERVAL 14 DAY
            {role_filter}
            GROUP BY u.company_id, c.company_name
            '''
            
            # Query for partner-based relay devices
            partner_query = f'''
            SELECT 
                u.partner_id,
                p.partner_name as entity_name,
                'Partner' as entity_type,
                COUNT(DISTINCT ram.relay_id) AS active_relay_devices
            FROM fido1.relay_activity_monitor ram
            JOIN fido1.logger_sessions ls ON ram.session_id = ls.session_id
            JOIN fido1.users_portal u ON ls.deployed_by = u.id
            JOIN fido1.partners p ON u.partner_id = p.id
            WHERE ram.create_time >= CURDATE() - INTERVAL 14 DAY
            {role_filter}
            GROUP BY u.partner_id, p.partner_name
            '''
            
            # Execute both queries and combine results
            company_df = pd.read_sql(company_query, connection)
            partner_df = pd.read_sql(partner_query, connection)
            
            # Combine results
            combined_df = pd.concat([company_df, partner_df], ignore_index=True)
            return combined_df
            
        except Exception as e:
            print(f"Error fetching active relay devices: {e}")
            return pd.DataFrame()
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