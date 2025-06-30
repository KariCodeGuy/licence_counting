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
    page_icon="📊",
    layout="wide"
)

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

# Dashboard title
dashboard_title = f"📊 {st.session_state.selected_dashboard} Dashboard"
st.title(dashboard_title)
st.markdown("---")

# Sidebar filters
with st.sidebar:
    st.header("🔍 Filters")
    
    # Dashboard Selector
    st.subheader("📊 Dashboard Type")
    dashboard_options = ['All Licenses', 'Relay Licenses', 'User Licenses']
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
    
    # Quick Actions (moved above filters)
    st.subheader("⚡ Quick Actions")
    current_user = auth_manager.get_current_user()
    can_edit = current_user and 'edit' in current_user.get('permissions', [])

    col1, col2 = st.columns(2)
    with col1:
        if can_edit:
            if st.button("➕ Add License", type="primary", use_container_width=True):
                st.session_state.show_add_form = True
        else:
            st.button("➕ Add License", disabled=True, help="Admin access required", use_container_width=True)

    with col2:
        if can_edit:
            if st.button("📥 Import CSV", use_container_width=True):
                st.session_state.show_import = True
        else:
            st.button("📥 Import CSV", disabled=True, help="Admin access required", use_container_width=True)

    if st.button("🔄 Refresh", use_container_width=True):
        load_license_data.clear()
        st.session_state.df_data = None
        st.success("✅ Data refreshed!")
        st.rerun()

    st.markdown("---")
    
    # Filter controls
    if not df.empty:
        # Date range filter - use safe defaults
        default_start = datetime.now().date() - timedelta(days=365)
        default_end = datetime.now().date()

        date_range = st.date_input(
            "Select Date Range",
            value=(default_start, default_end)
        )

        # Company filter - include both companies and partners
        if not df.empty:
            # Create entity column for filtering if it doesn't exist
            if 'entity' not in df.columns:
                df['entity'] = df.apply(lambda row: 
                    row.get('partner', '') if pd.notna(row.get('partner')) and row.get('partner') 
                    else row.get('company', ''), axis=1)
            
            entity_options = sorted(df['entity'].dropna().unique()) if not df.empty else []
            companies = st.multiselect(
                "Companies/Partners",
                options=entity_options,
                default=entity_options,
                help="Filter by companies or partners"
            )

        # Status filter
        status_options = df['status'].unique().tolist() if not df.empty else ['Active', 'Expired']
        status_filter = st.multiselect(
            "Status",
            options=status_options,
            default=status_options
        )

        # Currency filter
        if not df.empty and 'currency' in df.columns:
            currency_options = sorted(df['currency'].dropna().unique())
            currency_filter = st.multiselect(
                "Currency",
                options=currency_options,
                default=currency_options
            )
        else:
            currency_filter = []

        # Product code filter
        if not df.empty and 'product_code' in df.columns:
            product_options = sorted(df['product_code'].dropna().unique())
            product_filter = st.multiselect(
                "Product Code",
                options=product_options,
                default=product_options,
                help="Filter by specific product codes"
            )
        else:
            product_filter = []

# User info and logout
current_user = auth_manager.get_current_user()
if current_user:
    st.sidebar.markdown("---")
    st.sidebar.write(f"👤 **{current_user['display_name']}**")
    st.sidebar.write(f"🔐 {current_user['role'].title()} Access")
    
    if st.sidebar.button("🚪 Logout"):
        auth_manager.logout()

# Show live database indicator
st.sidebar.success("🗄️ Using Live Database")

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

# Key metrics
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    total_licences = filtered_df['number_of_licenses'].sum() if not filtered_df.empty else 0
    st.metric("Total Licences", f"{total_licences:,}")

with col2:
    total_users = int(filtered_df['user_count'].sum()) if not filtered_df.empty else 0
    st.metric("Total Users", f"{total_users:,}", help="Number of users created under a company or partner with a licence")

with col3:
    active_users = int(filtered_df['active_users'].sum()) if not filtered_df.empty else 0
    st.metric("Active Users", f"{active_users:,}", help="Users with activity detected in the last 14 days")

