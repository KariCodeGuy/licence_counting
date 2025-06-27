import pytest
import pandas as pd
from database import DatabaseConnection

@pytest.fixture
def db_connection():
    return DatabaseConnection()


def test_get_user_count_from_portal(db_connection):
    # Test retrieval of user count from the database
    user_count_df = db_connection.get_user_count_from_portal()
    assert not user_count_df.empty, "User count DataFrame should not be empty"
    assert 'entity_name' in user_count_df.columns, "DataFrame should have 'entity_name' column"
    assert 'user_count' in user_count_df.columns, "DataFrame should have 'user_count' column"


def test_merge_user_count():
    # Test merging of user count into the main DataFrame
    main_df = pd.DataFrame({
        'company': ['Company A', 'Company B'],
        'other_data': [123, 456]
    })
    user_count_df = pd.DataFrame({
        'entity_name': ['Company A', 'Company B'],
        'user_count': [10, 20]
    })
    
    merged_df = main_df.merge(user_count_df, left_on='company', right_on='entity_name', how='left')
    assert 'user_count' in merged_df.columns, "Merged DataFrame should have 'user_count' column"
    assert merged_df['user_count'].isnull().sum() == 0, "There should be no NaN values in 'user_count' column"
    assert merged_df['user_count'].tolist() == [10, 20], "User counts should match expected values"


def test_user_count_column_always_exists():
    # Simulate filtered_df with and without user_count
    main_df = pd.DataFrame({'company': ['A', 'B'], 'other': [1, 2]})
    user_count_df = pd.DataFrame({'company_name': ['A'], 'user_count': [5]})

    # Merge as in app.py
    merged = main_df.merge(user_count_df, left_on='company', right_on='company_name', how='left')
    # Simulate the fix
    if 'user_count' not in merged.columns:
        merged['user_count'] = 0
    else:
        merged['user_count'] = merged['user_count'].fillna(0)
    assert 'user_count' in merged.columns
    assert merged['user_count'].tolist() == [5, 0]


def test_active_users_merge():
    # Test merging of active users into the main DataFrame
    main_df = pd.DataFrame({
        'company': ['Company A', 'Company B'],
        'active_users': [0, 0]  # Initial values
    })
    active_users_df = pd.DataFrame({
        'entity_name': ['Company A', 'Company B'],
        'active_users': [5, 3]  # Real active user counts
    })
    
    # Merge as in app.py
    merged_df = main_df.merge(active_users_df, left_on='company', right_on='entity_name', how='left')
    # Apply the fix logic
    if 'active_users_y' in merged_df.columns:
        merged_df['active_users'] = merged_df['active_users_y'].fillna(0)
    elif 'active_users' not in merged_df.columns:
        merged_df['active_users'] = 0
    else:
        merged_df['active_users'] = merged_df['active_users'].fillna(0)
    
    assert 'active_users' in merged_df.columns, "Merged DataFrame should have 'active_users' column"
    assert merged_df['active_users'].tolist() == [5, 3], "Active user counts should match expected values" 