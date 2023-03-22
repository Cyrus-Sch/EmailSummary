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
    con.close()
    cur.close()
    for user in users:
        print("Running for: " + user[1])
        # Extract the credentials and user_id from the row
        credentials_json, user_id = user[:2]
        app.background_get_summary(str(credentials_json), user_id)

if __name__ == "__main__":
    run_script()