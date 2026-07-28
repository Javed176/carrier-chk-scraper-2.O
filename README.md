🚛 Carrier Lookup App
A Streamlit web app to instantly verify US motor carriers using the CarrierChk API.
Features
🔍 Search by USDOT number, MC number, phone, or email
✅ Real-time authority status verification
🛡️ Insurance coverage details
🚛 Fleet size & driver count
📞 Contact information
⚠️ Risk flagging (new carriers, inactive authority, bad safety ratings)
Deploy on Streamlit Cloud (Free)
Step 1: Push to GitHub
Create a new repository on GitHub
Upload these 3 files:
app.py
requirements.txt
README.md (this file)
Step 2: Connect to Streamlit Cloud
Go to share.streamlit.io
Click "New app"
Select your GitHub repo
Set Main file path to app.py
Click Deploy
That's it! Your app will be live in ~2 minutes.
Local Testing
bash
pip install -r requirements.txt
streamlit run app.py
API
Powered by CarrierChk API.
