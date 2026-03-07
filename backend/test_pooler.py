import psycopg2

regions = [
    "aws-0-ap-south-1",   # Mumbai
    "aws-0-ap-southeast-1", # Singapore
    "aws-0-ap-southeast-2", # Sydney
    "aws-0-ap-northeast-1", # Tokyo
    "aws-0-eu-central-1", # Frankfurt
    "aws-0-us-east-1",    # N. Virginia
    "aws-0-us-west-1",    # N. California
    "aws-0-us-west-2",    # Oregon
]

for r in regions:
    host = f"{r}.pooler.supabase.com"
    db_url = f"postgresql://postgres.lhswtcrtzhmiedhdqrjy:daddywashere%40123@{host}:5432/postgres?sslmode=require"
    try:
        conn = psycopg2.connect(db_url)
        print(f"SUCCESS region: {r}")
        conn.close()
        break
    except Exception as e:
        print(f"FAILED {r}: {str(e).strip()}")
