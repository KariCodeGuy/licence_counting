from sqlalchemy import create_engine, Column, Integer, String, Date, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os
import streamlit as st

# Load environment variables
DB_HOST = st.secrets["database"]["host"]
DB_USER = st.secrets["database"]["user"]
DB_PASSWORD = st.secrets["database"]["password"]
DB_NAME = st.secrets["database"]["name"]
DB_PORT = st.secrets["database"].get("port", 3306)

# Create SQLAlchemy engine
engine = create_engine(f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}')

# Create a configured "Session" class
Session = sessionmaker(bind=engine)

# Create a Base class for declarative class definitions
Base = declarative_base()

# Define ORM models
class LicenseRecord(Base):
    __tablename__ = 'license_records'

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey('companies.id'))
    partner_id = Column(Integer, ForeignKey('partners.id'), nullable=True)
    product_code_id = Column(Integer, ForeignKey('license_product_codes.id'))
    start_date = Column(Date)
    end_date = Column(Date)
    number_of_licenses = Column(Integer)
    cost_per_license = Column(Float)
    total_cost = Column(Float)
    currency = Column(String(3))
    status = Column(String(10))

    company = relationship('Company', back_populates='licenses')
    partner = relationship('Partner', back_populates='licenses')
    product_code = relationship('LicenseProductCode', back_populates='licenses')

class Company(Base):
    __tablename__ = 'companies'

    id = Column(Integer, primary_key=True)
    company_name = Column(String(255))
    active = Column(Integer)

    licenses = relationship('LicenseRecord', back_populates='company')

class Partner(Base):
    __tablename__ = 'partners'

    id = Column(Integer, primary_key=True)
    partner_name = Column(String(255))

    licenses = relationship('LicenseRecord', back_populates='partner')

class LicenseProductCode(Base):
    __tablename__ = 'license_product_codes'

    id = Column(Integer, primary_key=True)
    code = Column(String(10))
    label = Column(String(255))

    licenses = relationship('LicenseRecord', back_populates='product_code')

class UserPortal(Base):
    __tablename__ = 'users_portal'

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey('companies.id'))
    active = Column(Integer)

class LoggerSession(Base):
    __tablename__ = 'logger_sessions'

    id = Column(Integer, primary_key=True)
    deployed_by = Column(Integer, ForeignKey('users_portal.id'))
    collected_by = Column(Integer, ForeignKey('users_portal.id'))
    created = Column(Date)
    last_update = Column(Date) 