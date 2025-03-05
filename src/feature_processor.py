import json
import numpy as np
import pandas as pd
from typing import Dict, List
from dateutil import relativedelta


def process_application_features(application_data: pd.DataFrame) -> pd.DataFrame:
    """Processes features from application data to calculate features."""
    cleaned_df = _clean_application_data(application_data)

    claim_frequency = _calculate_claim_frequency(cleaned_df)
    loan_exposure = _calculate_loan_exposure(cleaned_df)
    days_since_last_loan = _calculate_days_since_last_loan(cleaned_df)

    application_score = _combine_application_scores(application_data, claim_frequency, loan_exposure, days_since_last_loan)
    return application_score



def _clean_application_data(application_data: pd.DataFrame) -> pd.DataFrame:
    raw_data = application_data.copy()

    raw_data['jsoned'] = raw_data['contracts'].apply(_process_contract)
    exploded_jsons_df = raw_data.explode('jsoned')

    column_names=['contract_id', 'bank', 'summa', 'loan_summa', 'claim_date', 'claim_id', 'contract_date']    
    for col_name in column_names:
        exploded_jsons_df[col_name] = exploded_jsons_df['jsoned'].apply(lambda x: x.get(col_name) if pd.notnull(x) and isinstance(x, dict) else None)

    pivoted_df = exploded_jsons_df.drop(labels=['contracts', 'jsoned'], axis=1)
    
    cleansed_data = _type_conversions(pivoted_df)

    return cleansed_data

def _process_contract(contract_string: str) -> List[Dict]:
    if pd.isnull(contract_string):
        return []  # Handle NaN values

    try:
        contract_data = json.loads(contract_string)

        if isinstance(contract_data, dict):
            return [contract_data]  # return it as a list of dict, so that explode will work correctly
        elif isinstance(contract_data, list):
            if all(isinstance(item, dict) for item in contract_data):
                return contract_data # already list of dictionaries
            else:
                return None # Handle invalid lists(not all dictionaries)
        else:
            return None # Handle unexpected JSON types
    except json.JSONDecodeError:
        return None # Handle invalid JSON strings
    

def _type_conversions(untyped_data: pd.DataFrame) -> pd.DataFrame:
    untyped_data['application_date'] = pd.to_datetime(untyped_data['application_date'], format='ISO8601', utc=True)
    untyped_data['claim_date'] = pd.to_datetime(untyped_data['claim_date'], format='%d.%m.%Y', utc=True)
    untyped_data['contract_date'] = pd.to_datetime(untyped_data['contract_date'], format='%d.%m.%Y', utc=True)


    # Convert numeric columns to floats
    untyped_data['id'] = untyped_data['id'].astype(float)
    untyped_data['summa'] = pd.to_numeric(untyped_data['summa'], errors='coerce')
    untyped_data['loan_summa'] = pd.to_numeric(untyped_data['loan_summa'], errors='coerce')
    untyped_data['contract_id'] = pd.to_numeric(untyped_data['contract_id'], errors='coerce')

    # Convert other columns to strings
    untyped_data['bank'] = untyped_data['bank'].astype(str)
    untyped_data['claim_id'] = untyped_data['claim_id'].astype(str)

    return untyped_data


def _calculate_claim_frequency(cleaned_df: pd.DataFrame) -> pd.DataFrame:
    claims_df = cleaned_df.copy()
    claims_df['app_date_180'] = claims_df['application_date'].apply(lambda x: x - relativedelta.relativedelta(days=180))

    claims_df = claims_df[claims_df['claim_date'] > claims_df['app_date_180']].groupby('id')['claim_id'].count().reset_index()
    claims_df = claims_df.rename(columns={'claim_id': 'tot_claim_cnt_l180d'})

    return claims_df


def _calculate_loan_exposure(cleaned_df: pd.DataFrame) -> pd.DataFrame:
    bank_mask = (cleaned_df['bank'].notna()) & ~(cleaned_df['bank'] == 'None') & (~cleaned_df['bank'].isin(['LIZ', 'LOM', 'MKO', 'SUG']))
    filtered_loans = cleaned_df[bank_mask & (cleaned_df['contract_date'].notna())]
    loans_sum = filtered_loans.groupby('id')['loan_summa'].sum().reset_index()

    loans_sum = loans_sum.rename(columns={'loan_summa': 'disb_bank_loan_wo_tbc'})
    return loans_sum

def _calculate_days_since_last_loan(cleaned_df: pd.DataFrame) -> pd.DataFrame:
    last_loan_dates = cleaned_df.dropna(subset=['summa', 'contract_date'])
    last_loan_dates = last_loan_dates.groupby(['id', 'application_date'])['contract_date'].max().reset_index()
    last_loan_dates = last_loan_dates.rename(columns={'contract_date': 'last_loan_date'})
    last_loan_dates['day_sinlastloan'] = ((last_loan_dates['application_date'] - last_loan_dates['last_loan_date']) / np.timedelta64(1, 'D')).astype('int64')
    last_loan_dates.drop(['last_loan_date', 'application_date'], axis=1, inplace=True)
    return last_loan_dates

def _combine_application_scores(application_data, claim_frequency, loan_exposure, days_since_last_loan: pd.DataFrame) -> pd.DataFrame:
    final_df = (application_data.
                merge(claim_frequency, on='id', how='left').
                merge(loan_exposure, on='id', how='left').
                merge(days_since_last_loan, on='id', how='left'))
        
    final_df['tot_claim_cnt_l180d'] = final_df['tot_claim_cnt_l180d'].fillna(-3)
    final_df['disb_bank_loan_wo_tbc'] = final_df['disb_bank_loan_wo_tbc'].fillna(-1)
    final_df['day_sinlastloan'] = final_df['day_sinlastloan'].fillna(-1)
    
    return final_df