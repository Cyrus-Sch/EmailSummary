import app
import psycopg2
import os
import json
def run_script():
    DATABASE_URL = os.environ['DATABASE_URL']
    # Connect to the PostgreSQL database
    con = psycopg2.connect(DATABASE_URL, sslmode='require')
    cur = con.cursor()
    print("Running script...")
    cur.execute("SELECT * FROM user_of_summary_service")
    users = cur.fetchall()
    for user in users:
        # Extract the credentials and user_id from the row
        credentials_json, user_id = user[:2]
        credentials = json.loads(credentials_json)
        app.background_get_summary(credentials, user_id)