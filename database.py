import mysql.connector
import pandas as pd
import os
from dotenv import load_dotenv
import datetime
from sqlalchemy.orm import sessionmaker
from models import engine, LicenseRecord, Company, Partner, LicenseProductCode, UserPortal, LoggerSession

# Load environment variables
load_dotenv()

# Create a new session
Session = sessionmaker(bind=engine)

class DatabaseConnection:
    """Database connection handler for MySQL"""
    
    def __init__(self):
        self.host = os.getenv('DB_HOST', 'localhost')
        self.user = os.getenv('DB_USER', 'your_username')
        self.password = os.getenv('DB_PASSWORD', 'your_password')
        self.database = os.getenv('DB_NAME', 'license_db')
        self.port = int(os.getenv('DB_PORT', '3306'))
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
            query = self.session.query(LicenseRecord, Company.company_name.label('company_name'))
            query = query.join(Company, LicenseRecord.company_id == Company.id)
            if start_date:
                query = query.filter(LicenseRecord.start_date >= start_date)
            if end_date:
                query = query.filter(LicenseRecord.start_date <= end_date)
            licenses = query.all()
            # Convert list of tuples to DataFrame
            df = pd.DataFrame([{**license.__dict__, 'company': company_name} for license, company_name in licenses])
            # Drop SQLAlchemy state column
            df = df.drop('_sa_instance_state', axis=1, errors='ignore')
            return df
        except Exception as e:
            print(f"Error fetching data: {e}")
            return None
            
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
        """Get list of active companies for dropdowns"""
        connection = self.get_connection()
        if not connection:
            return []
            
        try:
            query = """
            SELECT id, company_name 
            FROM fido1.companies 
            WHERE active = 1 
            ORDER BY company_name
            """
            
            cursor = connection.cursor()
            cursor.execute(query)
            companies = [{'id': row[0], 'company_name': row[1]} for row in cursor.fetchall()]
            return companies
            
        except Exception as e:
            print(f"Error fetching companies: {e}")
            return []
            
        finally:
            cursor.close()
            connection.close()
    
    def get_active_partners(self):
        """Get list of active partners for dropdowns"""
        connection = self.get_connection()
        if not connection:
            return []
            
        try:
            query = """
            SELECT id, partner_name 
            FROM fido1.partners 
            WHERE active = 1 
            ORDER BY partner_name
            """
            
            cursor = connection.cursor()
            cursor.execute(query)
            partners = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]
            return partners
            
        except Exception as e:
            print(f"Error fetching partners: {e}")
            return []
            
        finally:
            cursor.close()
            connection.close()
    
    def get_product_codes(self):
        """Get list of available product codes for dropdowns"""
        connection = self.get_connection()
        if not connection:
            return []
            
        try:
            query = """
            SELECT id, code, label 
            FROM fido1.license_product_codes 
            ORDER BY code
            """
            
            cursor = connection.cursor()
            cursor.execute(query)
            product_codes = [{'id': row[0], 'code': row[1], 'label': row[2]} for row in cursor.fetchall()]
            return product_codes
            
        except Exception as e:
            print(f"Error fetching product codes: {e}")
            return []
            
        finally:
            cursor.close()
            connection.close()
    
    def get_product_code_by_code(self, code):
        """Get product code ID by code string (e.g., 'SUB' -> id)"""
        connection = self.get_connection()
        if not connection:
            return None
            
        try:
            query = """
            SELECT id, code, label 
            FROM fido1.license_product_codes 
            WHERE code = %s
            """
            
            cursor = connection.cursor()
            cursor.execute(query, (code,))
            result = cursor.fetchone()
            
            if result:
                return {'id': result[0], 'code': result[1], 'label': result[2]}
            return None
            
        except Exception as e:
            print(f"Error fetching product code: {e}")
            return None
            
        finally:
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
        """Fetch active users per company based on the last 14 days of activity"""
        connection = self.get_connection()
        if not connection:
            return pd.DataFrame()
        
        try:
            query = '''
            SELECT 
              c.company_name,
              lr.number_of_licenses,
              COUNT(DISTINCT u.id) AS active_users,
              ROUND(COUNT(DISTINCT u.id) / lr.number_of_licenses, 2) AS utilization_ratio
            FROM fido1.license_records lr
            JOIN fido1.companies c ON lr.company_id = c.id
            LEFT JOIN fido1.users_portal u ON u.company_id = c.id
            INNER JOIN (
                SELECT DISTINCT deployed_by AS user_id
                FROM fido1.logger_sessions
                WHERE created >= CURDATE() - INTERVAL 14 DAY
                AND deployed_by IS NOT NULL

                UNION

                SELECT DISTINCT collected_by AS user_id
                FROM fido1.logger_sessions
                WHERE last_update >= CURDATE() - INTERVAL 14 DAY
                AND collected_by IS NOT NULL
            ) recent_activity ON recent_activity.user_id = u.id
            WHERE lr.company_id IS NOT NULL
            GROUP BY lr.id, c.company_name, lr.number_of_licenses;
            '''
            
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query)
            results = cursor.fetchall()
            df = pd.DataFrame(results)
            return df
        except Exception as e:
            print(f"Error fetching active users per company: {e}")
            return pd.DataFrame()
        finally:
            cursor.close()
            connection.close()

    def get_user_count_from_portal(self):
        """Fetch user count per company from the users_portal table"""
        connection = self.get_connection()
        if not connection:
            return pd.DataFrame()
        
        try:
            query = '''
            SELECT 
              c.company_name,
              COUNT(u.id) AS user_count
            FROM fido1.users_portal u
            JOIN fido1.companies c ON u.company_id = c.id
            GROUP BY c.company_name;
            '''
            
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query)
            results = cursor.fetchall()
            df = pd.DataFrame(results)
            return df
        except Exception as e:
            print(f"Error fetching user count from portal: {e}")
            return pd.DataFrame()
        finally:
            cursor.close()
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