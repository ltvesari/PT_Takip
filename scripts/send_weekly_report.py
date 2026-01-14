import os
import smtplib
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import json

def get_google_sheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # Load credentials from environment variable
    creds_json = os.environ.get("GCP_SERVICE_ACCOUNT")
    if not creds_json:
        raise ValueError("GCP_SERVICE_ACCOUNT environment variable not found.")
    
    creds_dict = json.loads(creds_json)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

def send_email(subject, body, to_email):
    sender_email = os.environ.get("GMAIL_USER")
    sender_password = os.environ.get("GMAIL_PASSWORD")
    
    if not sender_email or not sender_password:
        raise ValueError("GMAIL_USER or GMAIL_PASSWORD environment variables not found.")

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'html'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, to_email, text)
        print("Email sent successfully!")
        server.quit()
    except Exception as e:
        print(f"Failed to send email: {e}")

def main():
    try:
        client = get_google_sheet_client()
        sheet = client.open("PT_Takip_Sistemi")
        ws_ogrenci = sheet.worksheet("Ogrenciler")
        
        data = ws_ogrenci.get_all_records()
        df = pd.DataFrame(data)
        
        # Ensure numeric balance, handle missing/string values
        df['bakiye'] = pd.to_numeric(df['bakiye'], errors='coerce').fillna(0).astype(int)
        
        # Filter active students
        active_students = df[df['durum'] == 'active']
        
        if active_students.empty:
            print("No active students found.")
            return

        # Build Email Content
        today = datetime.now().strftime("%d.%m.%Y")
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px; }}
                .container {{ background-color: #ffffff; padding: 20px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
                h2 {{ color: #2C3E50; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th, td {{ padding: 12px; border-bottom: 1px solid #ddd; text-align: left; }}
                th {{ background-color: #3498DB; color: white; }}
                tr:hover {{ background-color: #f1f1f1; }}
                .low-balance {{ color: #e74c3c; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>📊 Haftalık PT Öğrenci Raporu</h2>
                <p>Tarih: <b>{today}</b></p>
                <p>İşte aktif öğrencilerinin son durumları:</p>
                
                <table>
                    <tr>
                        <th>Öğrenci Adı</th>
                        <th>Kalan Ders</th>
                        <th>Notlar</th>
                    </tr>
        """
        
        for _, row in active_students.iterrows():
            bakiye = row['bakiye']
            bakiye_class = 'class="low-balance"' if bakiye <= 3 else ''
            notlar = row['notlar'] if row['notlar'] and row['notlar'] != 'nan' else '-'
            
            html_content += f"""
                    <tr>
                        <td>{row['isim']}</td>
                        <td {bakiye_class}>{bakiye}</td>
                        <td>{notlar}</td>
                    </tr>
            """
        
        html_content += """
                </table>
                <br>
                <p style="font-size: 12px; color: #7f8c8d;">Bu rapor GitHub Actions tarafından otomatik oluşturulmuştur.</p>
            </div>
        </body>
        </html>
        """
        
        target_email = "levent.akin.ozel@gmail.com"
        send_email(f"Pazar Raporu - {today}", html_content, target_email)
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
