from flask import Flask, jsonify, request, render_template_string, render_template
from apscheduler.schedulers.background import BackgroundScheduler
from google_auth_oauthlib.flow import InstalledAppFlow
import json
import email_assistant
import get_gmail
import sqlite3
import datetime
import os
import psycopg2
from google.oauth2 import id_token

app = Flask(__name__)
DATABASE_URL = os.environ['DATABASE_URL']

# Connect to the PostgreSQL database
con = psycopg2.connect(DATABASE_URL, sslmode='require')
cur = con.cursor()

cur.execute("""
    CREATE TABLE IF NOT EXISTS user_of_summary_service (
        user_gmail_credentials TEXT,
        id TEXT PRIMARY KEY,
        email TEXT,
        current_summary TEXT,
        last_created TIMESTAMP
    )
""")
con.commit()

def run_script():
    print("Running script...")
    cur.execute("SELECT * FROM user_of_summary_service")
    users = cur.fetchall()
    for user in users:
        # Extract the credentials and user_id from the row
        credentials_json, user_id = user[:2]
        credentials = json.loads(credentials_json)
        summary = email_assistant.main(credentials,cur,con,user_id)

        print(f"Script finished for user {user_id}.")

scheduler = BackgroundScheduler()
scheduler.add_job(run_script, 'interval', hours=4)
scheduler.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/result/<string:id_>')
def get_result(id_):
    print(id_)
    cur.execute("SELECT current_summary FROM user_of_summary_service WHERE id = %s", (str(id_),))
    row = cur.fetchone()
    if row is None:
        return jsonify(f'Nothing found for id: {id_}'), 404
    else:
        if str(row) == "('No Summary yet come back later',)":
            cur.execute("SELECT user_gmail_credentials FROM user_of_summary_service WHERE id = %s", (str(id_),))
            creds = cur.fetchall()
            print("Creds fetched:")
            for cred in creds:
                print(str(cred))
            #creds_txt = json.loads(creds[0])
            #run_time = datetime.datetime.now() + datetime.timedelta(seconds=10)
            #job_id = f"email_job_{id_}"

            # Check if the job with the same ID already exists
            #existing_job = scheduler.get_job(job_id)
            #if existing_job is None:
                # If it doesn't exist, add the job
                #scheduler.add_job(email_assistant.main, 'date', run_date=run_time, args=(creds_txt, cur, con, id_), id=job_id)
                #print(run_time)
            #else:
                #print("Job already scheduled for this id")
        return jsonify(row), 200

@app.route('/oauth2callback')
def oauth2callback():
    code = request.args.get('code')
    root_url = app.url_for('index', _external=True)
    flow = InstalledAppFlow.from_client_secrets_file(
        'credentials.json',
        get_gmail.SCOPES,
        redirect_uri="https://emailsummary.herokuapp.com/oauth2callback"
    )
    flow.fetch_token(code=code)
    credentials = flow.credentials
    access_token = credentials.token

    # Check if the user ID exists
    cur.execute("SELECT * FROM user_of_summary_service WHERE 'id' = %s", (str(credentials.client_id),))
    row = cur.fetchone()

    if row is None:
        cur.execute("""
            INSERT INTO user_of_summary_service (user_gmail_credentials, id, email, current_summary, last_created)
            VALUES (%s, %s, %s, %s, %s)
        """, (str(credentials.to_json()), str(credentials.client_id), '', 'No Summary yet come back later', None,))
    else:
        cur.execute("UPDATE user_of_summary_service SET user_gmail_credentials = %s WHERE 'id' = %s",
                    (str(credentials.to_json()), str(credentials.client_id),))

    con.commit()

    root_url = app.url_for('index', _external=True)
    return '''
    <html>
      <head>
        <title>Success!</title>
      </head>
      <body>
        <h1>SUCCESS!</h1>
        <p>Your ID: {0}</p>
        <p>Go copy this link for SIRI Shortcuts: {1}/result/{0}</p>
        <h1>Creating a Siri Shortcut for Get Contents of URL</h1>
    <ol>
      <li>Open the Shortcuts app on your iOS device.</li>
      <li>Tap the "+" button in the top right corner to create a new shortcut.</li>
      <li>Tap "Add Action" to add a new action to your shortcut.</li>
      <li>Search for "Get Contents of URL" in the search bar and select it from the list of actions.</li>
      <li>In the "URL" field, enter the URL that you want to retrieve the contents of. You can either type it in manually or use a variable if you want to retrieve a different URL each time you run the shortcut.</li>
      <li>If the URL requires authentication or custom headers, you can specify them in the "Headers" field. To add a header, tap the "+" button next to the field and enter the name and value of the header.</li>
      <li>If you want to save the contents of the URL to a file or variable, you can specify that in the "Save File" or "Save Variable" fields. Otherwise, the contents will be returned as text.</li>
      <li>Tap "Done" to save the "Get Contents of URL" action.</li>
      <li>If you want to add any additional actions to your shortcut, tap "Add Action" and search for the action you want to add. You can also use variables or conditional statements to add more complex logic to your shortcut.</li>
      <li>Once you have added all the necessary actions to your shortcut, tap "Done" to save it.</li>
      <li>To run the shortcut with Siri, you can either say "Hey Siri, run [shortcut name]" or add the shortcut to your Siri Shortcuts widget or Home screen for quick access.</li>
    </ol>
      </body>
    </html>
    '''.format(credentials.client_id, root_url), 200


@app.route('/get_mail_token')
def get_token():
    root_url = app.url_for('index', _external=True)
    auth_url = get_gmail.get_auth_url()
    return render_template_string(f'''
        <!doctype html>
        <html lang="en">
        <head>
            <title>Get Mail Token</title>
            <a href="{auth_url}">Please Click here to validate youre Email</a>
        </head>
        <body onload="openAuthWindow();">
            <h1>Getting mail token...</h1>
        </body>
        </html>
    ''')

if __name__ == '__main__':
    try:
        port = int(os.environ.get('PORT', 5001))
        app.run(port=port, debug=True)
    finally:
        scheduler.shutdown()
