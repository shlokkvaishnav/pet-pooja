import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()
db_url = os.environ.get('DATABASE_URL')
print("Trying to connect to:", db_url.split('@')[1] if '@' in db_url else db_url)

try:
    conn = psycopg2.connect(db_url)
    print("CONNECTION SUCCESSFUL!")
    conn.close()
except Exception as e:
    print("CONNECTION FAILED:", e)
