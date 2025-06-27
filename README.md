# License Counting Dashboard

A comprehensive Streamlit-based dashboard for tracking and managing software licenses, user counts, and utilization metrics.

## Features

### 📊 **Dashboard & Analytics**
- Real-time license utilization tracking
- Active user monitoring (14-day activity window)
- Revenue tracking across multiple currencies
- Visual charts and metrics
- License vs. user comparison analytics

### 🏢 **Multi-Entity Support**
- Company license management
- Partner license tracking
- Unified entity selection interface

### ✏️ **License Management**
- Add new licenses with comprehensive details
- Edit existing license records
- Bulk CSV import functionality
- Status tracking (Active/Expired)

### 👥 **User & Activity Tracking**
- Total user count per company
- Active user detection based on system activity
- Utilization ratio calculations
- License compliance monitoring

### 🔐 **Security & Access Control**
- Role-based permissions (view/edit)
- Secure database connections
- Environment-based configuration

## Tech Stack

- **Frontend**: Streamlit
- **Backend**: Python 3.12+
- **Database**: MySQL with SQLAlchemy ORM
- **Charts**: Plotly
- **Authentication**: Custom auth manager

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd licence_counting
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Setup**
   Create a `.env` file with your database credentials:
   ```env
   DB_HOST=your_mysql_host
   DB_USER=your_mysql_user
   DB_PASSWORD=your_mysql_password
   DB_NAME=your_database_name
   ```

5. **Run the application**
   ```bash
   streamlit run app.py
   ```

## Database Schema

The application expects the following database tables:
- `license_records` - Main license data
- `companies` - Company information
- `partners` - Partner information
- `license_product_codes` - Product type definitions
- `users_portal` - User account data
- `logger_sessions` - Activity tracking data

## Usage

### Quick Actions (Sidebar)
- **Add License**: Create new license records
- **Import CSV**: Bulk import licenses from CSV file
- **Refresh**: Update data and clear cache

### Filtering
- Date range selection
- Company/partner filtering
- License status filtering
- Currency filtering

### Editing
- Click any cell in the data table to edit
- Save changes to update the database
- Real-time validation and error handling

### Analytics
- **License vs Active Users**: Scatter plot showing utilization
- **Revenue by Currency**: Bar chart of revenue breakdown
- **License Timeline**: Gantt chart of license periods
- **Utilization Tracking**: Visual indicators for over-licensed companies

## Key Metrics

- **Total Licenses**: Sum of all license counts
- **Total Users**: Registered users across all companies
- **Active Users**: Users with activity in last 14 days
- **Total Revenue**: Revenue totals by currency
- **Active Licenses**: Currently active license count
- **Average Cost/License**: Mean cost per license

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is proprietary software for internal use.

## Support

For issues or questions, please contact the development team. 