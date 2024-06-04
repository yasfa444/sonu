from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
import threading

load_dotenv()  # Load environment variables from .env file

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with your actual secret key

# Load email configuration from environment variables
EMAIL_ADDRESS = os.getenv('EMAIL_USER')
EMAIL_PASSWORD = os.getenv('EMAIL_PASS')

progress = {
    "sent": 0,
    "failed": 0,
    "total": 0
}
email_thread = None
cancel_event = threading.Event()

def send_email(to_email, subject, message, send_as_html=False):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = to_email
    msg['Subject'] = subject

    if send_as_html:
        msg.attach(MIMEText(message, 'html'))
    else:
        msg.attach(MIMEText(message, 'plain'))

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())

def send_emails_thread(to_emails, subject, message, send_as_html):
    global progress
    progress["total"] = len(to_emails)
    progress["sent"] = 0
    progress["failed"] = 0
    for index, email in enumerate(to_emails):
        if cancel_event.is_set():
            break
        try:
            send_email(email, subject, message, send_as_html)
            progress["sent"] += 1
        except Exception as e:
            app.logger.error(f'Failed to send email to {email}: {str(e)}')
            progress["failed"] += 1

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/send_email', methods=['POST'])
def send_email_route():
    global email_thread, cancel_event

    to_emails = [email.strip() for email in request.form['to_emails'].split(',')]
    subject = request.form['subject']
    message = request.form['message']
    send_as_html = 'html_checkbox' in request.form

    cancel_event.clear()
    email_thread = threading.Thread(target=send_emails_thread, args=(to_emails, subject, message, send_as_html))
    email_thread.start()

    return jsonify({"status": "Email sending started."}), 200

@app.route('/progress', methods=['GET'])
def progress_route():
    return jsonify(progress)

@app.route('/cancel', methods=['POST'])
def cancel_route():
    global cancel_event
    cancel_event.set()
    return jsonify({"status": "Email sending cancelled."}), 200

@app.route('/save_credentials', methods=['POST'])
def save_credentials_route():
    email_user = request.form['email_user']
    email_pass = request.form['email_pass']

    with open('.env', 'w') as env_file:
        env_file.write(f"EMAIL_USER='{email_user}'\n")
        env_file.write(f"EMAIL_PASS='{email_pass}'\n")

    # Update the loaded environment variables
    global EMAIL_ADDRESS, EMAIL_PASSWORD
    EMAIL_ADDRESS = email_user
    EMAIL_PASSWORD = email_pass

    return jsonify({"status": "Credentials saved successfully."}), 200

if __name__ == "__main__":
    app.run(debug=True)
