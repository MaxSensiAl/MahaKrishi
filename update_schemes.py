import os
import json
import urllib.request
import xml.etree.ElementTree as ET
import firebase_admin
from firebase_admin import credentials, firestore

# १. गिटहब सीक्रेट से फ़ायरबेस क्रेडेंशियल्स लोड करना (सुरक्षित तरीका)
service_account_env = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
if not service_account_env:
    raise ValueError("त्रुटी: FIREBASE_SERVICE_ACCOUNT पर्यावरण वेरिएबल गिटहब पर सेट नहीं है!")

cred_dict = json.loads(service_account_env)
cred = credentials.Certificate(cred_dict)
firebase_admin.initialize_app(cred)
db = firestore.client()

# २. महाराष्ट्र सरकारी अपडेट की लाइव RSS फीड
FEED_URL = "https://mahasarkar.co.in/feed/"

# ३. कृषि और किसानों से संबंधित कीवर्ड्स की सूची (फिल्टर करने के लिए)
AGRI_KEYWORDS = ["शेतकरी", "विहीर", "सौर", "सोलर", "पीक विमा", "ठिबक", "अनुदान", "कुसुम", "शेततळे", "ट्रॅक्टर", "कर्जमाफी"]

# महाराष्ट्र के जिलों की सूची (क्षेत्रीय वर्गीकरण के लिए)
DISTRICTS = ["Latur", "Beed", "Nanded", "Pune", "Nashik", "Nagpur", "Thane", "Jalgaon", "Amravati", "Akola", "Solapur", "Satara", "Kolhapur"]

def fetch_and_update_schemes():
    try:
        # लाइव XML फीड डाउनलोड करना
        req = urllib.request.Request(FEED_URL, headers={'User-Agent': 'MahaKrishi-App-Scraper'})
        with urllib.request.urlopen(req) as response:
            xml_data = response.read()
        
        # XML डेटा पार्स करना
        root = ET.fromstring(xml_data)
        items = root.findall('.//item')
        
        print(f"लाइव फीड से {len(items)} नए आर्टिकल्स मिले।")
        
        for item in items:
            title = item.find('title').text
            link = item.find('link').text
            pub_date = item.find('pubDate').text
            
            # जांचें कि क्या यह किसानों की योजना से संबंधित है
            is_relevant = any(keyword in title for keyword in AGRI_KEYWORDS)
            
            if is_relevant:
                # जिले की पहचान करना (डिफ़ॉल्ट रूप से "All" यानी पूरे महाराष्ट्र के लिए)
                applicable_districts = ["All"]
                for dist in DISTRICTS:
                    if dist.lower() in title.lower():
                        applicable_districts = [dist]
                        break
                
                # जांचें कि क्या यह योजना पहले से डेटाबेस में है या नहीं (ताकि डुप्लीकेट प्रविष्टियां न हों)
                existing = db.collection("schemes").where("link", "==", link).limit(1).get()
                
                if len(existing) == 0:
                    # फ़ायरबेस फ़ायरस्टोर में लाइव डेटा अपलोड करना
                    db.collection("schemes").add({
                        "title": title,
                        "link": link,
                        "published": pub_date,
                        "applicable_districts": applicable_districts
                    })
                    print(f"✅ डेटाबेस में नई योजना जोडी गई: {title}")
                else:
                    print(f"⏭️ योजना पहले से मौजूद है: {title}")
                    
    except Exception as e:
        print("त्रुटी आई:", str(e))

if __name__ == "__main__":
    fetch_and_update_schemes()