with col4:
    active_licences = filtered_df[filtered_df['status'] == 'Active']['number_of_licenses'].sum() if not filtered_df.empty else 0
    st.metric("Active Licences", f"{active_licences:,}")

with col5:
    # Dashboard-specific metric
    if st.session_state.selected_dashboard == 'Relay Licenses':
        avg_relay_cost = filtered_df['cost_per_license'].mean() if not filtered_df.empty else 0
        st.metric("Avg Relay Cost", f"£{avg_relay_cost:,.0f}", help="Average cost per Relay license")
    elif st.session_state.selected_dashboard == 'User Licenses':
        avg_user_cost = filtered_df['cost_per_license'].mean() if not filtered_df.empty else 0
        st.metric("Avg User Cost", f"£{avg_user_cost:,.0f}", help="Average cost per User license")
    else:
        total_revenue = filtered_df['total_cost'].sum() if not filtered_df.empty else 0
        st.metric("Total Revenue", f"£{total_revenue:,.0f}", help="Total revenue from all licenses")

# Add active relay devices metric in a new row
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    active_relay_devices = int(filtered_df['active_relay_devices'].sum()) if not filtered_df.empty else 0
    st.metric("🔗 Active Relay Devices", f"{active_relay_devices:,}", help="Unique relay devices with activity in the last 14 days")

with col2:
    # Show relay utilization if we have relay licenses
    if st.session_state.selected_dashboard == 'Relay Licenses' and not filtered_df.empty:
        relay_licenses = filtered_df['number_of_licenses'].sum()
        relay_utilization = (active_relay_devices / relay_licenses * 100) if relay_licenses > 0 else 0
        st.metric("🔗 Relay Utilization", f"{relay_utilization:.1f}%", help="Percentage of relay licenses being actively used")
    else:
        st.metric("📊 Dashboard", st.session_state.selected_dashboard, help="Current dashboard view")

with col3:
    # Show total entities
    total_entities = len(filtered_df['entity'].unique()) if not filtered_df.empty else 0
    st.metric("🏢 Total Entities", f"{total_entities:,}", help="Number of companies/partners with licenses")

with col4:
    # Show average utilization across all entities
    if not filtered_df.empty:
        avg_utilization = (filtered_df['active_users'].sum() / filtered_df['number_of_licenses'].sum() * 100) if filtered_df['number_of_licenses'].sum() > 0 else 0
        st.metric("📈 Avg Utilization", f"{avg_utilization:.1f}%", help="Average license utilization across all entities")
    else:
        st.metric("📈 Avg Utilization", "0%", help="Average license utilization across all entities")

with col5:
    # Show currency breakdown if multiple currencies
    if not filtered_df.empty and 'currency' in filtered_df.columns:
        unique_currencies = len(filtered_df['currency'].unique())
        st.metric("💰 Currencies", f"{unique_currencies}", help="Number of different currencies in use")
    else:
        st.metric("💰 Currencies", "1", help="Number of different currencies in use")

st.markdown("---")

# Dashboard-specific information
if st.session_state.selected_dashboard == 'Relay Licenses':
    st.info("🔗 **Relay Licenses Dashboard**: Viewing data for Relay infrastructure licenses. These licenses control the number of Relay instances that can be deployed.")
elif st.session_state.selected_dashboard == 'User Licenses':
    st.info("👥 **User Licenses Dashboard**: Viewing data for user access licenses. These licenses control the number of users who can access the system.")
else:
    st.info("📊 **All Licenses Dashboard**: Viewing data for all license types combined.")

# Data table
st.subheader("License Details")

# Add editing tip
if can_edit:
    st.info("💡 **Tip**: Click any cell to edit, then use the sidebar Quick Actions to add/import licences.")
else:
    st.info("👁️ **View Only**: Contact admin for edit access. Use sidebar Quick Actions when available.")

