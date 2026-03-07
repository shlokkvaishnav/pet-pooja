import os
import sys
from sqlalchemy import create_engine, MetaData, text
from database import Base, DATABASE_URL as PG_URL
import urllib.parse
import models

# Use direct connection port 5432 instead of transaction pooler 6543
PG_URL_DIRECT = PG_URL.replace(":6543", ":5432")

# Replace the async format with sync for sqlalchemy if needed, but it's already sync in .env
pg_engine = create_engine(PG_URL_DIRECT)

SQLITE_PATH = os.path.join(os.path.dirname(__file__), "petpooja.db")
SQLITE_URL = f"sqlite:///{SQLITE_PATH}"
sqlite_engine = create_engine(SQLITE_URL)

# Exclude views from creation if needed, but if SQLite creates a table for v_sales, that might be fine.
print("Creating tables in local SQLite...")
# Drop all first to ensure clean state
Base.metadata.drop_all(sqlite_engine)
Base.metadata.create_all(sqlite_engine)

print("Copying data from Supabase to SQLite...")
with pg_engine.connect() as pg_conn:
    with sqlite_engine.connect() as sqlite_conn:
        
        # Disable foreign key checks in SQLite during mass insert
        sqlite_conn.execute(text("PRAGMA foreign_keys = OFF;"))
        
        for table in Base.metadata.sorted_tables:
            is_view = table.info.get("is_view", False)
            print(f"Cloning table/view: {table.name}...")
            
            try:
                # Select all rows
                result = pg_conn.execute(table.select())
                rows = result.fetchall()
                print(f"  Found {len(rows)} records.")
                
                if rows:
                    if is_view:
                        # For views, since it's mapped as a table in SQLite metadata via create_all, 
                        # injecting it as a table is simpler for local unless there's a trigger.
                        # Wait, SQLite may have created a table instead of a view! Let's insert the data to it.
                        pass
                        
                    # Insert into SQLite
                    # Convert rows to dicts
                    insert_data = [row._mapping for row in rows]
                    
                    # Batch insert
                    sqlite_conn.execute(table.insert(), insert_data)
                    sqlite_conn.commit()
            except Exception as e:
                print(f"  Error cloning {table.name}: {e}")
                
        # Re-enable foreign key checks
        sqlite_conn.execute(text("PRAGMA foreign_keys = ON;"))
        sqlite_conn.commit()

print("Database cloning complete! Local SQLite is ready at:", SQLITE_PATH)
