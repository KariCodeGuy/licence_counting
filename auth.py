import streamlit as st
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class AuthManager:
    """Simple authentication manager for License Dashboard"""
    
    def __init__(self):
        self.session_timeout = 8 * 60 * 60  # 8 hours in seconds
    
    def authenticate_user(self, username, password):
        """Simple authentication against .env file credentials"""
        # Get credentials from environment variables
        admin_user = os.getenv('ADMIN_USERNAME', 'admin')
        admin_pass = os.getenv('ADMIN_PASSWORD', 'admin123')
        viewer_user = os.getenv('VIEWER_USERNAME', 'viewer')
        viewer_pass = os.getenv('VIEWER_PASSWORD', 'viewer123')
        
        # Debug mode removed for security
        
        # Check admin credentials
        if username == admin_user and password == admin_pass:
            return {
                'username': username,
                'role': 'admin',
                'display_name': 'Administrator',
                'permissions': ['view', 'edit', 'delete', 'export'],
                'login_time': datetime.now()
            }
        
        # Check viewer credentials
        elif username == viewer_user and password == viewer_pass:
            return {
                'username': username,
                'role': 'viewer',
                'display_name': 'Viewer',
                'permissions': ['view', 'export'],
                'login_time': datetime.now()
            }
        
        return None
    
    def check_session(self):
        """Check if user session is valid"""
        if 'authenticated' not in st.session_state:
            return False
            
        if not st.session_state.authenticated:
            return False
            
        # Check session timeout
        login_time = st.session_state.get('login_time')
        if login_time:
            elapsed = (datetime.now() - login_time).total_seconds()
            if elapsed > self.session_timeout:
                self.logout()
                return False
                
        return True
    
    def login(self, user_data):
        """Set user session"""
        st.session_state.authenticated = True
        st.session_state.user = user_data
        st.session_state.login_time = user_data['login_time']
        
    def logout(self):
        """Clear user session"""
        for key in ['authenticated', 'user', 'login_time']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
    
    def get_current_user(self):
        """Get current authenticated user"""
        return st.session_state.get('user', None)
    
    def require_auth(self):
        """Decorator-like function to require authentication"""
        if not self.check_session():
            self.show_login_page()
            st.stop()
    
    def show_login_page(self):
        """Display login form"""
        st.set_page_config(
            page_title="License Dashboard - Login",
            page_icon="🔐",
            layout="centered"
        )
        
        # Center the login form
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.title("🔐 License Management Dashboard")
            st.markdown("---")
            
            st.info("**Login Required** - Enter your credentials to access the dashboard")
            
            with st.form("login_form"):
                username = st.text_input("Username", key="login_username")
                password = st.text_input("Password", type="password", key="login_password")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.form_submit_button("🔑 Login", type="primary", use_container_width=True):
                        if username and password:
                            user = self.authenticate_user(username, password)
                            if user:
                                self.login(user)
                                st.success("✅ Login successful!")
                                st.rerun()
                            else:
                                st.error("❌ Invalid credentials")
                        else:
                            st.error("❌ Please enter both username and password")
                
                with col2:
                    if st.form_submit_button("ℹ️ Help", use_container_width=True):
                        st.info("""
                        **Access Levels:**
                        - **Admin**: Full access (view, edit, delete, export)
                        - **Viewer**: Read-only access (view, export)
                        - Contact system admin for credentials
                        """)
            
            st.markdown("---")
            st.caption("🔒 Secure access to licensed software metrics")
            
            with st.expander("🛡️ Security Notes"):
                st.markdown("""
                **Current Security Level: Internal Use**
                - Passwords stored in .env file (keep secure, don't commit to git)
                - Use HTTPS in production deployment
                - 8-hour session timeout
                - For enhanced security, consider integrating with your existing SSO/LDAP
                """)


# Global auth manager instance
auth_manager = AuthManager()

# Simple two-account authentication system 