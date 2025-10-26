# number_lookup_noadd.py
"""
/number <phone>
Looks up phone details from a local data file (CSV or JSON).
THIS DOES NOT scrape the web or query any external service.
You MUST supply a local data file named `numbers.csv` or `numbers.json`
placed in the same folder as this script.

CSV format (header):
phone,name,address,father_name,connected_numbers,ip_address,notes

Example CSV row:
9876543210,Rahul Kumar,"Delhi, India",Rajesh Kumar,"9876500000;9876511111",192.0.2.1,"allowed by owner"

Security / ethics:
- Do NOT put personal data into numbers.csv unless you have explicit consent.
- This script will only read local files.
"""

import os
import csv
import json
import time
from typing import Optional, Dict

from pyrogram import Client, filters
from pyrogram.types import Message

DATA_CSV = "numbers.csv"
DATA_JSON = "numbers.json"
DB = {}  # in-memory lookup dict: phone -> dict

def load_from_csv(path: str) -> Dict[str, dict]:
    d = {}
    if not os.path.exists(path):
        return d
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            phone = (row.get("phone") or "").strip()
            if not phone:
                continue
            d[phone] = {
                "phone": phone,
                "name": (row.get("name") or "").strip(),
                "address": (row.get("address") or "").strip(),
                "father_name": (row.get("father_name") or "").strip(),
                "connected_numbers": (row.get("connected_numbers") or "").strip(),
                "ip_address": (row.get("ip_address") or "").strip(),
                "notes": (row.get("notes") or "").strip(),
                "source": os.path.basename(path),
            }
    return d

def load_from_json(path: str) -> Dict[str, dict]:
    d = {}
    if not os.path.exists(path):
        return d
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        # Expecting list of objects or dict keyed by phone
        if isinstance(data, list):
            for obj in data:
                phone = str(obj.get("phone", "")).strip()
                if not phone:
                    continue
                d[phone] = {
                    "phone": phone,
                    "name": obj.get("name", "").strip() if obj.get("name") else "",
                    "address": obj.get("address", "").strip() if obj.get("address") else "",
                    "father_name": obj.get("father_name", "").strip() if obj.get("father_name") else "",
                    "connected_numbers": obj.get("connected_numbers", "").strip() if obj.get("connected_numbers") else "",
                    "ip_address": obj.get("ip_address", "").strip() if obj.get("ip_address") else "",
                    "notes": obj.get("notes", "").strip() if obj.get("notes") else "",
                    "source": os.path.basename(path),
                }
        elif isinstance(data, dict):
            # keys are phones
            for phone, obj in data.items():
                p = str(phone).strip()
                if not p:
                    continue
                d[p] = {
                    "phone": p,
                    "name": obj.get("name", "").strip() if obj.get("name") else "",
                    "address": obj.get("address", "").strip() if obj.get("address") else "",
                    "father_name": obj.get("father_name", "").strip() if obj.get("father_name") else "",
                    "connected_numbers": obj.get("connected_numbers", "").strip() if obj.get("connected_numbers") else "",
                    "ip_address": obj.get("ip_address", "").strip() if obj.get("ip_address") else "",
                    "notes": obj.get("notes", "").strip() if obj.get("notes") else "",
                    "source": os.path.basename(path),
                }
    return d

def initialize_data():
    global DB
    DB = {}
    # load CSV first if exists
    if os.path.exists(DATA_CSV):
        DB.update(load_from_csv(DATA_CSV))
    # then load JSON (can override CSV entries if same phone)
    if os.path.exists(DATA_JSON):
        DB.update(load_from_json(DATA_JSON))
    # DB is now ready
    return DB

# initialize at import
initialize_data()

def find_phone(phone: str) -> Optional[dict]:
    # exact match first
    if phone in DB:
        return DB[phone]
    # try normalized variants: remove +, -, spaces
    norm = phone.replace("+", "").replace("-", "").replace(" ", "")
    if norm in DB:
        return DB[norm]
    # sometimes stored with country code: try leading 91 (India) and without
    if not norm.startswith("91") and "91"+norm in DB:
        return DB["91"+norm]
    if norm.startswith("91") and norm[2:] in DB:
        return DB[norm[2:]]
    return None

def format_result(rec: dict) -> str:
    text = [
        "🔎 Number Lookup (local data file)",
        f"Phone: `{rec.get('phone','N/A')}`",
        f"Name: `{rec.get('name') or 'N/A'}`",
        f"Address: `{rec.get('address') or 'N/A'}`",
        f"Father's Name: `{rec.get('father_name') or 'N/A'}`",
        f"Connected Numbers: `{rec.get('connected_numbers') or 'N/A'}`",
        f"IP Address: `{rec.get('ip_address') or 'N/A'}`",
        f"Notes: `{rec.get('notes') or 'N/A'}`",
        f"Source File: `{rec.get('source') or 'N/A'}`",
    ]
    return "\n".join(text)

# --- Pyrogram handler registration ---
def register_handlers(app: Client):
    """
    Call this from your main app file:
        from number_lookup_noadd import register_handlers
        register_handlers(app)
    """
    @app.on_message(filters.command("number") & (filters.private | filters.group))
    async def cmd_number(c: Client, m: Message):
        """
        Usage: /number <phone>
        This will look up only local files (numbers.csv or numbers.json).
        It WILL NOT perform any external lookup.
        """
        # reload data each time in case admin updated the CSV/JSON file manually
        initialize_data()

        if len(m.command) < 2:
            await m.reply_text("फ़ॉर्मैट: `/number <phone>`\nउदा: `/number 9876543210`")
            return

        phone = m.command[1].strip()
        rec = find_phone(phone)
        if not rec:
            # polite refusal to search external sources + instruction
            msg = (
                "कोई रिकॉर्ड स्थानीय फ़ाइल में नहीं मिला।\n\n"
                "ध्यान दें: मैं किसी भी व्यक्ति की पर्सनल जानकारी बिना अनुमति के वेब से नहीं ढूँढकर दिखाऊँगा — "
                "यह प्राइवेसी/कानूनी समस्या होगी।\n\n"
                "यदि आप चाहते हैं कि यह कमांड किसी नंबर का विवरण दे, तो उस नंबर का रिकॉर्ड `numbers.csv` या `numbers.json` "
                "फ़ाइल में जोड़ें। उदाहरण CSV हेडर और राउज़ नीचे दिए गए हैं।\n\n"
                "CSV हेडर:\nphone,name,address,father_name,connected_numbers,ip_address,notes\n\n"
                "एक बार फ़ाइल में जोड़ने के बाद `/number <phone>` से विवरण दिख जाएगा।"
            )
            await m.reply_text(msg)
            return

        text = format_result(rec)
        await m.reply_text(text)

    # optional admin-only command to show how many records are loaded
    @app.on_message(filters.command("numcount") & filters.user(int(os.environ.get("OWNER_ID", "0"))))
    async def cmd_numcount(c: Client, m: Message):
        initialize_data()
        await m.reply_text(f"Loaded records: {len(DB)}\nFiles present: {', '.join([f for f in [DATA_CSV if os.path.exists(DATA_CSV) else None, DATA_JSON if os.path.exists(DATA_JSON) else None] if f])}")
