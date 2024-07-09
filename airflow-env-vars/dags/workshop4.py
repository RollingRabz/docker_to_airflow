import os
from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator
from airflow.utils.dates import days_ago
from datetime import timedelta

import pymysql.cursors
import pandas as pd
import requests


class Config:
    MYSQL_HOST = os.getenv("MYSQL_HOST")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT"))
    MYSQL_USER = os.getenv("MYSQL_USER")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
    MYSQL_DB = os.getenv("MYSQL_DB")
    MYSQL_CHARSET = os.getenv("MYSQL_CHARSET")

# For PythonOperator

def get_data_from_db():
    # Connect to the database
    connection = pymysql.connect(host=Config.MYSQL_HOST,
                                 port=Config.MYSQL_PORT,
                                 user=Config.MYSQL_USER,
                                 password=Config.MYSQL_PASSWORD,
                                 db=Config.MYSQL_DB,
                                 charset=Config.MYSQL_CHARSET,
                                 cursorclass=pymysql.cursors.DictCursor)


    with connection.cursor() as cursor:
        # Read a single record
        sql = "SELECT * from audible_data"
        cursor.execute(sql)
        result = cursor.fetchall()

    audible_data = pd.DataFrame(result)
    audible_data.set_index("Book_ID")

    with connection.cursor() as cursor:
        # query data from table audible_transaction
        cursor.execute("SELECT * FROM audible_transaction;")
        result = cursor.fetchall()  # .fetchall() is to retrieve all data in the database

    audible_transaction = pd.DataFrame(result)
    #Join table
    transaction = audible_transaction.merge(audible_data, how="left", left_on="book_id", right_on="Book_ID")
    transaction.to_csv("/home/airflow/data/transaction.csv", index=False)

    

def get_data_from_api():
    url = ""
    response = requests.get(url)
    result_conversion_rate = response.json()

    conversion_rate = pd.DataFrame.from_dict(result_conversion_rate)
    conversion_rate = conversion_rate.reset_index().rename(columns={"index":"date"})

    conversion_rate['date'] = pd.to_datetime(conversion_rate['date']).dt.date
    conversion_rate.to_csv("/home/airflow/data/conversion_rate_from_api.csv", index=False)


def convert_to_thb():
    transaction = pd.read_csv("/home/airflow/data/transaction.csv")
    conversion_rate = pd.read_csv("/home/airflow/data/conversion_rate_from_api.csv")

    transaction['date'] = transaction['timestamp']
    transaction['date'] = pd.to_datetime(transaction['date']).dt.date
    conversion_rate['date'] = pd.to_datetime(conversion_rate['date']).dt.date
    final_df = transaction.merge(conversion_rate, how="left", left_on="date", right_on="date")
    final_df["Price"] = final_df.apply(lambda x: x["Price"].replace("$",""), axis=1)
    final_df["Price"] = final_df["Price"].astype(float)
    final_df['THBPrice'] = final_df['Price'] * final_df['conversion_rate']
    final_df = final_df.drop("date", axis=1)
    final_df.to_csv("/home/airflow/data/result.csv", index=False)
        


# Default Args

default_args = {
    'owner': 'datath',
    'depends_on_past': False,
    'catchup': False,
    'start_date': days_ago(1),
    'email': ['airflow@example.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Create DAG

dag = DAG(
    'Retail_pipeline',
    default_args=default_args,
    description='Pipeline for ETL online_retail data',
    schedule_interval=timedelta(days=1),
)

# Tasks
t1 = PythonOperator(
    task_id='db_ingest',
    python_callable=get_data_from_db,
    dag=dag,
)

t2 = PythonOperator(
    task_id='api_call',
    python_callable=get_data_from_api,
    dag=dag,
)

t3 = PythonOperator(
    task_id='convert_currency',
    python_callable=convert_to_thb,
    dag=dag,
)

# Dependencies
[t1, t2] >> t3