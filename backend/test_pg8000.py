import os
import ssl
from sqlalchemy import create_engine

# Need to pass an actual SSLContext to ssl_context instead of boolean if using args,
# but can usually just do `?ssl=true`? Let's see if sqlalchemy translates it.
conn_str_direct = "postgresql+pg8000://postgres:daddywashere%40123@db.lhswtcrtzhmiedhdqrjy.supabase.co:5432/postgres"

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

try:
    engine = create_engine(conn_str_direct, connect_args={"ssl_context": ssl_context})
    with engine.connect() as conn:
        print("PG8000 DIRECT CONNECTION SUCCESSFUL!")
except Exception as e:
    print("PG8000 DIRECT FAILED:", getattr(e, "orig", e))