# Add utilization metrics to the table
display_df = filtered_df.copy()
if not display_df.empty:
    # Ensure entity column exists in display_df
    if 'entity' not in display_df.columns:
        display_df['entity'] = display_df.apply(lambda row: 
            row.get('partner', '') if pd.notna(row.get('partner')) and row.get('partner') 
            else row.get('company', ''), axis=1)
    
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

# Show data table - editable for admins, read-only for viewers
if can_edit:
    # Editable data for admins - show comprehensive columns but make key ones editable (exclude id for space)
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

# Charts section
if not filtered_df.empty:
    # Dashboard-specific charts
    if st.session_state.selected_dashboard == 'Relay Licenses':
        # Relay-specific charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🔗 Relay Deployment Status")
            # Show relay deployment vs licenses
            relay_summary = filtered_df.groupby('entity_with_type').agg({
                'number_of_licenses': 'sum',
                'active_relay_devices': 'sum'  # Use active_relay_devices instead of active_users
            }).reset_index()
            
            if not relay_summary.empty:
                fig_relay = px.bar(
                    relay_summary,
                    x='entity_with_type',
                    y=['number_of_licenses', 'active_relay_devices'],
                    title="Relay Licenses vs Active Devices (Last 14 Days)",
                    barmode='group',
                    labels={'value': 'Count', 'variable': 'Type'}
                )
                fig_relay.update_xaxes(tickangle=45)
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
        # Calculate utilization ratio based on active users
        utilization_df = filtered_df.copy()
        utilization_df['active_utilization_ratio'] = (utilization_df['active_users'] / utilization_df['number_of_licenses']).round(2)
        utilization_df['utilization_status'] = utilization_df['active_utilization_ratio'].apply(
            lambda x: 'Over-utilized' if x > 1.0 else 'Under-utilized' if x < 0.7 else 'Well-utilized'
        )
        
        utilization_summary = utilization_df['utilization_status'].value_counts().reset_index()
        utilization_summary.columns = ['status', 'count']
        
        fig_util = px.pie(
            utilization_summary,
            values='count',
            names='status',
            title="Active License Utilization Status",
            color_discrete_map={
                'Well-utilized': '#2E8B57',
                'Under-utilized': '#FFD700', 
                'Over-utilized': '#DC143C'
            }
        )
        st.plotly_chart(fig_util, use_container_width=True)

    with col2:
        # User vs License comparison chart
        company_util = utilization_df.groupby('entity_with_type').agg({
            'user_count': 'sum',
            'active_users': 'sum',
            'number_of_licenses': 'sum'
        }).reset_index()
        
        # Show top 10 entities by total user count
        top_user_companies = company_util.nlargest(10, 'user_count')
        
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
            
            # Update layout for grouped bars
            fig_grouped.update_layout(
                title="License Usage vs User Count by Entity",
                xaxis_title="Entity",
                yaxis_title="Count",
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
            
            st.plotly_chart(fig_grouped, use_container_width=True)
            
            # Add summary alert for over-limit entities
            over_limit_companies = top_user_companies[top_user_companies['user_count'] > top_user_companies['number_of_licenses']]
            if not over_limit_companies.empty:
                st.error("🚨 **LICENSE LIMIT EXCEEDED** 🚨")
                for _, company in over_limit_companies.iterrows():
                    excess = company['user_count'] - company['number_of_licenses']
                    st.error(f"**{company['entity_with_type']}**: {company['user_count']} users vs {company['number_of_licenses']} licences (⚠️ {excess} over limit)")
            
        else:
            st.info("📊 No data available for user activity chart")

else:
    st.info("📊 No data available for charts. Add some license records to see visualizations.")

# Dashboard-specific summary
if not filtered_df.empty:
    st.markdown("---")
    
    if st.session_state.selected_dashboard == 'Relay Licenses':
        st.subheader("🔗 Relay License Summary")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_relay_licenses = filtered_df['number_of_licenses'].sum()
            st.metric("Total Relay Licenses", f"{total_relay_licenses:,}")
        
        with col2:
            avg_relay_cost = filtered_df['cost_per_license'].mean()
            st.metric("Average Relay Cost", f"£{avg_relay_cost:,.0f}")
        
        with col3:
            active_relay_licenses = filtered_df[filtered_df['status'] == 'Active']['number_of_licenses'].sum()
            st.metric("Active Relay Licenses", f"{active_relay_licenses:,}")
        
        # Add relay device metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_active_devices = filtered_df['active_relay_devices'].sum()
            st.metric("🔗 Active Relay Devices", f"{total_active_devices:,}", help="Devices with activity in last 14 days")
        
        with col2:
            relay_utilization = (total_active_devices / total_relay_licenses * 100) if total_relay_licenses > 0 else 0
            st.metric("🔗 Device Utilization", f"{relay_utilization:.1f}%", help="Percentage of licenses with active devices")
        
        with col3:
            avg_cost_per_device = (filtered_df['total_cost'].sum() / total_active_devices) if total_active_devices > 0 else 0
            st.metric("💰 Cost per Active Device", f"£{avg_cost_per_device:,.0f}", help="Average cost per active relay device")
        
        # Show top relay customers
        if not filtered_df.empty:
            top_relay_customers = filtered_df.groupby('entity_with_type').agg({
                'number_of_licenses': 'sum',
                'active_relay_devices': 'sum'
            }).nlargest(5, 'number_of_licenses')
            
            st.write("**Top 5 Relay Customers:**")
            for entity, data in top_relay_customers.iterrows():
                utilization = (data['active_relay_devices'] / data['number_of_licenses'] * 100) if data['number_of_licenses'] > 0 else 0
                st.write(f"• {entity}: {data['number_of_licenses']:,} licenses ({data['active_relay_devices']:,} active devices - {utilization:.1f}% utilization)")
    
    elif st.session_state.selected_dashboard == 'User Licenses':
        st.subheader("👥 User License Summary")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_user_licenses = filtered_df['number_of_licenses'].sum()
            st.metric("Total User Licenses", f"{total_user_licenses:,}")
        
        with col2:
            total_users = filtered_df['user_count'].sum()
            st.metric("Total Users", f"{total_users:,}")
        
        with col3:
            avg_utilization = (filtered_df['active_users'].sum() / filtered_df['number_of_licenses'].sum() * 100) if filtered_df['number_of_licenses'].sum() > 0 else 0
            st.metric("Average Utilization", f"{avg_utilization:.1f}%")
        
        # Show utilization insights
        if not filtered_df.empty:
            over_utilized = filtered_df[filtered_df['active_users'] > filtered_df['number_of_licenses']]
            under_utilized = filtered_df[filtered_df['active_users'] < filtered_df['number_of_licenses'] * 0.7]
            
            if not over_utilized.empty:
                st.warning(f"⚠️ **{len(over_utilized)} entities** are over-utilizing their user licenses")
            if not under_utilized.empty:
                st.info(f"ℹ️ **{len(under_utilized)} entities** have low user license utilization")
    
    else:
        # All Licenses summary
        st.subheader("📊 Overall License Summary")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_licenses = filtered_df['number_of_licenses'].sum()
            st.metric("Total Licenses", f"{total_licenses:,}")
        
        with col2:
            total_revenue = filtered_df['total_cost'].sum()
            st.metric("Total Revenue", f"£{total_revenue:,.0f}")
        
        with col3:
            active_licenses = filtered_df[filtered_df['status'] == 'Active']['number_of_licenses'].sum()
            st.metric("Active Licenses", f"{active_licenses:,}")
        
        # Show product breakdown
        if 'product_code' in filtered_df.columns:
            product_breakdown = filtered_df.groupby('product_code').agg({
                'number_of_licenses': 'sum',
                'total_cost': 'sum'
            }).reset_index()
            
            if not product_breakdown.empty:
                st.write("**License Breakdown by Product:**")
                for _, row in product_breakdown.iterrows():
                    st.write(f"• {row['product_code']}: {row['number_of_licenses']:,} licenses (£{row['total_cost']:,.0f})") 