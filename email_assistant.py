import os
import time
from datetime import datetime, timedelta
import base64
import requests
import openai
import base64
from google.auth.api_key import Credentials
from google.oauth2 import credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle
import json
import re
import psycopg2


def preprocess_email(email: str) -> str:
    # Remove email signature and other irrelevant sections
    email = re.sub(r'----------------.*', '', email, flags=re.DOTALL)

    # Remove URLs
    email = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', email)

    # Remove newline characters and extra whitespaces
    email = re.sub(r'\n+', ' ', email)
    email = re.sub(r'\s+', ' ', email)

    # Remove special characters (emojis, etc.) if not relevant
    email = re.sub(r'[^\x00-\x7F]+', '', email)

    return email.strip()
def openai_chat_api_call(key, prompt, model):

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
    }
    data = {
        "model": f"{model}",
        "messages": [{"role": "system", "content": "You are a helpful assistant with the Name Dave.Youre Awnsers are as concise as possible."},{"role": "user", "content": f"{prompt}!"}]}
    response = requests.post(url, headers=headers, data=json.dumps(data), timeout=120)
    try:
        txt = response.json()['choices'][0]['message']['content']
    except KeyError:
        txt = "This Mail could'nt Open right!"
    return txt

def get_email_messages(credentials_txt_obj:str, user_id='me'):
    info = json.loads(credentials_txt_obj)
    credential = credentials.Credentials.from_authorized_user_info(info)
    service = build('gmail', 'v1', credentials=credential)
    now = datetime.utcnow()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=0)
    start_of_day_unix = int(start_of_day.timestamp())
    end_of_day_unix = int(end_of_day.timestamp())
    query = f'after:{start_of_day_unix} before:{end_of_day_unix}'
    result = service.users().messages().list(userId=user_id, labelIds=['INBOX'], q=query ).execute()
    messages = result.get('messages', [])
    emails = []
    for msg in messages:
        txt = service.users().messages().get(userId=user_id, id=msg['id'], format='full').execute()
        msg_str = ""
        if ('parts' in txt['payload'] ):
            for part in txt['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    msg_str += base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    emails.append(preprocess_email(msg_str))
                    break
    return emails

def summarize_email_gpt(email, assistant_style=True, max_prompt_tokens=4090):
    import os

    api_key = os.environ.get("API_KEY")
    # Truncate the email content if it exceeds the max_prompt_tokens
    if len(email) > max_prompt_tokens:
        email = email[:max_prompt_tokens]
    model = "gpt-3.5-turbo"
    prompt = f"Summarize the following email.{email}"
    if not assistant_style:
        prompt = f"Summarize the following email:{email}"
    return openai_chat_api_call(api_key, prompt, model)

def summarize_all(email_list, client, styles, max_prompt_tokens=4090):
    import os

    api_key = os.environ.get("API_KEY")
    if len(email_list) < 3:
        print("No summaries!")
        return 1
    # Truncate the email content if it exceeds the max_prompt_tokens
    if len(email_list) > max_prompt_tokens:
        email_list = email_list[:max_prompt_tokens]
    model = "gpt-3.5-turbo"
    prompt = f"""Provide {', '.join(styles)} mailbox summary for {client}.
    Please make useful assumptions about the importance of the emails and group them accordingly.
    Assume that some emails are promotional and not important.
    Keep the summary light and avoid focusing on details but write a fluent text.
    Please write to the reader. For example if the Mail contains: Cyrus Scholten is receving money. Write you will receive money!.
    Email Summaries: {email_list}
    """
    return openai_chat_api_call(api_key, prompt, model)

def test_variety():
    emails = get_email_messages()
    summaries = []
    index = 1
    final_prompt = ""
    for email in emails:
        summaries.append(f"{index}: " + summarize_email_gpt(email))
        print(summaries[index - 1])
        index += 1
    for summarie in summaries:
        final_prompt += summarie + "\n"
    # Write all outputs to a txt file
    with open("../output_summaries.txt", "w") as file:
        # Loop through different combinations of styles and generate summaries
        for n in range(1, len(styles) + 1):
            for style in styles:
                print(f"Prompting {style}")
                summary = summarize_all(final_prompt, "Cyrus Scholten", styles=style)
                file.write(f"Summary with styles {style}:\n{summary}\n")
                file.write("\n")

def main(credentials_txt_obj, user_id):
    DATABASE_URL = os.environ['DATABASE_URL']
    # Connect to the PostgreSQL database
    con = psycopg2.connect(DATABASE_URL, sslmode='require')
    cur = con.cursor()
    print("Fetching Mail...")
    emails = get_email_messages(credentials_txt_obj)
    summaries = []
    index = 1
    final_prompt = ""
    print("Generating Summaries...")
    for email in emails:
        summaries.append(f"{index}: " + summarize_email_gpt(email))
        print(summaries[index - 1])
        index += 1
    for summarie in summaries:
        final_prompt += summarie + "\n"
    # Write all outputs to a txt file
    summary = summarize_all(final_prompt, "Cyrus Scholten", ['news-report', 'personal', 'informative'])
    cur.execute("UPDATE user_of_summary_service SET current_summary = %s WHERE id = %s", (summary, str(user_id),))
    con.commit()
    cur.close()
    con.close()
    return summary

