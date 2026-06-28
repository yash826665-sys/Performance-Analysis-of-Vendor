import pandas as pd
import os
from sqlalchemy import create_engine, text
import logging
import time

logging.basicConfig(
    filename = "logs/ingestion_db.log",
    level = logging.DEBUG,
    format = "%(asctime)s - %(levelname)s - %(message)s",
    filemode = 'a'
)

def create_db_and_engine():
    master_engine = create_engine(
        "mssql+pyodbc://localhost\\SQLEXPRESS/master"
        "?driver=ODBC+Driver+17+for+SQL+Server"
        "&trusted_connection=yes",
        isolation_level="AUTOCOMMIT"
    )

    with master_engine.connect() as conn:
        conn.execute(text("IF DB_ID('inventory') IS NULL CREATE DATABASE inventory"))

    engine = create_engine(
        "mssql+pyodbc://localhost\\SQLEXPRESS/inventory"
        "?driver=ODBC+Driver+17+for+SQL+Server"
        "&trusted_connection=yes"
    )

    return engine

def ingest_db(df, table_name, engine):
    """this function will ingest the DataFrame into database Table"""
    df.to_sql(table_name, con = engine, if_exists = 'replace', index = False)

def load_raw_data(engine):
    """this function will load the CSVs as DataFrame and ingest into db"""
    start = time.time()
    for file in os.listdir('data'):
        if '.csv' in file:
            df = pd.read_csv('data/'+file)
            logging.info(f'Ingesting {file} in db')
            ingest_db(df, file[:-4], engine)
    end = time.time()
    total_time = (end - start)/60
    logging.info('-------------Ingestion Complete-------------')
    logging.info(f'Total Time Taken: {total_time} minutes')

if __name__ == "__main__":
    engine = create_db_and_engine()
    load_raw_data(engine)