# License Management System

A generic, open-source license tracking dashboard built with Streamlit for organizations managing software licenses and user access.

## Features

### 📊 **Dashboard & Analytics**
- Real-time license utilization tracking
- User activity monitoring (configurable time window)
- Multi-currency revenue tracking
- Visual charts and metrics
- License compliance analytics

### 🏢 **Multi-Entity Support**
- Organization license management
- Partner/reseller tracking
- Flexible entity selection

### ✏️ **License Management**
- Create and edit license records
- Bulk CSV import functionality
- Status tracking and lifecycle management
- Cost and revenue tracking

### 👥 **User & Activity Tracking**
- User count per organization
- Activity-based user detection
- Utilization ratio calculations
- Compliance monitoring

### 🔐 **Security & Access Control**
- Role-based permissions
- Secure database connections
- Environment-based configuration

## Tech Stack

- **Frontend**: Streamlit
- **Backend**: Python 3.12+
- **Database**: MySQL with SQLAlchemy ORM
- **Visualization**: Plotly
- **Authentication**: Built-in auth system

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
- `fido1.app_log` - Activity tracking data (recently updated from logger_sessions)

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

## Recent Changes

### Active User Tracking Update (Latest)
- **Changed from**: `logger_sessions` table (deployed_by/collected_by fields)
- **Changed to**: `fido1.app_log` table (user_id field)
- **Definition**: A user is considered active if they have any record in the `fido1.app_log` table within the last 14 days
- **Benefits**: More accurate user activity tracking based on actual application usage

### App Log Schema
The `fido1.app_log` table contains:
- `user_id` - User identifier
- `timestamp` - Activity timestamp
- `action` - User action performed
- `status` - Action status
- Additional fields for detailed tracking

## Support

For issues or questions, please contact the development team. 