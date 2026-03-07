import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()
db_url = "postgresql://postgres:daddywashere%40123@[2406:da1a:6b0:f60a:a808:93e3:a82d:d1db]:5432/postgres?sslmode=require"
print("Trying IPv6 literal...")
try:
    conn = psycopg2.connect(db_url)
    print("CONNECTION SUCCESSFUL!")
    conn.close()
except Exception as e:
    print("CONNECTION FAILED:", e)
