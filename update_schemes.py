import os
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, firestore, messaging

# 1. फ़ायरबेस क्रेडेंशियल्स लोड करना
service_account_env = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
if not service_account_env:
    raise ValueError("FIREBASE_SERVICE_ACCOUNT not set!")

cred_dict = json.loads(service_account_env)
cred = credentials.Certificate(cred_dict)
firebase_admin.initialize_app(cred)
db = firestore.client()

FEED_URL = "https://mahasarkar.co.in/feed/"
AGRI_KEYWORDS = ["शेतकरी", "विहीर", "सौर", "सोलर", "पीक विमा", "ठिबक", "अनुदान", "कुसुम", "शेततळे", "ट्रॅक्टर", "कर्जमाफी"]
DISTRICTS = ["Latur", "Beed", "Nanded", "Pune", "Nashik", "Nagpur", "Thane", "Jalgaon", "Amravati", "Akola", "Solapur", "Satara", "Kolhapur"]

# फ़्री पुश नोटिफिकेशन भेजने का फ़ंक्शन
def send_push_notification(title_text):
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title="MahaKrishi: नवीन योजना अलर्ट! 🌾",
                body=title_text
            ),
            topic="live_updates"
        )
        response = messaging.send(message)
        print("📢 नोटिफिकेशन सफलतापूर्वक भेजा गया:", response)
    except Exception as e:
        print("⚠️ नोटिफिकेशन भेजने में त्रुटि:", str(e))

# 🧹 पुरानी और समाप्त हो चुकी योजनाओं को डेटाबेस से अपने आप डिलीट करने का जुगाड़
def delete_expired_schemes():
    try:
        now = datetime.utcnow()
        # ऐसी योजनाएं खोजना जिनकी एक्सपायरी तारीख अभी के समय से कम हो चुकी है
        expired_docs = db.collection("schemes").where("expireAt", "<", now).get()
        
        for doc in expired_docs:
            title = doc.to_dict().get("title")
            db.collection("schemes").document(doc.id).delete()
            print(f"🗑️ पुरानी योजना समाप्त होने के कारण डिलीट की गई: {title}")
            
    except Exception as e:
        print("⚠️ सफाई के दौरान त्रुटि आई:", str(e))

def fetch_and_update_schemes():
    try:
        req = urllib.request.Request(FEED_URL, headers={'User-Agent': 'MahaKrishi-App-Scraper'})
        with urllib.request.urlopen(req) as response:
            xml_data = response.read()
        
        root = ET.fromstring(xml_data)
        items = root.findall('.//item')
        
        for item in items:
            title = item.find('title').text
            link = item.find('link').text
            pub_date = item.find('pubDate').text
            
            is_relevant = any(keyword in title for keyword in AGRI_KEYWORDS)
            
            if is_relevant:
                applicable_districts = ["All"]
                for dist in DISTRICTS:
                    if dist.lower() in title.lower():
                        applicable_districts = [dist]
                        break
                
                # ऑटो-डिलीट के लिए 30 दिन बाद का समय तय करना
                expire_time = datetime.utcnow() + timedelta(days=30)
                
                existing = db.collection("schemes").where("link", "==", link).limit(1).get()
                
                if len(existing) == 0:
                    db.collection("schemes").add({
                        "title": title,
                        "link": link,
                        "published": pub_date,
                        "applicable_districts": applicable_districts,
                        "expireAt": expire_time
                    })
                    print(f"✅ नई योजना जोड़ी गई: {title}")
                    send_push_notification(title)
                else:
                    doc_id = existing[0].id
                    old_data = existing[0].to_dict()
                    if old_data.get("title") != title:
                        db.collection("schemes").document(doc_id).update({
                            "title": title,
                            "published": pub_date,
                            "expireAt": expire_time
                        })
                        print(f"🔄 योजना अपडेट की गई: {title}")
                        send_push_notification(f"अपडेटेड: {title}")
                
    except Exception as e:
        print("त्रुटी आई:", str(e))

if __name__ == "__main__":
    fetch_and_update_schemes()
    delete_expired_schemes() # हर बार चलने पर पुरानी योजनाओं को डिलीट करेगा
