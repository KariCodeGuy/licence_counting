import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
from auth import auth_manager
from database import DatabaseConnection

# Require authentication before showing dashboard
auth_manager.require_auth()

# Page configuration
st.set_page_config(
    page_title="License Management Dashboard",
    page_icon="��",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin-bottom: 1rem;
    }
    .action-button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 5px;
        cursor: pointer;
    }
    .sidebar-section {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    .status-active {
        color: #28a745;
        font-weight: bold;
    }
    .status-expired {
        color: #dc3545;
        font-weight: bold;
    }
    .utilization-high {
        color: #28a745;
    }
    .utilization-medium {
        color: #ffc107;
    }
    .utilization-low {
        color: #dc3545;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state first
if 'show_add_form' not in st.session_state:
    st.session_state.show_add_form = False
if 'show_import' not in st.session_state:
    st.session_state.show_import = False
if 'show_delete_confirm' not in st.session_state:
    st.session_state.show_delete_confirm = False
if 'delete_license_id' not in st.session_state:
    st.session_state.delete_license_id = None
if 'df_data' not in st.session_state:
    st.session_state.df_data = None
if 'selected_dashboard' not in st.session_state:
    st.session_state.selected_dashboard = 'All Licenses'
if 'show_logs_dashboard' not in st.session_state:
    st.session_state.show_logs_dashboard = False

# --- Modal dialog for deleting licences ---
@st.dialog("🗑️ Delete Licence")
def delete_licence_dialog():
    st.subheader("🗑️ Delete Licence")
    if not display_df.empty:
        delete_options = []
        for idx, row in display_df.iterrows():
            entity_name = row.get('entity', 'Unknown')
            entity_type = row.get('entity_type', 'Unknown')
            product = row.get('product_label', 'Unknown')
            licences = row.get('number_of_licenses', 0)
            delete_options.append(f"{entity_name} ({entity_type}) - {product} - {licences} licences")
        selected_delete = st.selectbox(
            "Select licence to delete:",
            options=delete_options,
            key="delete_selector_modal",
            help="Choose the licence you want to delete"
        )
        if selected_delete:
            selected_index = delete_options.index(selected_delete)
            selected_row = display_df.iloc[selected_index]
            licence_id = selected_row.get('id')
            entity_name = selected_row.get('entity', 'Unknown')
            st.warning(f"⚠️ You are about to delete licence for **{entity_name}**")
            st.info(f"**Details:** {selected_row.get('product_label', 'Unknown')} - {selected_row.get('number_of_licenses', 0)} licences")
            col_confirm, col_cancel = st.columns(2)
            with col_confirm:
                if st.button("🗑️ Confirm Delete", type="primary", key="confirm_delete_modal"):
                    db = DatabaseConnection()
                    if db.delete_license(licence_id):
                        st.success(f"✅ Licence for {entity_name} deleted successfully!")
                        load_license_data.clear()
                        st.session_state.df_data = None
                        st.session_state.original_df = None
                        st.session_state.show_delete_modal = False
                        st.rerun()
                    else:
                        st.error("❌ Failed to delete licence. Please try again.")
            with col_cancel:
                if st.button("❌ Cancel", type="secondary", key="cancel_delete_modal"):
                    st.session_state.show_delete_modal = False
                    st.rerun()
    else:
        st.info("No licences available to delete.")

# Add License Dialog
@st.dialog("➕ Add New License")
def add_license_dialog():
    st.write("Fill in the details for the new license:")
    
    # Add helpful information about multiple license rounds
    with st.expander("ℹ️ **How Multiple License Rounds Work**", expanded=False):
        st.markdown("""
        **Multiple License Rounds**: You can add multiple license records for the same company/partner with different date ranges.
        
        **Examples:**
        - **Round 1**: 50 User licenses (Jan 2024 - Dec 2024)
        - **Round 2**: 25 User licenses (Mar 2024 - Feb 2025) 
        - **Round 3**: 10 Relay licenses (Jun 2024 - May 2025)
        
        **Benefits:**
        ✅ Different start/end dates for each round  
        ✅ Different license counts per round  
        ✅ Different product types per round  
        ✅ Automatic aggregation in dashboards  
        ✅ Individual tracking and management  
        
        **Use the 'Quick Add Another License Round' section below for faster workflow!**
        """)
    
    # Load companies, partners, and product codes from database
    db = DatabaseConnection()
    companies = db.get_active_companies()
    partners = db.get_active_partners()
    product_code_options = db.get_product_codes()
    
    # Combine companies and partners into unified list with type indicators
    entity_options = []
    for company in companies:
        entity_options.append({
            'id': company['id'], 
            'name': company['company_name'], 
            'type': 'company'
        })
    for partner in partners:
        entity_options.append({
            'id': partner['id'], 
            'name': partner['name'], 
            'type': 'partner'
        })
    
    # Sort by name for better UX
    entity_options.sort(key=lambda x: x['name'])
    
    with st.form("add_license_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            if entity_options:
                # Create unified display options with type indicators
                entity_display_options = []
                for entity in entity_options:
                    if entity['type'] == 'company':
                        entity_display_options.append(f"🏢 {entity['name']}")
                    else:  # partner
                        entity_display_options.append(f"🤝 {entity['name']}")
                
                selected_entity_display = st.selectbox(
                    "Company/Partner*", 
                    entity_display_options, 
                    key="new_entity",
                    help="Select either a company or partner for this license"
                )
                
                # Find the selected entity
                selected_entity_index = entity_display_options.index(selected_entity_display)
                selected_entity = entity_options[selected_entity_index]
                
                if selected_entity['type'] == 'company':
                    new_company_id = selected_entity['id']
                    new_partner_id = None
                    new_company = selected_entity['name']
                    new_partner = None
                    entity_name = new_company
                else:  # partner
                    # For partners, only set partner_id, leave company_id as None
                    new_company_id = None
                    new_partner_id = selected_entity['id']
                    new_company = None
                    new_partner = selected_entity['name']
                    entity_name = f"{new_partner} (Partner)"
            else:
                st.error("⚠️ No companies or partners found in database. Please contact admin to add entities.")
                st.stop()
                
            new_start_date = st.date_input("Start Date*", value=datetime.now().date(), key="new_start_date")
            new_licenses = st.number_input("Number of Licences*", min_value=1, value=10, key="new_licenses")
            
            # Currency selection
            currency_options = ["GBP", "USD", "EUR", "CAD", "AUD", "JPY", "CHF", "SEK", "NOK", "DKK"]
            new_currency = st.selectbox("Currency*", currency_options, key="new_currency")
            
            new_cost = st.number_input(f"Cost per Licence (per year)*", min_value=0.01, value=540.0, step=1.0, format="%.2f", key="new_cost")
        
        with col2:
            new_end_date = st.date_input("End Date*", value=datetime.now().date() + timedelta(days=365), key="new_end_date")
            
            # Product code selection from database
            if product_code_options:
                product_display_options = [f"{pc['code']} - {pc['label']}" for pc in product_code_options]
                
                # Find Subscription index for default selection
                default_index = 0
                for i, pc in enumerate(product_code_options):
                    if pc['code'] == 'SUB' or 'subscription' in pc['label'].lower():
                        default_index = i
                        break
                
                selected_product_display = st.selectbox(
                    "Product Code*", 
                    product_display_options, 
                    index=default_index,
                    key="new_product_code",
                    help="Select the type of license product"
                )
                
                # Find the selected product code
                selected_product_index = product_display_options.index(selected_product_display)
                selected_product = product_code_options[selected_product_index]
                
                new_product_code_id = selected_product['id']
                new_product_code = selected_product['code']
                new_product_label = selected_product['label']
            else:
                st.error("⚠️ No product codes found in database. Please contact admin to add product codes.")
                st.stop()
            
            new_status = st.selectbox("Status", ["Active", "Expired"], key="new_status")
            
            st.info("ℹ️ **User Counts** (Total & Active) are calculated automatically from the company's user records and system activity")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.form_submit_button("💾 Save License", type="primary", use_container_width=True):
                if entity_name and new_start_date and new_end_date and new_licenses > 0 and new_cost > 0 and new_product_code_id and new_currency:
                    if new_end_date >= new_start_date:
                        total_cost = new_licenses * new_cost
                        
                        # Save to database
                        license_data = {
                            'company_id': new_company_id,
                            'partner_id': new_partner_id,
                            'product_code_id': new_product_code_id,
                            'start_date': new_start_date,
                            'end_date': new_end_date,
                            'number_of_licenses': int(new_licenses),
                            'cost_per_license': new_cost,
                            'total_cost': total_cost,
                            'currency': new_currency,
                            'status': new_status
                        }
                        
                        if db.insert_license(license_data):
                            st.success(f"✅ License for {entity_name} saved to database!")
                            # Clear cache and refresh data from database
                            load_license_data.clear()
                            st.session_state.df_data = None
                            st.session_state.show_add_form = False
                            st.rerun()
                        else:
                            st.error("❌ Failed to save license to database")
                    else:
                        st.error("❌ End date must be after start date!")
                else:
                    st.error("❌ Please fill in all required fields!")
        
        with col2:
            if st.form_submit_button("❌ Cancel", use_container_width=True):
                st.session_state.show_add_form = False
                st.rerun()

    # Add Quick Add Another section after the form
    st.markdown("---")
    st.subheader("🔄 Quick Add Another License Round")
    st.info("💡 **Tip**: Use this to quickly add another license round for the same entity with different dates")
    
    with st.form("quick_add_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Pre-select the same entity if available
            if entity_options:
                entity_display_options = [f"🏢 {entity['name']}" if entity['type'] == 'company' else f"🤝 {entity['name']}" for entity in entity_options]
                quick_entity = st.selectbox(
                    "Entity",
                    entity_display_options,
                    index=entity_display_options.index(selected_entity_display) if 'selected_entity_display' in locals() else 0,
                    key="quick_entity"
                )
                
                # Find the selected entity
                quick_entity_index = entity_display_options.index(quick_entity)
                quick_entity_obj = entity_options[quick_entity_index]
                
                if quick_entity_obj['type'] == 'company':
                    quick_company_id = quick_entity_obj['id']
                    quick_partner_id = None
                else:
                    quick_company_id = None
                    quick_partner_id = quick_entity_obj['id']
            else:
                st.error("No entities available")
                st.stop()
        
        with col2:
            # Pre-select the same product code if available
            if product_code_options:
                product_display_options = [f"{pc['code']} - {pc['label']}" for pc in product_code_options]
                quick_product = st.selectbox(
                    "Product Code",
                    product_display_options,
                    index=product_display_options.index(selected_product_display) if 'selected_product_display' in locals() else 0,
                    key="quick_product"
                )
                
                # Find the selected product code
                quick_product_index = product_display_options.index(quick_product)
                quick_product_obj = product_code_options[quick_product_index]
                quick_product_code_id = quick_product_obj['id']
            else:
                st.error("No product codes available")
                st.stop()
        
        with col3:
            # Pre-select the same currency if available
            currency_options = ["GBP", "USD", "EUR", "CAD", "AUD", "JPY", "CHF", "SEK", "NOK", "DKK"]
            quick_currency = st.selectbox(
                "Currency",
                currency_options,
                index=currency_options.index(new_currency) if 'new_currency' in locals() else 0,
                key="quick_currency"
            )
        
        # Second row for dates and license details
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            quick_start_date = st.date_input("Start Date", value=datetime.now().date(), key="quick_start_date")
        
        with col2:
            quick_end_date = st.date_input("End Date", value=datetime.now().date() + timedelta(days=365), key="quick_end_date")
        
        with col3:
            quick_licenses = st.number_input("Number of Licenses", min_value=1, value=10, key="quick_licenses")
        
        with col4:
            quick_cost = st.number_input("Cost per License", min_value=0.01, value=540.0, step=1.0, format="%.2f", key="quick_cost")
        
        # Submit button for quick add
        if st.form_submit_button("🚀 Quick Add License Round", type="secondary", use_container_width=True):
            if quick_start_date and quick_end_date and quick_licenses > 0 and quick_cost > 0:
                if quick_end_date >= quick_start_date:
                    quick_total_cost = quick_licenses * quick_cost
                    
                    # Save to database
                    quick_license_data = {
                        'company_id': quick_company_id,
                        'partner_id': quick_partner_id,
                        'product_code_id': quick_product_code_id,
                        'start_date': quick_start_date,
                        'end_date': quick_end_date,
                        'number_of_licenses': int(quick_licenses),
                        'cost_per_license': quick_cost,
                        'total_cost': quick_total_cost,
                        'currency': quick_currency,
                        'status': 'Active'
                    }
                    
                    if db.insert_license(quick_license_data):
                        st.success(f"✅ Quick license round added successfully!")
                        # Clear cache and refresh data from database
                        load_license_data.clear()
                        st.session_state.df_data = None
                        st.rerun()
                    else:
                        st.error("❌ Failed to save quick license to database")
                else:
                    st.error("❌ End date must be after start date!")
            else:
                st.error("❌ Please fill in all required fields!")

# Bulk Import Dialog  
@st.dialog("📥 Bulk Import Licences")
def bulk_import_dialog():
    st.info("Upload a CSV file with columns: company, start_date, end_date, number_of_licenses, cost_per_license, product_code, currency, status")
    st.info("💡 **Product Code**: Use 3-character codes like 'SUB', 'REL', 'ADM', 'ENT' etc. Must match existing product codes in database.")
    st.info("💰 **Currency**: Use 3-character ISO codes like 'USD', 'EUR', 'GBP', etc. Defaults to 'USD' if not specified.")
    
    uploaded_file = st.file_uploader("Choose CSV file", type="csv")
    
    if uploaded_file is not None:
        try:
            import_df = pd.read_csv(uploaded_file)
            
            # Validate required columns
            required_cols = ['company', 'start_date', 'end_date', 'number_of_licenses', 'cost_per_license']
            missing_cols = [col for col in required_cols if col not in import_df.columns]
            
            if missing_cols:
                st.error(f"❌ Missing required columns: {', '.join(missing_cols)}")
            else:
                st.success(f"✅ File uploaded successfully! Found {len(import_df)} records.")
                st.dataframe(import_df.head(), use_container_width=True)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("💾 Import Data", type="primary", use_container_width=True):
                        # Process each row and insert into database
                        db = DatabaseConnection()
                        success_count = 0
                        error_count = 0
                        
                        for _, row in import_df.iterrows():
                            try:
                                # Look up product code ID
                                product_code = row.get('product_code', 'SUB')
                                product_info = db.get_product_code_by_code(product_code)
                                if not product_info:
                                    st.error(f"❌ Unknown product code: {product_code}")
                                    error_count += 1
                                    continue
                                
                                # For now, assume all imports are for companies (not partners)
                                # You could extend this to look up company names
                                license_data = {
                                    'company_id': 1,  # This would need proper company lookup
                                    'partner_id': None,
                                    'product_code_id': product_info['id'],
                                    'start_date': pd.to_datetime(row['start_date']).date(),
                                    'end_date': pd.to_datetime(row['end_date']).date(),
                                    'number_of_licenses': int(row['number_of_licenses']),
                                    'cost_per_license': float(row['cost_per_license']),
                                    'total_cost': int(row['number_of_licenses']) * float(row['cost_per_license']),
                                    'currency': row.get('currency', 'USD'),
                                    'status': row.get('status', 'Active')
                                }
                                
                                if db.insert_license(license_data):
                                    success_count += 1
                                else:
                                    error_count += 1
                                    
                            except Exception as e:
                                st.error(f"❌ Error processing row: {str(e)}")
                                error_count += 1
                        
                        # Clear cache and refresh
                        load_license_data.clear()
                        st.session_state.df_data = None
                        
                        if success_count > 0:
                            st.success(f"✅ Successfully imported {success_count} licences!")
                        if error_count > 0:
                            st.warning(f"⚠️ {error_count} records failed to import")
                            
                        st.session_state.show_import = False
                        st.rerun()
                
                with col2:
                    if st.button("❌ Cancel Import", use_container_width=True):
                        st.session_state.show_import = False
                        st.rerun()
                        
        except Exception as e:
            st.error(f"❌ Error reading file: {str(e)}")

# Delete Confirmation Dialog
@st.dialog("🗑️ Delete License")
def delete_confirmation_dialog():
    license_id = st.session_state.delete_license_id
    
    # Get license details for confirmation
    if not filtered_df.empty and license_id:
        license_row = filtered_df[filtered_df['id'] == license_id]
        if not license_row.empty:
            license_info = license_row.iloc[0]
            
            st.error("⚠️ **WARNING: This action cannot be undone!**")
            st.write("You are about to delete the following license:")
            
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Company:** {license_info.get('company', 'N/A')}")
                st.write(f"**Partner:** {license_info.get('partner', 'N/A') or 'None'}")
                st.write(f"**Product:** {license_info.get('product_label', 'N/A')}")
            with col2:
                st.write(f"**Licences:** {license_info.get('number_of_licenses', 'N/A')}")
                st.write(f"**Start Date:** {license_info.get('start_date', 'N/A')}")
                st.write(f"**End Date:** {license_info.get('end_date', 'N/A')}")
            
            st.markdown("---")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🗑️ Yes, Delete", type="primary", use_container_width=True):
                    db = DatabaseConnection()
                    if db.delete_license(license_id):
                        st.success("✅ License deleted successfully!")
                        # Clear cache and refresh
                        load_license_data.clear()
                        st.session_state.df_data = None
                        st.session_state.show_delete_confirm = False
                        st.session_state.delete_license_id = None
                        st.rerun()
                    else:
                        st.error("❌ Failed to delete license")
            
            with col2:
                if st.button("❌ Cancel", use_container_width=True):
                    st.session_state.show_delete_confirm = False
                    st.session_state.delete_license_id = None
                    st.rerun()
        else:
            st.error("License not found")
            st.session_state.show_delete_confirm = False
            st.session_state.delete_license_id = None

# Load data function
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_license_data():
    db = DatabaseConnection()
    # Use default date range for initial load
    default_start = datetime.now().date() - timedelta(days=365)
    default_end = datetime.now().date()
    df = db.fetch_license_data(start_date=default_start, end_date=default_end)
    return df if df is not None else pd.DataFrame()

# Load data
if st.session_state.df_data is None:
    st.session_state.df_data = load_license_data()
df = st.session_state.df_data

# Check if DataFrame is empty
if df is None or df.empty:
    st.warning("⚠️ No license data available. Add some licences to get started!")
    df = pd.DataFrame(columns=['id', 'company', 'company_id', 'partner', 'partner_id', 'product_code', 'product_label', 'start_date', 'end_date', 
                              'number_of_licenses', 'user_count', 'active_users', 'cost_per_license', 'total_cost', 'currency', 'status'])
else:
    st.write("DataFrame loaded.")  # Placeholder to fix indentation error

# Main header with gradient background
st.markdown(f"""
<div class="main-header">
    <h1 style="margin: 0; font-size: 2.5rem;">📊 {st.session_state.selected_dashboard} Dashboard</h1>
    <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">License Management & Analytics Platform</p>
</div>
""", unsafe_allow_html=True)

# Sidebar - Redesigned for better UX
with st.sidebar:
    # User info at the top
    current_user = auth_manager.get_current_user()
    if current_user:
        st.markdown("""
        <div class="sidebar-section">
            <h4>👤 User Info</h4>
        </div>
        """, unsafe_allow_html=True)
        st.write(f"**{current_user['display_name']}**")
        st.write(f"🔐 {current_user['role'].title()} Access")
        
        if st.button("🚪 Logout", use_container_width=True, key="logout"):
            auth_manager.logout()
    
    st.markdown("---")
    
    # Quick Actions Section
    st.markdown("""
    <div class="sidebar-section">
        <h4>⚡ Quick Actions</h4>
    </div>
    """, unsafe_allow_html=True)
    
    can_edit = current_user and 'edit' in current_user.get('permissions', [])
    
    if can_edit:
        if st.button("➕ Add License", type="primary", use_container_width=True, key="sidebar_add_license"):
            st.session_state.show_add_form = True
        
        if st.button("📥 Import CSV", use_container_width=True, key="sidebar_import_csv"):
            st.session_state.show_import = True
    else:
        st.button("➕ Add License", disabled=True, help="Admin access required", use_container_width=True, key="sidebar_add_license_disabled")
        st.button("📥 Import CSV", disabled=True, help="Admin access required", use_container_width=True, key="sidebar_import_csv_disabled")
    
    if st.button("🔄 Refresh Data", use_container_width=True, key="sidebar_refresh_data"):
        load_license_data.clear()
        st.session_state.df_data = None
        st.success("✅ Data refreshed!")
        st.rerun()
    
    st.markdown("---")
    
    # Dashboard Selector
    st.markdown("""
    <div class="sidebar-section">
        <h4>📊 Dashboard Type</h4>
    </div>
    """, unsafe_allow_html=True)
    
    dashboard_options = ['All Licenses', 'Relay Licenses', 'User Licenses', 'System Logs']
    st.write('DEBUG: dashboard_options =', dashboard_options)
    selected_dashboard = st.selectbox(
        "Select Dashboard",
        options=dashboard_options,
        index=dashboard_options.index(st.session_state.selected_dashboard),
        key="dashboard_selector",
        help="Choose which type of licenses to view"
    )
    
    # Update session state when dashboard changes
    if selected_dashboard != st.session_state.selected_dashboard:
        st.session_state.selected_dashboard = selected_dashboard
        st.rerun()
    
    st.markdown("---")
    
    # Filters Section
    st.markdown("""
    <div class="sidebar-section">
        <h4>🔍 Filters</h4>
    </div>
    """, unsafe_allow_html=True)
    
    if not df.empty:
        # Date range filter
        default_start = datetime.now().date() - timedelta(days=365)
        default_end = datetime.now().date()
        
        date_range = st.date_input(
            "📅 Date Range",
            value=(default_start, default_end),
            help="Filter licenses by start date range"
        )
        
        # Entity filter
        if 'entity' not in df.columns:
            df['entity'] = df.apply(lambda row: 
                row.get('partner', '') if pd.notna(row.get('partner')) and row.get('partner') 
                else row.get('company', ''), axis=1)
        
        entity_options = sorted(df['entity'].dropna().unique()) if not df.empty else []
        companies = st.multiselect(
            "🏢 Companies/Partners",
            options=entity_options,
            default=entity_options,
            help="Filter by companies or partners"
        )
        
        # Status filter
        status_options = df['status'].unique().tolist() if not df.empty else ['Active', 'Expired']
        status_filter = st.multiselect(
            "📊 Status",
            options=status_options,
            default=status_options,
            help="Filter by license status"
        )
        
        # Currency filter
        if not df.empty and 'currency' in df.columns:
            currency_options = sorted(df['currency'].dropna().unique())
            currency_filter = st.multiselect(
                "💰 Currency",
                options=currency_options,
                default=currency_options,
                help="Filter by currency"
            )
        else:
            currency_filter = []
        
        # Product code filter
        if not df.empty and 'product_code' in df.columns:
            product_options = sorted(df['product_code'].dropna().unique())
            product_filter = st.multiselect(
                "🏷️ Product Code",
                options=product_options,
                default=product_options,
                help="Filter by specific product codes"
            )
        else:
            product_filter = []
    
    # Database status
    st.markdown("---")
    st.success("🗄️ Live Database Connected")

# Convert DataFrame dates to proper format for filtering (only if not empty)
if not df.empty:
    df['start_date'] = pd.to_datetime(df['start_date']).dt.date
    df['end_date'] = pd.to_datetime(df['end_date']).dt.date

# Apply filters
if df.empty:
    filtered_df = df.copy()
elif len(date_range) == 2:
    # Create entity column for filtering if it doesn't exist
    if 'entity' not in df.columns:
        df['entity'] = df.apply(lambda row: 
            row.get('partner', '') if pd.notna(row.get('partner')) and row.get('partner') 
            else row.get('company', ''), axis=1)
    
    # Auto-filter by product code based on dashboard selection
    if st.session_state.selected_dashboard == 'Relay Licenses':
        # Filter for Relay licenses (assuming 'REL' is the product code for Relay)
        dashboard_product_filter = ['REL'] if 'product_code' in df.columns else []
    elif st.session_state.selected_dashboard == 'User Licenses':
        # Filter for User licenses (assuming 'SUB' or other codes are for User licenses)
        dashboard_product_filter = ['SUB', 'USR', 'USR_LIC'] if 'product_code' in df.columns else []
    else:
        # All Licenses - no product code filtering
        dashboard_product_filter = []
    
    # Apply dashboard-specific product filtering
    if dashboard_product_filter and 'product_code' in df.columns:
        df_filtered_by_dashboard = df[df['product_code'].isin(dashboard_product_filter)]
    else:
        df_filtered_by_dashboard = df
    
    base_filter = (
        (df_filtered_by_dashboard['start_date'] >= date_range[0]) & 
        (df_filtered_by_dashboard['start_date'] <= date_range[1]) &
        (df_filtered_by_dashboard['entity'].isin(companies)) &
        (df_filtered_by_dashboard['status'].isin(status_filter))
    )
    # Add currency filter if available
    if currency_filter and 'currency' in df_filtered_by_dashboard.columns:
        base_filter = base_filter & (df_filtered_by_dashboard['currency'].isin(currency_filter))
    # Add product code filter if available
    if product_filter and 'product_code' in df_filtered_by_dashboard.columns:
        base_filter = base_filter & (df_filtered_by_dashboard['product_code'].isin(product_filter))
    filtered_df = df_filtered_by_dashboard[base_filter].copy()
else:
    # Create entity column for filtering if it doesn't exist
    if 'entity' not in df.columns:
        df['entity'] = df.apply(lambda row: 
            row.get('partner', '') if pd.notna(row.get('partner')) and row.get('partner') 
            else row.get('company', ''), axis=1)
    
    # Auto-filter by product code based on dashboard selection
    if st.session_state.selected_dashboard == 'Relay Licenses':
        # Filter for Relay licenses (assuming 'REL' is the product code for Relay)
        dashboard_product_filter = ['REL'] if 'product_code' in df.columns else []
    elif st.session_state.selected_dashboard == 'User Licenses':
        # Filter for User licenses (assuming 'SUB' or other codes are for User licenses)
        dashboard_product_filter = ['SUB', 'USR', 'USR_LIC'] if 'product_code' in df.columns else []
    else:
        # All Licenses - no product code filtering
        dashboard_product_filter = []
    
    # Apply dashboard-specific product filtering
    if dashboard_product_filter and 'product_code' in df.columns:
        df_filtered_by_dashboard = df[df['product_code'].isin(dashboard_product_filter)]
    else:
        df_filtered_by_dashboard = df
    
    base_filter = (
        (df_filtered_by_dashboard['entity'].isin(companies)) &
        (df_filtered_by_dashboard['status'].isin(status_filter))
    )
    # Add currency filter if available
    if currency_filter and 'currency' in df_filtered_by_dashboard.columns:
        base_filter = base_filter & (df_filtered_by_dashboard['currency'].isin(currency_filter))
    # Add product code filter if available
    if product_filter and 'product_code' in df_filtered_by_dashboard.columns:
        base_filter = base_filter & (df_filtered_by_dashboard['product_code'].isin(product_filter))
    filtered_df = df_filtered_by_dashboard[base_filter].copy()

# Create unified entity column for merging with user/active user data
if not filtered_df.empty:
    # Ensure entity column exists and is properly populated
    if 'entity' not in filtered_df.columns:
        filtered_df['entity'] = filtered_df.apply(lambda row: 
            row.get('partner', '') if pd.notna(row.get('partner')) and row.get('partner') 
            else row.get('company', ''), axis=1)
    else:
        # Update existing entity column to ensure it's correct
        filtered_df['entity'] = filtered_df.apply(lambda row: 
            row.get('partner', '') if pd.notna(row.get('partner')) and row.get('partner') 
            else row.get('company', ''), axis=1)

# Ensure 'user_count' column exists before merging
if 'user_count' not in filtered_df.columns:
    filtered_df = filtered_df.assign(user_count=0)

# Ensure 'active_users' column exists before accessing it
if 'active_users' not in filtered_df.columns:
    filtered_df = filtered_df.assign(active_users=0)

# Fetch active users per company
db = DatabaseConnection()
active_users_df = db.get_active_users_per_company()

# Merge active user data with filtered_df
if not active_users_df.empty and not filtered_df.empty:
    # Ensure entity column exists before merge
    if 'entity' not in filtered_df.columns:
        filtered_df['entity'] = filtered_df.apply(lambda row: 
            row.get('partner', '') if pd.notna(row.get('partner')) and row.get('partner') 
            else row.get('company', ''), axis=1)
    
    filtered_df = filtered_df.merge(active_users_df[['entity_name', 'active_users']], left_on='entity', right_on='entity_name', how='left')
    # Use active_users_y if it exists, else fill with 0
    if 'active_users_y' in filtered_df.columns:
        filtered_df = filtered_df.assign(active_users=filtered_df['active_users_y'].fillna(0))
    elif 'active_users' not in filtered_df.columns:
        filtered_df = filtered_df.assign(active_users=0)
    else:
        filtered_df = filtered_df.assign(active_users=filtered_df['active_users'].fillna(0))
    # Cleanup extra columns from merge
    columns_to_drop = [col for col in ['active_users_x', 'active_users_y', 'entity_name'] if col in filtered_df.columns]
    if columns_to_drop:
        filtered_df = filtered_df.drop(columns=columns_to_drop)

# Fetch user count from users_portal table
user_count_df = db.get_user_count_from_portal()

# Merge user count data with filtered_df
if not user_count_df.empty and not filtered_df.empty:
    # Ensure entity column exists before merge
    if 'entity' not in filtered_df.columns:
        filtered_df['entity'] = filtered_df.apply(lambda row: 
            row.get('partner', '') if pd.notna(row.get('partner')) and row.get('partner') 
            else row.get('company', ''), axis=1)
    
    filtered_df = filtered_df.merge(user_count_df[['entity_name', 'user_count']], left_on='entity', right_on='entity_name', how='left')
    # Use user_count_y if it exists, else fill with 0
    if 'user_count_y' in filtered_df.columns:
        filtered_df = filtered_df.assign(user_count=filtered_df['user_count_y'].fillna(0))
    elif 'user_count' not in filtered_df.columns:
        filtered_df = filtered_df.assign(user_count=0)
    else:
        filtered_df = filtered_df.assign(user_count=filtered_df['user_count'].fillna(0))
    # Cleanup extra columns from merge
    columns_to_drop = [col for col in ['user_count_x', 'user_count_y', 'entity_name'] if col in filtered_df.columns]
    if columns_to_drop:
        filtered_df = filtered_df.drop(columns=columns_to_drop)

# Fetch active relay devices data
current_user = auth_manager.get_current_user()
user_role = current_user.get('role', 'Admin') if current_user else 'Admin'
user_company_id = current_user.get('company_id') if current_user else None
user_partner_id = current_user.get('partner_id') if current_user else None

active_relay_devices_df = db.get_active_relay_devices(
    user_role=user_role,
    user_company_id=user_company_id,
    user_partner_id=user_partner_id
)

# Process active relay devices data - aggregate by company and partner
if not active_relay_devices_df.empty:
    # Create entity-based aggregation for dashboard display
    company_relay_data = active_relay_devices_df.groupby('company_name').agg({
        'active_relay_devices': 'sum'
    }).reset_index()
    company_relay_data['entity_name'] = company_relay_data['company_name']
    company_relay_data['entity_type'] = 'Company'
    
    # Handle partner data (some users might have direct partner relationships)
    partner_relay_data = active_relay_devices_df[active_relay_devices_df['partner_name'].notna()].groupby('partner_name').agg({
        'active_relay_devices': 'sum'
    }).reset_index()
    partner_relay_data['entity_name'] = partner_relay_data['partner_name']
    partner_relay_data['entity_type'] = 'Partner'
    
    # Combine company and partner data
    relay_aggregated_df = pd.concat([company_relay_data, partner_relay_data], ignore_index=True)
else:
    relay_aggregated_df = pd.DataFrame(columns=['entity_name', 'active_relay_devices'])

# Merge active relay devices data with filtered_df
if not relay_aggregated_df.empty and not filtered_df.empty:
    # Ensure entity column exists before merge
    if 'entity' not in filtered_df.columns:
        filtered_df['entity'] = filtered_df.apply(lambda row: 
            row.get('partner', '') if pd.notna(row.get('partner')) and row.get('partner') 
            else row.get('company', ''), axis=1)
    
    filtered_df = filtered_df.merge(relay_aggregated_df[['entity_name', 'active_relay_devices']], left_on='entity', right_on='entity_name', how='left')
    # Use active_relay_devices_y if it exists, else fill with 0
    if 'active_relay_devices_y' in filtered_df.columns:
        filtered_df = filtered_df.assign(active_relay_devices=filtered_df['active_relay_devices_y'].fillna(0))
    elif 'active_relay_devices' not in filtered_df.columns:
        filtered_df = filtered_df.assign(active_relay_devices=0)
    else:
        filtered_df = filtered_df.assign(active_relay_devices=filtered_df['active_relay_devices'].fillna(0))
    # Cleanup extra columns from merge
    columns_to_drop = [col for col in ['active_relay_devices_x', 'active_relay_devices_y', 'entity_name'] if col in filtered_df.columns]
    if columns_to_drop:
        filtered_df = filtered_df.drop(columns=columns_to_drop)
else:
    # Ensure active_relay_devices column exists
    if 'active_relay_devices' not in filtered_df.columns:
        filtered_df = filtered_df.assign(active_relay_devices=0)

# Main content area - Redesigned with better hierarchy

# Dashboard info banner
if st.session_state.selected_dashboard == 'Relay Licenses':
    st.info("🔗 **Relay Licenses Dashboard**: Viewing data for Relay infrastructure licenses. These licenses control the number of Relay instances that can be deployed.")
elif st.session_state.selected_dashboard == 'User Licenses':
    st.info("👥 **User Licenses Dashboard**: Viewing data for user access licenses. These licenses control the number of users who can access the system.")
elif st.session_state.selected_dashboard == 'System Logs':
    st.info("📋 **System Logs Dashboard**: Unified view of all system activity logs from Portal, App, and Waypoint systems for monitoring and auditing.")
else:
    st.info("📊 **All Licenses Dashboard**: Viewing data for all license types combined.")

# Check if we're showing the logs dashboard
if st.session_state.selected_dashboard == 'System Logs':
    # Logs Dashboard Content
    st.subheader("📋 System Activity Logs")
    
    # Load filter options
    db = DatabaseConnection()
    filter_options = db.get_log_filters()
    
    # Filters Section
    with st.expander("🔍 Log Filters", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Date range filter
            date_range = st.date_input(
                "📅 Date Range",
                value=(datetime.now().date() - timedelta(days=7), datetime.now().date()),
                help="Filter logs by date range"
            )
            
            # User filter
            user_options = [f"{user['name']} ({user['email']})" for user in filter_options['users']]
            user_options.insert(0, "All Users")
            selected_user = st.selectbox(
                "👤 User",
                options=user_options,
                help="Filter by specific user"
            )
        
        with col2:
            # Company filter
            company_options = [company['name'] for company in filter_options['companies']]
            company_options.insert(0, "All Companies")
            selected_company = st.selectbox(
                "🏢 Company",
                options=company_options,
                help="Filter by company"
            )
            
            # Partner filter
            partner_options = [partner['name'] for partner in filter_options['partners']]
            partner_options.insert(0, "All Partners")
            selected_partner = st.selectbox(
                "🤝 Partner",
                options=partner_options,
                help="Filter by partner"
            )
        
        with col3:
            # Log type filter
            log_type_options = ["All Types"] + filter_options['log_types']
            selected_log_type = st.selectbox(
                "📝 Log Type",
                options=log_type_options,
                help="Filter by log source"
            )
            
            # Refresh button
            if st.button("🔄 Refresh Logs", type="primary", use_container_width=True, key="logs_refresh"):
                st.rerun()
    
    # Ranking Panels
    st.subheader("🏆 Today's Top Performers")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🔗 Top 3 Most Active Waypoints")
        top_waypoints = db.get_top_waypoints_today()
        if not top_waypoints.empty:
            for idx, row in top_waypoints.iterrows():
                with st.container():
                    col_rank, col_info = st.columns([1, 4])
                    with col_rank:
                        st.markdown(f"**#{idx + 1}**")
                    with col_info:
                        st.write(f"**{row['waypoint_name']}** (ID: {row['waypoint_id']})")
                        st.write(f"📊 {row['actions_today']} actions today")
        else:
            st.info("📊 No waypoint activity recorded today")
    
    with col2:
        st.markdown("#### 💻 Top 3 Most Active Sessions")
        top_sessions = db.get_top_sessions_today()
        if not top_sessions.empty:
            for idx, row in top_sessions.iterrows():
                with st.container():
                    col_rank, col_info = st.columns([1, 4])
                    with col_rank:
                        st.markdown(f"**#{idx + 1}**")
                    with col_info:
                        st.write(f"**Session {row['session_id']}**")
                        st.write(f"📊 {row['activity_count']} activities today")
                        if pd.notna(row['first_activity']):
                            st.write(f"⏰ {row['first_activity'].strftime('%H:%M')} - {row['last_activity'].strftime('%H:%M')}")
        else:
            st.info("📊 No session activity recorded today")
    
    # Load and display logs
    st.subheader("📋 Activity Logs")
    
    # Prepare filter parameters
    start_date = date_range[0] if len(date_range) > 0 else None
    end_date = date_range[1] if len(date_range) > 1 else None
    
    user_id = None
    if selected_user != "All Users":
        user_name = selected_user.split(" (")[0]
        for user in filter_options['users']:
            if user['name'] == user_name:
                user_id = user['id']
                break
    
    company_id = None
    if selected_company != "All Companies":
        for company in filter_options['companies']:
            if company['name'] == selected_company:
                company_id = company['id']
                break
    
    partner_id = None
    if selected_partner != "All Partners":
        for partner in filter_options['partners']:
            if partner['name'] == selected_partner:
                partner_id = partner['id']
                break
    
    log_type = None
    if selected_log_type != "All Types":
        log_type = selected_log_type
    
    # Load logs data
    logs_df = db.get_unified_logs(
        start_date=start_date,
        end_date=end_date,
        user_id=user_id,
        company_id=company_id,
        partner_id=partner_id,
        log_type=log_type
    )
    
    # Display logs table
    if not logs_df.empty:
        # Convert timestamp to datetime for better display
        logs_df['timestamp'] = pd.to_datetime(logs_df['timestamp'])
        
        # Add log type icons
        logs_df['log_type_icon'] = logs_df['log_source'].map({
            'portal_logs': '🌐',
            'app_log': '📱',
            'fidoapi_waypoint_logs': '📍'
        })
        
        # Display the logs table
        st.dataframe(
            logs_df[['timestamp', 'log_type_icon', 'user_name', 'action', 'status', 'company_name', 'partner_name', 'session_id', 'waypoint_id', 'notes']],
            use_container_width=True,
            column_config={
                'timestamp': st.column_config.DatetimeColumn('Timestamp', format='DD-MM-YYYY HH:mm:ss'),
                'log_type_icon': st.column_config.TextColumn('Type', width="small"),
                'user_name': st.column_config.TextColumn('User', width="medium"),
                'action': st.column_config.TextColumn('Action', width="medium"),
                'status': st.column_config.TextColumn('Status', width="small"),
                'company_name': st.column_config.TextColumn('Company', width="medium"),
                'partner_name': st.column_config.TextColumn('Partner', width="medium"),
                'session_id': st.column_config.TextColumn('Session ID', width="small"),
                'waypoint_id': st.column_config.TextColumn('Waypoint ID', width="small"),
                'notes': st.column_config.TextColumn('Notes', width="large")
            },
            hide_index=True
        )
        
        # Summary statistics
        st.subheader("📊 Log Summary")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_logs = len(logs_df)
            st.metric("Total Logs", f"{total_logs:,}")
        
        with col2:
            unique_users = logs_df['user_name'].nunique()
            st.metric("Unique Users", f"{unique_users:,}")
        
        with col3:
            log_types = logs_df['log_source'].value_counts()
            portal_logs = log_types.get('portal_logs', 0)
            st.metric("Portal Logs", f"{portal_logs:,}")
        
        with col4:
            app_logs = log_types.get('app_log', 0)
            st.metric("App Logs", f"{app_logs:,}")
        
        # Log type distribution chart
        if len(log_types) > 0:
            st.subheader("📈 Log Type Distribution")
            fig_log_types = px.pie(
                values=log_types.values,
                names=log_types.index,
                title="Distribution of Log Types",
                color_discrete_map={
                    'portal_logs': '#667eea',
                    'app_log': '#764ba2',
                    'fidoapi_waypoint_logs': '#f093fb'
                }
            )
            st.plotly_chart(fig_log_types, use_container_width=True)
        
        # Activity timeline
        st.subheader("⏰ Activity Timeline")
        timeline_df = logs_df.groupby(logs_df['timestamp'].dt.date).size().reset_index(name='count')
        timeline_df.columns = ['date', 'activity_count']
        
        if not timeline_df.empty:
            fig_timeline = px.line(
                timeline_df,
                x='date',
                y='activity_count',
                title="Daily Activity Count",
                labels={'activity_count': 'Number of Activities', 'date': 'Date'}
            )
            st.plotly_chart(fig_timeline, use_container_width=True)
    
    else:
        st.info("📊 No logs found for the selected filters. Try adjusting your filter criteria.")
    
    # End of logs dashboard
    st.stop()

# License Dashboard Content (existing code)
# Primary Metrics Row - Most important KPIs
st.subheader("📈 Key Performance Indicators")
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_licences = filtered_df['number_of_licenses'].sum() if not filtered_df.empty else 0
    st.metric(
        label="Total Licenses", 
        value=f"{total_licences:,}",
        help="Total number of licenses across all entities"
    )

with col2:
    total_users = int(filtered_df['user_count'].sum()) if not filtered_df.empty else 0
    st.metric(
        label="Total Users", 
        value=f"{total_users:,}",
        help="Number of users created under companies/partners with licenses"
    )

with col3:
    active_users = int(filtered_df['active_users'].sum()) if not filtered_df.empty else 0
    st.metric(
        label="Active Users", 
        value=f"{active_users:,}",
        help="Users with activity detected in the last 14 days"
    )

with col4:
    active_licences = filtered_df[filtered_df['status'] == 'Active']['number_of_licenses'].sum() if not filtered_df.empty else 0
    st.metric(
        label="Active Licenses", 
        value=f"{active_licences:,}",
        help="Currently active licenses"
    )

# Secondary Metrics Row - Financial and utilization metrics
st.subheader("💰 Financial & Utilization Metrics")
col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.session_state.selected_dashboard == 'Relay Licenses':
        avg_relay_cost = filtered_df['cost_per_license'].mean() if not filtered_df.empty else 0
        st.metric(
            label="Avg Relay Cost", 
            value=f"£{avg_relay_cost:,.0f}",
            help="Average cost per Relay license"
        )
    elif st.session_state.selected_dashboard == 'User Licenses':
        avg_user_cost = filtered_df['cost_per_license'].mean() if not filtered_df.empty else 0
        st.metric(
            label="Avg User Cost", 
            value=f"£{avg_user_cost:,.0f}",
            help="Average cost per User license"
        )
    else:
        total_revenue = filtered_df['total_cost'].sum() if not filtered_df.empty else 0
        st.metric(
            label="Total Revenue", 
            value=f"£{total_revenue:,.0f}",
            help="Total revenue from all licenses"
        )

with col2:
    active_relay_devices = int(filtered_df['active_relay_devices'].sum()) if not filtered_df.empty else 0
    st.metric(
        label="🔗 Active Relay Devices", 
        value=f"{active_relay_devices:,}",
        help="Unique relay devices with activity in the last 14 days"
    )

with col3:
    if st.session_state.selected_dashboard == 'Relay Licenses' and not filtered_df.empty:
        relay_licenses = filtered_df['number_of_licenses'].sum()
        relay_utilization = (active_relay_devices / relay_licenses * 100) if relay_licenses > 0 else 0
        st.metric(
            label="🔗 Relay Utilization", 
            value=f"{relay_utilization:.1f}%",
            help="Percentage of relay licenses being actively used"
        )
    else:
        total_entities = len(filtered_df['entity'].unique()) if not filtered_df.empty else 0
        st.metric(
            label="🏢 Total Entities", 
            value=f"{total_entities:,}",
            help="Number of companies/partners with licenses"
        )

with col4:
    if not filtered_df.empty:
        if st.session_state.selected_dashboard == 'Relay Licenses':
            avg_utilization = (filtered_df['active_relay_devices'].sum() / filtered_df['number_of_licenses'].sum() * 100) if filtered_df['number_of_licenses'].sum() > 0 else 0
            st.metric(
                label="📈 Avg Relay Utilization", 
                value=f"{avg_utilization:.1f}%",
                help="Average relay device utilization across all entities"
            )
        else:
            avg_utilization = (filtered_df['active_users'].sum() / filtered_df['number_of_licenses'].sum() * 100) if filtered_df['number_of_licenses'].sum() > 0 else 0
            st.metric(
                label="📈 Avg Utilization", 
                value=f"{avg_utilization:.1f}%",
                help="Average license utilization across all entities"
            )
    else:
        st.metric(
            label="📈 Avg Utilization", 
            value="0%",
            help="Average license utilization across all entities"
        )

st.markdown("---")

# Data Management Section
st.subheader("📋 License Data Management")

# Action buttons row
col1, col2, col3, col4 = st.columns(4)
with col1:
    if can_edit:
        if st.button("➕ Add New License", type="primary", use_container_width=True, key="main_add_license"):
            st.session_state.show_add_form = True
    else:
        st.button("➕ Add New License", disabled=True, help="Admin access required", use_container_width=True, key="main_add_license_disabled")

with col2:
    if can_edit:
        if st.button("📥 Import CSV", use_container_width=True, key="main_import_csv"):
            st.session_state.show_import = True
    else:
        st.button("📥 Import CSV", disabled=True, help="Admin access required", use_container_width=True, key="main_import_csv_disabled")

with col3:
    if st.button("📊 Export Data", use_container_width=True, key="export_data"):
        # Export functionality
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"license_data_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

with col4:
    if st.button("🔄 Refresh", use_container_width=True, key="main_refresh"):
        load_license_data.clear()
        st.session_state.df_data = None
        st.rerun()

# User guidance
if can_edit:
    st.info("💡 **Editing Tip**: Click any cell in the table below to edit. Changes are saved automatically.")
else:
    st.info("👁️ **View Only Mode**: Contact admin for edit access. Use the action buttons above when available.")

# Data table with improved styling
display_df = filtered_df.copy()
if not display_df.empty:
    # Ensure entity column exists in display_df
    if 'entity' not in display_df.columns:
        display_df['entity'] = display_df.apply(lambda row: 
            row.get('partner', '') if pd.notna(row.get('partner')) and row.get('partner') 
            else row.get('company', ''), axis=1)
    
    # Calculate utilization based on license type
    if st.session_state.selected_dashboard == 'Relay Licenses':
        display_df['active_utilization_pct'] = ((display_df['active_relay_devices'] / display_df['number_of_licenses']) * 100).round(1)
    else:
        display_df['active_utilization_pct'] = ((display_df['active_users'] / display_df['number_of_licenses']) * 100).round(1)
    
    display_df['total_utilization_pct'] = ((display_df['user_count'] / display_df['number_of_licenses']) * 100).round(1)
    
    # Create entity_type column for display
    display_df['entity_type'] = display_df.apply(lambda row: 
        'Partner' if pd.notna(row.get('partner')) and row.get('partner') 
        else 'Company', axis=1)
    
    # Add entity type labels to entity names for charts
    display_df['entity_with_type'] = display_df.apply(lambda row: 
        f"{row['entity']} ({row['entity_type']})", axis=1)
    
    # Also add entity_with_type to filtered_df for analytics
    filtered_df['entity_type'] = filtered_df.apply(lambda row: 
        'Partner' if pd.notna(row.get('partner')) and row.get('partner') 
        else 'Company', axis=1)
    filtered_df['entity_with_type'] = filtered_df.apply(lambda row: 
        f"{row['entity']} ({row['entity_type']})", axis=1)

# Show data table with improved configuration
if can_edit:
    # Editable data for admins
    edit_columns = ['company', 'partner', 'product_label', 'start_date', 'end_date', 'number_of_licenses', 
                   'user_count', 'active_users', 'active_relay_devices', 'active_utilization_pct', 'cost_per_license', 'total_cost', 'currency', 'status']
    available_edit_columns = [col for col in edit_columns if col in display_df.columns]
    
    # Keep ID in original_df for database updates but don't display it
    st.session_state.original_df = display_df[available_edit_columns + ['id'] if 'id' in display_df.columns else available_edit_columns].copy()
    
    edited_df = st.data_editor(
        display_df[available_edit_columns],
        use_container_width=True,
        column_config={
            'company': st.column_config.TextColumn('Company', disabled=True, width="medium"),  # Read-only (complex to change)
            'partner': st.column_config.TextColumn('Partner', disabled=True, width="medium"),  # Read-only (complex to change)
            'product_label': st.column_config.TextColumn('Product Type', disabled=True, width="medium"),  # Read-only (FK relationship)
            'start_date': st.column_config.DateColumn('Start Date', required=True),
            'end_date': st.column_config.DateColumn('End Date', required=True),
            'number_of_licenses': st.column_config.NumberColumn('Licences', min_value=1, required=True, width="small"),
            'user_count': st.column_config.NumberColumn('Total Users', disabled=True, width="small"),  # Calculated field
            'active_users': st.column_config.NumberColumn('Active Users', disabled=True, width="small"),  # Calculated field
            'active_relay_devices': st.column_config.NumberColumn('Active Relay Devices', disabled=True, width="small"),  # Calculated field
            'active_utilization_pct': st.column_config.ProgressColumn(
                'Active Utilization %',
                help='Percentage of licences being actively used (calculated field)',
                min_value=0,
                max_value=150,
                format='%.1f%%',
                width="medium"
            ),
            'cost_per_license': st.column_config.NumberColumn('Cost/Licence (per year)', min_value=0.01, format='%.2f', required=True),
            'total_cost': st.column_config.NumberColumn('Total Cost', disabled=True, format='%.2f'),  # Calculated field
            'currency': st.column_config.SelectboxColumn('Currency', options=['GBP', 'USD', 'EUR', 'CAD', 'AUD', 'JPY', 'CHF', 'SEK', 'NOK', 'DKK'], required=True, width="small"),
            'status': st.column_config.SelectboxColumn('Status', options=['Active', 'Expired'], required=True, width="small")
        },
        hide_index=True,
        key="licence_editor"
    )
    col_save, col_delete = st.columns([1, 1])
    with col_save:
        if st.button("💾 Save Changes", type="primary"):
            db = DatabaseConnection()
            changes_saved = 0
            
            # Check if we have original data to compare against
            if st.session_state.original_df is None:
                st.error("❌ No original data found for comparison. Please refresh the page.")
            else:
                # Compare edited_df with original to find changes
                for idx in edited_df.index:
                    # Get the license ID from original_df (which includes ID)
                    if 'id' in st.session_state.original_df.columns:
                        license_id = st.session_state.original_df.loc[idx, 'id']
                        
                        # Check each editable field for changes
                        changes = {}
                        editable_fields = ['start_date', 'end_date', 'number_of_licenses', 'cost_per_license', 'currency', 'status']
                        
                        for field in editable_fields:
                            if field in edited_df.columns and field in st.session_state.original_df.columns:
                                old_val = st.session_state.original_df.loc[idx, field]
                                new_val = edited_df.loc[idx, field]
                                
                                if old_val != new_val:
                                    # Convert pandas/numpy types to Python native types for MySQL
                                    if hasattr(new_val, 'item'):  # numpy/pandas scalar
                                        changes[field] = new_val.item()
                                    else:
                                        changes[field] = new_val
                        
                        # If there are changes, update the database
                        if changes:
                            # Calculate new total_cost if relevant fields changed
                            if 'number_of_licenses' in changes or 'cost_per_license' in changes:
                                licences = changes.get('number_of_licenses', edited_df.loc[idx, 'number_of_licenses'])
                                cost_per = changes.get('cost_per_license', edited_df.loc[idx, 'cost_per_license'])
                                changes['total_cost'] = licences * cost_per
                            
                            if db.update_license(license_id, changes):
                                changes_saved += 1
            
            if changes_saved > 0:
                st.success(f"✅ Saved {changes_saved} changes to database!")
                # Clear cache and refresh
                load_license_data.clear()
                st.session_state.df_data = None
                st.session_state.original_df = None  # Reset original for next comparison
                st.rerun()
            else:
                st.info("ℹ️ No changes detected to save.")
    with col_delete:
        if st.button("🗑️ Delete Licences", type="secondary"):
            st.session_state.show_delete_modal = True
    if st.session_state.get("show_delete_modal", False):
        delete_licence_dialog()

else:
    # Read-only view for viewers - show comprehensive data
    view_columns = ['company', 'partner', 'product_label', 'start_date', 'end_date', 'number_of_licenses', 
                   'user_count', 'active_users', 'active_relay_devices', 'active_utilization_pct', 'cost_per_license', 'total_cost', 'currency', 'status']
    
    # Only include columns that exist in the dataframe
    available_view_columns = [col for col in view_columns if col in display_df.columns]
    
    st.dataframe(
        display_df[available_view_columns],
        use_container_width=True,
        column_config={
            'company': st.column_config.TextColumn('Company', width="medium"),
            'partner': st.column_config.TextColumn('Partner', width="medium"),
            'product_label': st.column_config.TextColumn('Product Type', width="medium"),
            'start_date': st.column_config.DateColumn('Start Date'),
            'end_date': st.column_config.DateColumn('End Date'),
            'number_of_licenses': st.column_config.NumberColumn('Licences', width="small"),
            'user_count': st.column_config.NumberColumn('Total Users', width="small"),
            'active_users': st.column_config.NumberColumn('Active Users', width="small"),
            'active_relay_devices': st.column_config.NumberColumn('Active Relay Devices', width="small"),
            'active_utilization_pct': st.column_config.ProgressColumn(
                'Active Utilization %',
                help='Percentage of licences being actively used',
                min_value=0,
                max_value=150,
                format='%.1f%%',
                width="medium"
            ),
            'cost_per_license': st.column_config.NumberColumn('Cost/Licence (per year)', format='%.2f'),
            'total_cost': st.column_config.NumberColumn('Total Cost', format='%.2f'),
            'currency': st.column_config.TextColumn('Currency', width="small"),
            'status': st.column_config.TextColumn('Status', width="small")
        }
    )

# Show dialogs when requested
if st.session_state.show_add_form:
    add_license_dialog()

if st.session_state.show_import:
    bulk_import_dialog()

st.markdown("---")

# Analytics & Visualization Section
st.subheader("📊 Analytics & Insights")

if not filtered_df.empty:
    # Dashboard-specific charts
    if st.session_state.selected_dashboard == 'Relay Licenses':
        # Relay-specific charts
        st.markdown("#### 🔗 Relay Infrastructure Analytics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Relay deployment vs licenses chart
            relay_summary = filtered_df.groupby('entity_with_type').agg({
                'number_of_licenses': 'sum',
                'active_relay_devices': 'sum'
            }).reset_index()
            
            if not relay_summary.empty:
                fig_relay = px.bar(
                    relay_summary,
                    x='entity_with_type',
                    y=['number_of_licenses', 'active_relay_devices'],
                    title="Relay Licenses vs Active Devices",
                    barmode='group',
                    labels={'value': 'Count', 'variable': 'Type'},
                    color_discrete_map={'number_of_licenses': '#667eea', 'active_relay_devices': '#764ba2'}
                )
                fig_relay.update_xaxes(tickangle=45)
                fig_relay.update_layout(
                    title_font_size=16,
                    title_x=0.5,
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_relay, use_container_width=True)
            else:
                st.info("📊 No relay data available")
        
        with col2:
            st.subheader("🔗 Relay Device Utilization")
            # Show relay device utilization rates
            relay_util = filtered_df.copy()
            relay_util['relay_utilization_rate'] = (relay_util['active_relay_devices'] / relay_util['number_of_licenses'] * 100).round(1)
            
            if not relay_util.empty:
                fig_util = px.scatter(
                    relay_util,
                    x='number_of_licenses',
                    y='active_relay_devices',
                    size='relay_utilization_rate',
                    hover_name='entity_with_type',
                    title="Relay License vs Active Devices",
                    labels={'number_of_licenses': 'Relay Licenses Available', 'active_relay_devices': 'Active Relay Devices'}
                )
                # Add diagonal line for 100% utilization
                max_val = max(relay_util['number_of_licenses'].max(), relay_util['active_relay_devices'].max())
                if max_val > 0:
                    fig_util.add_shape(
                        type="line", line=dict(dash="dash", color="red"),
                        x0=0, y0=0, x1=max_val, y1=max_val
                    )
                    fig_util.add_annotation(
                        x=max_val*0.7, y=max_val*0.8,
                        text="100% Utilization Line",
                        showarrow=False,
                        font=dict(color="red", size=10)
                    )
                st.plotly_chart(fig_util, use_container_width=True)
            else:
                st.info("📊 No relay utilization data available")
        
        # Add relay device summary table
        st.subheader("🔗 Relay Device Summary")
        if not filtered_df.empty:
            relay_summary_table = filtered_df.groupby('entity_with_type').agg({
                'number_of_licenses': 'sum',
                'active_relay_devices': 'sum',
                'cost_per_license': 'mean',
                'total_cost': 'sum'
            }).reset_index()
            
            relay_summary_table['relay_utilization_pct'] = (relay_summary_table['active_relay_devices'] / relay_summary_table['number_of_licenses'] * 100).round(1)
            relay_summary_table['avg_cost_per_device'] = (relay_summary_table['total_cost'] / relay_summary_table['active_relay_devices']).round(2)
            
            # Replace infinite values with 0
            relay_summary_table = relay_summary_table.replace([np.inf, -np.inf], 0)
            
            st.dataframe(
                relay_summary_table,
                use_container_width=True,
                column_config={
                    'entity_with_type': st.column_config.TextColumn('Entity', width="medium"),
                    'number_of_licenses': st.column_config.NumberColumn('Relay Licenses', width="small"),
                    'active_relay_devices': st.column_config.NumberColumn('Active Devices', width="small"),
                    'relay_utilization_pct': st.column_config.ProgressColumn(
                        'Device Utilization %',
                        help='Percentage of relay licenses with active devices',
                        min_value=0,
                        max_value=150,
                        format='%.1f%%',
                        width="medium"
                    ),
                    'cost_per_license': st.column_config.NumberColumn('Avg Cost/License', format='%.2f', width="small"),
                    'total_cost': st.column_config.NumberColumn('Total Cost', format='%.2f', width="small"),
                    'avg_cost_per_device': st.column_config.NumberColumn('Cost/Active Device', format='%.2f', width="small")
                }
            )
        else:
            st.info("📊 No relay data available for summary table")
        
        # Add detailed user-level relay devices table
        st.subheader("👥 User-Level Relay Device Activity")
        if not active_relay_devices_df.empty:
            # Show top users by relay device activity
            top_users = active_relay_devices_df.nlargest(10, 'active_relay_devices')
            
            st.dataframe(
                top_users,
                use_container_width=True,
                column_config={
                    'user_name': st.column_config.TextColumn('User Name', width="medium"),
                    'email': st.column_config.TextColumn('Email', width="medium"),
                    'company_name': st.column_config.TextColumn('Company', width="medium"),
                    'partner_name': st.column_config.TextColumn('Partner', width="medium"),
                    'active_relay_devices': st.column_config.NumberColumn('Active Relay Devices', width="small")
                }
            )
            
            # Show summary statistics
            col1, col2, col3 = st.columns(3)
            with col1:
                total_users_with_devices = len(active_relay_devices_df)
                st.metric("👥 Users with Active Devices", f"{total_users_with_devices}")
            
            with col2:
                avg_devices_per_user = active_relay_devices_df['active_relay_devices'].mean()
                st.metric("🔗 Avg Devices per User", f"{avg_devices_per_user:.1f}")
            
            with col3:
                max_devices_user = active_relay_devices_df.loc[active_relay_devices_df['active_relay_devices'].idxmax()]
                st.metric("🏆 Top User", f"{max_devices_user['user_name']} ({max_devices_user['active_relay_devices']} devices)")
        else:
            st.info("📊 No user-level relay device data available")
    
    elif st.session_state.selected_dashboard == 'User Licenses':
        # User-specific charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("👥 User Utilization")
            # Show user utilization rates
            user_util = filtered_df.copy()
            user_util['utilization_rate'] = (user_util['active_users'] / user_util['number_of_licenses'] * 100).round(1)
            
            if not user_util.empty:
                fig_util = px.scatter(
                    user_util,
                    x='number_of_licenses',
                    y='active_users',
                    size='utilization_rate',
                    hover_name='entity_with_type',
                    title="User License Utilization",
                    labels={'number_of_licenses': 'Licenses Available', 'active_users': 'Active Users'}
                )
                st.plotly_chart(fig_util, use_container_width=True)
            else:
                st.info("📊 No user data available")
        
        with col2:
            st.subheader("👥 User Growth Trend")
            # Show user growth over time
            if 'start_date' in filtered_df.columns:
                user_trend = filtered_df.groupby('start_date').agg({
                    'number_of_licenses': 'sum',
                    'user_count': 'sum'
                }).reset_index()
                
                if not user_trend.empty:
                    fig_trend = px.line(
                        user_trend,
                        x='start_date',
                        y=['number_of_licenses', 'user_count'],
                        title="User License Growth Over Time",
                        labels={'value': 'Count', 'variable': 'Type'}
                    )
                    st.plotly_chart(fig_trend, use_container_width=True)
                else:
                    st.info("📊 No trend data available")
            else:
                st.info("📊 No date data available")
    
    else:
        # All Licenses - show original charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Licences vs Active Users")
            # Focus on non-monetary metrics to avoid currency mixing
            company_summary = filtered_df.groupby('entity_with_type').agg({
                'number_of_licenses': 'sum',
                'user_count': 'sum',
                'active_users': 'sum'
            }).reset_index()
            
            # Show top 10 entities by license count
            top_companies = company_summary.nlargest(10, 'number_of_licenses') if not company_summary.empty else pd.DataFrame()
            
            if not top_companies.empty:
                fig_scatter = px.scatter(
                    top_companies,
                    x='number_of_licenses',
                    y='active_users',
                    size='number_of_licenses',  # Use license count instead of revenue for sizing
                    hover_name='entity_with_type',
                    hover_data={'user_count': True},
                    title="Licences vs Active Users (bubble size = total licences)",
                    labels={'number_of_licenses': 'Number of Licences', 'active_users': 'Active Users'}
                )
                # Add diagonal line for 100% utilization
                max_val = max(top_companies['number_of_licenses'].max(), top_companies['active_users'].max())
                fig_scatter.add_shape(
                    type="line", line=dict(dash="dash", color="red"),
                    x0=0, y0=0, x1=max_val, y1=max_val
                )
                fig_scatter.add_annotation(
                    x=max_val*0.7, y=max_val*0.8,
                    text="100% Utilization Line",
                    showarrow=False,
                    font=dict(color="red", size=10)
                )
                st.plotly_chart(fig_scatter, use_container_width=True)
            else:
                st.info("📊 No data available for scatter plot")

        with col2:
            st.subheader("Revenue by Currency")
            # Show revenue grouped by currency to avoid mixing currencies
            if 'currency' in filtered_df.columns:
                currency_revenue = filtered_df.groupby('currency').agg({
                    'total_cost': 'sum',
                    'number_of_licenses': 'sum'
                }).reset_index()
                currency_revenue = currency_revenue.sort_values('total_cost', ascending=False)
                
                if not currency_revenue.empty:
                    # Create currency labels with totals
                    currency_revenue['display_label'] = currency_revenue.apply(
                        lambda row: f"{row['currency']}: {row['total_cost']:,.0f}", axis=1
                    )
                    
                    fig_bar = px.bar(
                        currency_revenue,
                        x='currency',
                        y='total_cost',
                        title="Total Revenue by Currency",
                        labels={'total_cost': 'Revenue', 'currency': 'Currency'},
                        text='total_cost'
                    )
                    fig_bar.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                    fig_bar.update_xaxes(tickangle=0)
                    st.plotly_chart(fig_bar, use_container_width=True)
                else:
                    st.info("📊 No data available for revenue chart")
            else:
                # Fallback for data without currency column
                company_summary_with_revenue = filtered_df.groupby('entity_with_type').agg({
                    'total_cost': 'sum'
                }).reset_index()
                top_revenue_companies = company_summary_with_revenue.nlargest(10, 'total_cost')
                
                if not top_revenue_companies.empty:
                    fig_bar = px.bar(
                        top_revenue_companies,
                        x='entity_with_type',
                        y='total_cost',
                        title="Top 10 Entities by Revenue",
                        labels={'total_cost': 'Revenue', 'entity_with_type': 'Entity'}
                    )
                    fig_bar.update_xaxes(tickangle=45)
                    st.plotly_chart(fig_bar, use_container_width=True)
                else:
                    st.info("📊 No data available for revenue chart")

    # Timeline chart
    st.subheader("License Timeline")
    timeline_df = filtered_df.copy()
    timeline_df['duration_days'] = (pd.to_datetime(timeline_df['end_date']) - pd.to_datetime(timeline_df['start_date'])).dt.days

    fig_timeline = px.timeline(
        timeline_df,
        x_start='start_date',
        x_end='end_date',
        y='entity_with_type',
        color='status',
        title="License Duration by Entity",
        hover_data=['number_of_licenses', 'user_count', 'active_users', 'total_cost', 'cost_per_license']
    )
    fig_timeline.update_yaxes(categoryorder="total ascending")
    st.plotly_chart(fig_timeline, use_container_width=True)

    # License utilization analysis
    if st.session_state.selected_dashboard == 'Relay Licenses':
        st.subheader("🔗 Relay Utilization Analysis")
    elif st.session_state.selected_dashboard == 'User Licenses':
        st.subheader("👥 User License Utilization Analysis")
    else:
        st.subheader("License Utilization Analysis")
    
    col1, col2 = st.columns(2)

    with col1:
        # Calculate utilization ratio based on active users or active relay devices
        utilization_df = filtered_df.copy()
        
        if st.session_state.selected_dashboard == 'Relay Licenses':
            # For Relay licenses, use active relay devices
            utilization_df['active_utilization_ratio'] = (utilization_df['active_relay_devices'] / utilization_df['number_of_licenses']).round(2)
        else:
            # For User licenses and All licenses, use active users
            utilization_df['active_utilization_ratio'] = (utilization_df['active_users'] / utilization_df['number_of_licenses']).round(2)
        
        utilization_df['utilization_status'] = utilization_df['active_utilization_ratio'].apply(
            lambda x: 'Over-utilized' if x > 1.0 else 'Under-utilized' if x < 0.7 else 'Well-utilized'
        )
        
        utilization_summary = utilization_df['utilization_status'].value_counts().reset_index()
        utilization_summary.columns = ['status', 'count']
        
        # Update title based on dashboard type
        if st.session_state.selected_dashboard == 'Relay Licenses':
            title = "Active Relay Device Utilization Status"
        else:
            title = "Active License Utilization Status"
        
        fig_util = px.pie(
            utilization_summary,
            values='count',
            names='status',
            title=title,
            color_discrete_map={
                'Well-utilized': '#2E8B57',
                'Under-utilized': '#FFD700', 
                'Over-utilized': '#DC143C'
            }
        )
        st.plotly_chart(fig_util, use_container_width=True)

    with col2:
        # User vs License comparison chart (or Relay Device vs License for Relay dashboard)
        if st.session_state.selected_dashboard == 'Relay Licenses':
            # For Relay licenses, show relay devices vs licenses
            company_util = utilization_df.groupby('entity_with_type').agg({
                'active_relay_devices': 'sum',
                'number_of_licenses': 'sum'
            }).reset_index()
            
            # Show top 10 entities by relay device count
            top_user_companies = company_util.nlargest(10, 'active_relay_devices')
            chart_title = "Relay License Usage vs Active Devices by Entity"
            y_axis_title = "Count"
        else:
            # For User licenses and All licenses, show users vs licenses
            company_util = utilization_df.groupby('entity_with_type').agg({
                'user_count': 'sum',
                'active_users': 'sum',
                'number_of_licenses': 'sum'
            }).reset_index()
            
            # Show top 10 entities by total user count
            top_user_companies = company_util.nlargest(10, 'user_count')
            chart_title = "License Usage vs User Count by Entity"
            y_axis_title = "Count"
        
        if not top_user_companies.empty:
            # Create grouped bar chart using plotly.graph_objects
            fig_grouped = go.Figure()
            
            # Add licences bar (baseline)
            fig_grouped.add_trace(go.Bar(
                name='Licences Available',
                x=top_user_companies['entity_with_type'],
                y=top_user_companies['number_of_licenses'],
                marker_color='#87CEEB',  # Light blue for licences
                hovertemplate='<b>%{x}</b><br>Licences: %{y}<extra></extra>',
                opacity=0.8
            ))
            
            if st.session_state.selected_dashboard == 'Relay Licenses':
                # Add active relay devices bar with conditional coloring
                relay_device_colors = []
                for _, row in top_user_companies.iterrows():
                    if row['active_relay_devices'] > row['number_of_licenses']:
                        relay_device_colors.append('#DC143C')  # Red if exceeding licences
                    else:
                        relay_device_colors.append('#2E8B57')  # Green if within limits
                
                fig_grouped.add_trace(go.Bar(
                    name='Active Relay Devices',
                    x=top_user_companies['entity_with_type'],
                    y=top_user_companies['active_relay_devices'],
                    marker_color=relay_device_colors,
                    hovertemplate='<b>%{x}</b><br>Active Relay Devices: %{y}<extra></extra>',
                    opacity=0.9
                ))
                
                # Add annotations for entities exceeding licences
                for i, row in top_user_companies.iterrows():
                    if row['active_relay_devices'] > row['number_of_licenses']:
                        fig_grouped.add_annotation(
                            x=row['entity_with_type'],
                            y=row['active_relay_devices'] + 5,
                            text="⚠️ OVER LIMIT",
                            showarrow=True,
                            arrowhead=2,
                            arrowsize=1,
                            arrowwidth=2,
                            arrowcolor="red",
                            font=dict(color="red", size=10, family="Arial Black"),
                            bgcolor="rgba(255,255,255,0.8)",
                            bordercolor="red",
                            borderwidth=1
                        )
                
                # Add summary alert for over-limit entities
                over_limit_companies = top_user_companies[top_user_companies['active_relay_devices'] > top_user_companies['number_of_licenses']]
                if not over_limit_companies.empty:
                    st.error("🚨 **RELAY LICENSE LIMIT EXCEEDED** 🚨")
                    for _, company in over_limit_companies.iterrows():
                        excess = company['active_relay_devices'] - company['number_of_licenses']
                        st.error(f"**{company['entity_with_type']}**: {company['active_relay_devices']} active devices vs {company['number_of_licenses']} licenses (⚠️ {excess} over limit)")
            else:
                # Add total users bar with conditional coloring
                total_user_colors = []
                for _, row in top_user_companies.iterrows():
                    if row['user_count'] > row['number_of_licenses']:
                        total_user_colors.append('#DC143C')  # Red if exceeding licences
                    else:
                        total_user_colors.append('#FFD700')  # Yellow if within limits
                
                fig_grouped.add_trace(go.Bar(
                    name='Total Users',
                    x=top_user_companies['entity_with_type'],
                    y=top_user_companies['user_count'],
                    marker_color=total_user_colors,
                    hovertemplate='<b>%{x}</b><br>Total Users: %{y}<extra></extra>',
                    opacity=0.9
                ))
                
                # Add active users bar
                fig_grouped.add_trace(go.Bar(
                    name='Active Users',
                    x=top_user_companies['entity_with_type'],
                    y=top_user_companies['active_users'],
                    marker_color='#2E8B57',  # Green for active users
                    hovertemplate='<b>%{x}</b><br>Active Users: %{y}<extra></extra>'
                ))
                
                # Add annotations for entities exceeding licences
                for i, row in top_user_companies.iterrows():
                    if row['user_count'] > row['number_of_licenses']:
                        fig_grouped.add_annotation(
                            x=row['entity_with_type'],
                            y=row['user_count'] + 5,
                            text="⚠️ OVER LIMIT",
                            showarrow=True,
                            arrowhead=2,
                            arrowsize=1,
                            arrowwidth=2,
                            arrowcolor="red",
                            font=dict(color="red", size=10, family="Arial Black"),
                            bgcolor="rgba(255,255,255,0.8)",
                            bordercolor="red",
                            borderwidth=1
                        )
                
                # Add summary alert for over-limit entities
                over_limit_companies = top_user_companies[top_user_companies['user_count'] > top_user_companies['number_of_licenses']]
                if not over_limit_companies.empty:
                    st.error("🚨 **LICENSE LIMIT EXCEEDED** 🚨")
                    for _, company in over_limit_companies.iterrows():
                        excess = company['user_count'] - company['number_of_licenses']
                        st.error(f"**{company['entity_with_type']}**: {company['user_count']} users vs {company['number_of_licenses']} licences (⚠️ {excess} over limit)")
            
            # Update layout for grouped bars
            fig_grouped.update_layout(
                title=chart_title,
                xaxis_title="Entity",
                yaxis_title=y_axis_title,
                barmode='group',
                hovermode='closest',
                xaxis={'tickangle': 45},
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            
            st.plotly_chart(fig_grouped, use_container_width=True)
            
        else:
            st.info("📊 No data available for user activity chart")

else:
    st.info("📊 No data available for charts. Add some license records to see visualizations.")

# Key Insights & Alerts Section
if not filtered_df.empty:
    st.markdown("---")
    st.subheader("💡 Key Insights & Alerts")
    
    # Create columns for insights
    col1, col2 = st.columns(2)
    
    with col1:
        # Check for over-utilization
        if st.session_state.selected_dashboard == 'Relay Licenses':
            over_limit = filtered_df[filtered_df['active_relay_devices'] > filtered_df['number_of_licenses']]
            if not over_limit.empty:
                st.warning("⚠️ **Relay License Over-Utilization**")
                for _, row in over_limit.iterrows():
                    excess = row['active_relay_devices'] - row['number_of_licenses']
                    st.write(f"• **{row['entity']}**: {excess} devices over limit")
            else:
                st.success("✅ All relay licenses within limits")
        else:
            over_limit = filtered_df[filtered_df['user_count'] > filtered_df['number_of_licenses']]
            if not over_limit.empty:
                st.warning("⚠️ **User License Over-Utilization**")
                for _, row in over_limit.iterrows():
                    excess = row['user_count'] - row['number_of_licenses']
                    st.write(f"• **{row['entity']}**: {excess} users over limit")
            else:
                st.success("✅ All user licenses within limits")
        
        # Expiring licenses warning
        expiring_soon = filtered_df[
            (filtered_df['status'] == 'Active') & 
            (filtered_df['end_date'] <= datetime.now().date() + timedelta(days=30))
        ]
        if not expiring_soon.empty:
            st.warning("⚠️ **Licenses Expiring Soon** (30 days)")
            for _, row in expiring_soon.iterrows():
                days_left = (row['end_date'] - datetime.now().date()).days
                st.write(f"• **{row['entity']}**: {days_left} days left")
    
    with col2:
        # Top performers
        if st.session_state.selected_dashboard == 'Relay Licenses':
            top_performers = filtered_df.nlargest(3, 'active_relay_devices')
            if not top_performers.empty:
                st.info("🏆 **Top Relay Device Users**")
                for _, row in top_performers.iterrows():
                    utilization = (row['active_relay_devices'] / row['number_of_licenses'] * 100) if row['number_of_licenses'] > 0 else 0
                    st.write(f"• **{row['entity']}**: {utilization:.1f}% utilization")
        else:
            top_performers = filtered_df.nlargest(3, 'active_users')
            if not top_performers.empty:
                st.info("🏆 **Top Active Organizations**")
                for _, row in top_performers.iterrows():
                    utilization = (row['active_users'] / row['number_of_licenses'] * 100) if row['number_of_licenses'] > 0 else 0
                    st.write(f"• **{row['entity']}**: {utilization:.1f}% utilization")
        
        # Quick stats
        if not filtered_df.empty:
            total_entities = len(filtered_df['entity'].unique())
            active_licenses = filtered_df[filtered_df['status'] == 'Active']['number_of_licenses'].sum()
            st.info(f"📊 **Quick Stats**")
            st.write(f"• **{total_entities}** entities")
            st.write(f"• **{active_licenses:,}** active licenses")
            if 'currency' in filtered_df.columns:
                currencies = len(filtered_df['currency'].unique())
                st.write(f"• **{currencies}** currencies")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    <p>📊 License Management Dashboard | Built with Streamlit | Data from Live Database</p>
    <p>Last updated: {}</p>
</div>
""".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), unsafe_allow_html=True) 