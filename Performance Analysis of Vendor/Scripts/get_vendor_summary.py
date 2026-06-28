import pandas as pd
from sqlalchemy import create_engine, text
import logging
import numpy as np

logging.basicConfig(
    filename = "logs/get_vendor_summary.log",
    level = logging.DEBUG,
    format = "%(asctime)s - %(levelname)s - %(message)s",
    filemode = 'a'
)

def create_vendor_summary(conn):
    vendor_sales_summary = pd.read_sql("""WITH FreightSummary AS (
    SELECT 
        VendorNumber, 
        SUM(Freight) AS FreightCost
    FROM vendor_invoice
    GROUP BY VendorNumber
    ), 
    
    PurchaseSummary AS (
        SELECT
            p.VendorNumber,
            p.VendorName,
            p.Brand,
            p.Description,
            p.PurchasePrice,
            pp.Volume,
            pp.Price AS ActualPrice,
            SUM(p.Quantity) AS TotalPurchaseQuantity,
            SUM(p.Dollars) AS TotalPurchaseDollars
        FROM purchases p
        JOIN purchase_prices pp
            ON p.Brand = pp.Brand
        WHERE p.PurchasePrice > 0
        GROUP BY p.VendorNumber, p.VendorName, p.Brand, p.Description, p.PurchasePrice, pp.Volume, pp.Price
    ),
    
    SalesSummary AS (
        SELECT
            VendorNo,
            Brand,
            SUM(SalesDollars) AS TotalSalesDollars,
            SUM(SalesPrice) AS TotalSalesPrice,
            SUM(SalesQuantity) AS TotalSalesQuantity,
            SUM(ExciseTax) AS TotalExciseTax
        FROM sales
        GROUP BY VendorNo, Brand
    )
    
    SELECT
        ps.VendorNumber,
        ps.VendorName,
        ps.Brand,
        ps.Description,
        ps.PurchasePrice,
        ps.ActualPrice,
        ps.Volume,
        ps.TotalPurchaseQuantity,
        ps.TotalPurchaseDollars,
        ss.TotalSalesDollars,
        ss.TotalSalesPrice,
        ss.TotalSalesQuantity,
        ss.TotalExciseTax,
        fs.FreightCost
    FROM PurchaseSummary ps
    LEFT JOIN SalesSummary ss
        ON ps.VendorNumber = ss.VendorNo
        AND ps.Brand = ss.Brand
    LEFT JOIN FreightSummary fs
        ON ps.VendorNumber = fs.VendorNumber
    ORDER BY ps.TotalPurchaseDollars DESC""", conn)

    return vendor_sales_summary

def clean_data(df):
    """this function will clean the data and add four new features"""
    df.fillna(0, inplace=True)
    
    df['VendorName'] = df['VendorName'].str.strip()
    df['Description'] = df['Description'].str.strip()

    df['Volume'] = df['Volume'].astype('float')

    df['GrossProfit'] = (df['TotalSalesDollars'] - (df['TotalSalesQuantity'] * df['PurchasePrice']))
    df['ProfitMargin'] = np.where(df['TotalSalesDollars'] > 0,(df['GrossProfit'] / df['TotalSalesDollars']) * 100, 0)
    df['StockTurnover'] = (df['TotalSalesQuantity'] / df['TotalPurchaseQuantity'])
    df['SalesToPurchaseRatio'] = (df['TotalSalesDollars'] / df['TotalPurchaseDollars'])

    return df

def ingest_db(df, table_name, engine):
    """this function will ingest the DataFrame into database Table"""
    df.to_sql(table_name, con = engine, if_exists = 'replace', index = False)

if __name__ == '__main__':
    engine = create_engine(
    "mssql+pyodbc://localhost\\SQLEXPRESS/inventory"
    "?driver=ODBC+Driver+17+for+SQL+Server"
    "&trusted_connection=yes")

    with engine.connect() as conn:
        logging.info('Creating Vendor Summarry Table....')
        summary_df = create_vendor_summary(conn)
        logging.info(summary_df.head())
    
        logging.info('Cleaning Data....')
        clean_df = clean_data(summary_df)
        logging.info(clean_df.head())
    
        logging.info('Ingesting Data....')
        ingest_db(clean_df, 'vendor_sales_summary', engine)
        logging.info('Completed')