import os
import re
import sqlite3
from datetime import datetime
from typing import List, Optional

import streamlit as st
from openai import OpenAI
from pydantic import BaseModel, Field

# Datei-Parsing
from pypdf import PdfReader
from docx import Document

DB_PATH = "procurement.db"


# -----------------------------
# Commodity Groups (aus deiner Tabelle)
# -----------------------------
COMMODITY_GROUPS = [
    {"id": "001", "category": "General Services", "group": "Accommodation Rentals"},
    {"id": "002", "category": "General Services", "group": "Membership Fees"},
    {"id": "003", "category": "General Services", "group": "Workplace Safety"},
    {"id": "004", "category": "General Services", "group": "Consulting"},
    {"id": "005", "category": "General Services", "group": "Financial Services"},
    {"id": "006", "category": "General Services", "group": "Fleet Management"},
    {"id": "007", "category": "General Services", "group": "Recruitment Services"},
    {"id": "008", "category": "General Services", "group": "Professional Development"},
    {"id": "009", "category": "General Services", "group": "Miscellaneous Services"},
    {"id": "010", "category": "General Services", "group": "Insurance"},
    {"id": "011", "category": "Facility Management", "group": "Electrical Engineering"},
    {"id": "012", "category": "Facility Management", "group": "Facility Management Services"},
    {"id": "013", "category": "Facility Management", "group": "Security"},
    {"id": "014", "category": "Facility Management", "group": "Renovations"},
    {"id": "015", "category": "Facility Management", "group": "Office Equipment"},
    {"id": "016", "category": "Facility Management", "group": "Energy Management"},
    {"id": "017", "category": "Facility Management", "group": "Maintenance"},
    {"id": "018", "category": "Facility Management", "group": "Cafeteria and Kitchenettes"},
    {"id": "019", "category": "Facility Management", "group": "Cleaning"},
    {"id": "020", "category": "Publishing Production", "group": "Audio and Visual Production"},
    {"id": "021", "category": "Publishing Production", "group": "Books/Videos/CDs"},
    {"id": "022", "category": "Publishing Production", "group": "Printing Costs"},
    {"id": "023", "category": "Publishing Production", "group": "Software Development for Publishing"},
    {"id": "024", "category": "Publishing Production", "group": "Material Costs"},
    {"id": "025", "category": "Publishing Production", "group": "Shipping for Production"},
    {"id": "026", "category": "Publishing Production", "group": "Digital Product Development"},
    {"id": "027", "category": "Publishing Production", "group": "Pre-production"},
    {"id": "028", "category": "Publishing Production", "group": "Post-production Costs"},
    {"id": "029", "category": "Information Technology", "group": "Hardware"},
    {"id": "030", "category": "Information Technology", "group": "IT Services"},
    {"id": "031", "category": "Information Technology", "group": "Software"},
    {"id": "032", "category": "Logistics", "group": "Courier, Express, and Postal Services"},
    {"id": "033", "category": "Logistics", "group": "Warehousing and Material Handling"},
    {"id": "034", "category": "Transportation Logistics", "group": "Transportation Logistics"},
    {"id": "035", "category": "Logistics", "group": "Delivery Services"},
    {"id": "036", "category": "Marketing & Advertising", "group": "Advertising"},
    {"id": "037", "category": "Marketing & Advertising", "group": "Outdoor Advertising"},
    {"id": "038", "category": "Marketing & Advertising", "group": "Marketing Agencies"},
    {"id": "039", "category": "Marketing & Advertising", "group": "Direct Mail"},
    {"id": "040", "category": "Marketing & Advertising", "group": "Customer Communication"},
    {"id": "041", "category": "Marketing & Advertising", "group": "Online Marketing"},
    {"id": "042", "category": "Marketing & Advertising", "group": "Events"},
    {"id": "043", "category": "Marketing & Advertising", "group": "Promotional Materials"},
    {"id": "044", "category": "Production", "group": "Warehouse and Operational Equipment"},
    {"id": "045", "category": "Production", "group": "Production Machinery"},
    {"id": "046", "category": "Production", "group": "Spare Parts"},
    {"id": "047", "category": "Production", "group": "Internal Transportation"},
    {"id": "048", "category": "Production", "group": "Production Materials"},
    {"id": "049", "category": "Production", "group": "Consumables"},
    {"id": "050", "category": "Production", "group": "Maintenance and Repairs"},
]

COMMODITY_TEXT = "\n".join([f'{c["id"]} | {c["category"]} | {c["group"]}' for c in COMMODITY_GROUPS])


# -----------------------------
# Utility: API Key säubern
# -----------------------------
def get_clean_openai_key() -> str:
    raw = os.getenv("OPENAI_API_KEY", "")
    if not raw:
        return ""
    k = raw.strip()
    k = k.strip('"').strip("'")
    k = k.strip("“").strip("”")
    k = k.strip('"').strip("“").strip("”").strip()
    return k


# -----------------------------
# DSGVO: Redaction (personenbezogene Daten maskieren)
# -----------------------------
def redact_personal_data(text: str) -> str:
    """
    Heuristische Maskierung typischer personenbezogener Daten.
    Ziel: Datenminimierung, bevor Text an OpenAI geht.
    """
    if not text:
        return ""

    t = text

    # E-Mail
    t = re.sub(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", "[EMAIL]", t, flags=re.IGNORECASE)

    # Telefonnummer (grob)
    t = re.sub(r"\b(\+?\d{1,3}[\s\-]?)?(\(?\d{2,5}\)?[\s\-]?)?\d{3,}[\s\-]?\d{2,}\b", "[PHONE]", t)

    # IBAN (DE + allgemein grob)
    t = re.sub(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b", "[IBAN]", t)

    # BIC (8 oder 11 Zeichen)
    t = re.sub(r"\b[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?\b", "[BIC]", t)

    # Ansprechpartner / Contact Person (einfach)
    t = re.sub(r"(?i)(ansprechpartner|kontakt|bearbeiter)\s*:\s*[^\n\r]{1,60}", r"\1: [PERSON]", t)

    # Adresszeile (sehr grob, optional)
    # t = re.sub(r"\b\d{5}\s+[A-Za-zÄÖÜäöüß\- ]{2,}\b", "[ADDRESS]", t)

    return t


# -----------------------------
# Utility: Text/Nummern normalisieren
# -----------------------------
def normalize_offer_text(t: str) -> str:
    t = t.replace("“", '"').replace("”", '"')
    t = t.replace("\u00A0", " ")
    return t

def parse_de_number_to_float(val) -> Optional[float]:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    if not s:
        return None
    s = s.replace("€", "").replace("EUR", "").replace("Euro", "").strip()
    s = re.sub(r"\s+", "", s)
    if "," in s:
        s = s.replace(".", "")
        s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        return None


# -----------------------------
# Datei → Text (Upload)
# -----------------------------
def extract_text_from_uploaded_file(uploaded_file) -> str:
    if uploaded_file is None:
        return ""

    name = uploaded_file.name.lower()
    data = uploaded_file.getvalue()

    # TXT
    if name.endswith(".txt"):
        try:
            return data.decode("utf-8", errors="ignore")
        except Exception:
            return data.decode("latin-1", errors="ignore")

    # DOCX
    if name.endswith(".docx"):
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        doc = Document(tmp_path)
        text = "\n".join([p.text for p in doc.paragraphs if p.text])
        return text

    # PDF (nur Text-PDFs)
    if name.endswith(".pdf"):
        import io
        reader = PdfReader(io.BytesIO(data))
        pages_text = []
        for p in reader.pages:
            pages_text.append(p.extract_text() or "")
        return "\n".join(pages_text)

    return ""


# -----------------------------
# Extraktion: Angebot → strukturierte Daten
# -----------------------------
class ExtractedOrderLine(BaseModel):
    description: str
    unit_price: float = Field(..., ge=0)
    quantity: float = Field(..., ge=0)
    unit: Optional[str] = None

class ExtractedOffer(BaseModel):
    vendor_name: Optional[str] = None
    vendor_vat_id: Optional[str] = None
    department: Optional[str] = None

    # Requestor Name kommt in Angeboten oft nicht vor → nicht extrahieren
    # Title/Short Description generieren wir separat (siehe unten)

    order_lines: List[ExtractedOrderLine] = []

    positions_net: Optional[float] = None
    shipping_net: Optional[float] = None
    tax_amount: Optional[float] = None
    total_gross: Optional[float] = None

    currency: Optional[str] = "EUR"

def extract_offer_with_openai(offer_text: str) -> ExtractedOffer:
    api_key = get_clean_openai_key()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY ist nicht gesetzt oder leer.")
    client = OpenAI(api_key=api_key)

    offer_text = normalize_offer_text(offer_text)

    system_msg = (
        "Du extrahierst Daten aus einem Lieferanten-Angebot/Rechnungstext (Copy/Paste) für einen Procurement Request.\n"
        "Gib NUR Daten gemäß Schema zurück.\n\n"
        "Sehr wichtig:\n"
        "- Der Text ist oft aus PDF kopiert (Zeilenumbrüche). Bitte robust interpretieren.\n"
        "- total_gross ist die Endsumme/Gesamtbetrag/Endsumme (inkl. Versand & Steuer), NICHT die Positionssumme.\n"
        "- positions_net ist 'Positionen netto' (ohne Versand, ohne Steuer).\n"
        "- shipping_net ist 'Versandkosten netto'.\n"
        "- tax_amount ist die SUMME aller Steuerbeträge (z.B. USt auf Positionen + USt auf Versand).\n"
        "- Zahlen bitte als reine Zahlen (ohne €). Dezimalkomma ist erlaubt.\n"
        "- quantity darf Dezimal sein (z.B. 1,28).\n"
        "- Wenn etwas nicht sicher erkennbar ist: None.\n"
    )

    resp = client.responses.parse(
        model="gpt-4o-2024-08-06",
        input=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": offer_text},
        ],
        text_format=ExtractedOffer,
    )
    return resp.output_parsed


# -----------------------------
# NEU: Title/Short Description generieren (weil im Angebot oft nicht vorhanden)
# -----------------------------
class TitleSuggestion(BaseModel):
    title: str = Field(..., description="Kurzer Titel/Short Description, max. ca. 70 Zeichen")

def generate_title_with_openai(vendor: str, lines: List[dict], department: str = "") -> str:
    api_key = get_clean_openai_key()
    if not api_key:
        # Fallback ohne KI
        first = (lines[0].get("description", "") if lines else "").strip()
        base = first[:50] if first else vendor
        return (base or "Procurement Request").strip()

    client = OpenAI(api_key=api_key)

    # Nur wenig Kontext senden (Datenminimierung)
    short_lines = []
    for l in (lines or [])[:5]:
        short_lines.append(str(l.get("description", "")).strip()[:80])
    lines_text = "; ".join([x for x in short_lines if x])

    user_msg = (
        "Erstelle einen kurzen Titel für einen Procurement Request.\n"
        "Regeln: kurz, verständlich, keine personenbezogenen Daten.\n"
        f"Vendor: {vendor}\n"
        f"Department: {department}\n"
        f"Items: {lines_text}\n"
    )

    resp = client.responses.parse(
        model="gpt-4o-2024-08-06",
        input=[{"role": "user", "content": user_msg}],
        text_format=TitleSuggestion,
    )
    t = (resp.output_parsed.title or "").strip()
    # Safety: begrenzen
    return t[:80] if t else "Procurement Request"


# -----------------------------
# Commodity Group Auswahl (Ausschlusslogik + Zweck)
# -----------------------------
class CommodityPick(BaseModel):
    commodity_group_id: str
    commodity_group_name: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning_short: str

def pick_commodity_group_with_openai(title: str, vendor: str, lines: list[dict]) -> CommodityPick:
    api_key = get_clean_openai_key()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY ist nicht gesetzt oder leer.")
    client = OpenAI(api_key=api_key)

    lines_text = "\n".join(
        [f'- {l.get("description","")} (unit_price={l.get("unit_price")}, qty={l.get("quantity")}, unit={l.get("unit")})'
         for l in lines]
    ) if lines else "- (keine)"

    user_context = (
        f"TITLE: {title}\n"
        f"VENDOR: {vendor}\n"
        f"ORDER_LINES:\n{lines_text}\n\n"
        "Wähle die passendste Commodity Group aus der Liste. Entscheide nach dem ZWECK.\n"
    )

    system_msg = (
        "Du bist Procurement-Experte und klassifizierst Requests in Commodity Groups.\n\n"
        "Regeln:\n"
        "1) Du DARFST NUR eine Commodity Group aus der Liste wählen.\n"
        "2) '019 – Facility Management – Cleaning' NUR wählen bei echter Reinigungsdienstleistung oder Reinigungs-Verbrauchsmaterial.\n"
        "   NICHT wählen bei: Begrünung, Mooswand, Interior-Elemente, Dekoration, Branding, Schilder, Acryl-Logo-Platten.\n"
        "3) Interior / Büro-Ausstattung / feste Elemente: häufig '015 – Office Equipment'.\n"
        "4) Logo/Branding/Promo-Material: häufig '043 – Promotional Materials'.\n"
        "5) reasoning_short: 1 Satz.\n\n"
        "LISTE:\n"
        f"{COMMODITY_TEXT}"
    )

    resp = client.responses.parse(
        model="gpt-4o-2024-08-06",
        input=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_context},
        ],
        text_format=CommodityPick,
    )
    pick = resp.output_parsed

    valid_ids = {c["id"] for c in COMMODITY_GROUPS}
    if pick.commodity_group_id not in valid_ids:
        raise RuntimeError("KI hat eine ungültige Commodity Group ID geliefert (nicht in der Liste).")
    return pick

def simple_commodity_group_guess(title: str, vendor: str, lines: list[dict]) -> tuple[str, str]:
    text = (title + " " + vendor + " " + " ".join([l.get("description", "") for l in lines])).lower()
    if any(k in text for k in ["logo", "acryl", "schild", "wand", "moos", "begrünung", "deko", "decor"]):
        return ("015", "Facility Management – Office Equipment")
    if any(k in text for k in ["license", "licence", "subscription", "adobe", "software"]):
        return ("031", "Information Technology – Software")
    if any(k in text for k in ["laptop", "notebook", "server", "hardware"]):
        return ("029", "Information Technology – Hardware")
    if any(k in text for k in ["consulting", "berater", "beratung"]):
        return ("004", "General Services – Consulting")
    return ("009", "General Services – Miscellaneous Services")


# -----------------------------
# SQLite: Migration + CRUD
# -----------------------------
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def ensure_column(conn: sqlite3.Connection, table: str, col: str, coltype: str):
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    if col not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {coltype}")
        conn.commit()

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        requestor_name TEXT NOT NULL,
        department TEXT NOT NULL,
        title TEXT NOT NULL,
        vendor_name TEXT NOT NULL,
        vendor_vat_id TEXT NOT NULL,
        commodity_group_id TEXT,
        commodity_group_name TEXT,
        total_cost REAL NOT NULL,
        currency TEXT NOT NULL,
        submit_status TEXT NOT NULL,
        process_status TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    ensure_column(conn, "requests", "positions_net", "REAL")
    ensure_column(conn, "requests", "shipping_net", "REAL")
    ensure_column(conn, "requests", "tax_amount", "REAL")
    ensure_column(conn, "requests", "total_is_gross", "TEXT")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS order_lines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id INTEGER NOT NULL,
        description TEXT NOT NULL,
        unit_price REAL NOT NULL,
        quantity REAL NOT NULL,
        unit TEXT,
        line_total REAL NOT NULL,
        FOREIGN KEY(request_id) REFERENCES requests(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS status_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id INTEGER NOT NULL,
        old_status TEXT,
        new_status TEXT NOT NULL,
        changed_at TEXT NOT NULL,
        note TEXT,
        FOREIGN KEY(request_id) REFERENCES requests(id)
    )
    """)

    conn.commit()
    conn.close()

def insert_request(header: dict, lines: list[dict]) -> int:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO requests
        (requestor_name, department, title, vendor_name, vendor_vat_id,
         commodity_group_id, commodity_group_name,
         total_cost, currency, submit_status, process_status, created_at,
         positions_net, shipping_net, tax_amount, total_is_gross)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        header["requestor_name"],
        header["department"],
        header["title"],
        header["vendor_name"],
        header["vendor_vat_id"],
        header.get("commodity_group_id"),
        header.get("commodity_group_name"),
        header["total_cost"],
        header["currency"],
        header["submit_status"],
        header["process_status"],
        header["created_at"],
        header.get("positions_net"),
        header.get("shipping_net"),
        header.get("tax_amount"),
        header.get("total_is_gross", "yes"),
    ))

    request_id = cur.lastrowid

    for l in lines:
        cur.execute("""
            INSERT INTO order_lines
            (request_id, description, unit_price, quantity, unit, line_total)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            request_id,
            l["description"],
            l["unit_price"],
            l["quantity"],
            l.get("unit", ""),
            l["line_total"],
        ))

    cur.execute("""
        INSERT INTO status_history (request_id, old_status, new_status, changed_at, note)
        VALUES (?, ?, ?, ?, ?)
    """, (
        request_id,
        None,
        header["process_status"],
        header["created_at"],
        "Initial status",
    ))

    conn.commit()
    conn.close()
    return request_id

def load_requests():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, title, vendor_name, total_cost, currency, submit_status, process_status, created_at,
               commodity_group_id, commodity_group_name,
               positions_net, shipping_net, tax_amount, total_is_gross
        FROM requests
        ORDER BY id DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows

def load_order_lines(request_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT description, unit_price, quantity, unit, line_total
        FROM order_lines
        WHERE request_id = ?
        ORDER BY id ASC
    """, (request_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_request_status(request_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT process_status FROM requests WHERE id = ?", (request_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def update_request_status(request_id: int, new_status: str, note: str = ""):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT process_status FROM requests WHERE id = ?", (request_id,))
    row = cur.fetchone()
    old_status = row[0] if row else None

    if old_status is None:
        conn.close()
        return False, None

    if new_status == old_status:
        conn.close()
        return True, old_status

    cur.execute("UPDATE requests SET process_status = ? WHERE id = ?", (new_status, request_id))

    cur.execute("""
        INSERT INTO status_history
        (request_id, old_status, new_status, changed_at, note)
        VALUES (?, ?, ?, ?, ?)
    """, (
        request_id,
        old_status,
        new_status,
        datetime.now().isoformat(timespec="seconds"),
        note.strip()
    ))

    conn.commit()
    conn.close()
    return True, old_status

def load_status_history(request_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT old_status, new_status, changed_at, note
        FROM status_history
        WHERE request_id = ?
        ORDER BY id ASC
    """, (request_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


# -----------------------------
# Lines: Summe berechnen
# -----------------------------
def calc_lines(lines: list[dict]) -> tuple[list[dict], float]:
    cleaned = []
    total_sum = 0.0
    for l in lines:
        desc = str(l.get("description", "")).strip()
        unit_price = float(l.get("unit_price", 0) or 0)
        qty = float(l.get("quantity", 0) or 0)
        unit = str(l.get("unit", "")).strip()

        line_total = round(unit_price * qty, 2)
        total_sum += line_total
        cleaned.append({
            "description": desc,
            "unit_price": unit_price,
            "quantity": qty,
            "unit": unit,
            "line_total": line_total
        })
    return cleaned, round(total_sum, 2)


def validate_for_submit(header: dict, lines: list[dict], lines_sum: float) -> list[str]:
    errors = []
    for f in ["requestor_name", "department", "title", "vendor_name", "vendor_vat_id"]:
        if not header.get(f, "").strip():
            errors.append(f"Pflichtfeld fehlt: {f}")

    vat = header.get("vendor_vat_id", "").strip()
    if len(vat) < 8:
        errors.append("VAT ID wirkt zu kurz (bitte prüfen).")

    if not lines:
        errors.append("Mindestens eine Order Line ist nötig.")
    for i, l in enumerate(lines, start=1):
        if not str(l.get("description", "")).strip():
            errors.append(f"Order Line {i}: Beschreibung fehlt.")
        if float(l.get("unit_price", 0) or 0) <= 0:
            errors.append(f"Order Line {i}: Unit Price muss > 0 sein.")
        if float(l.get("quantity", 0) or 0) <= 0:
            errors.append(f"Order Line {i}: Quantity muss > 0 sein.")

    total = float(header.get("total_cost", 0) or 0)
    if total <= 0:
        errors.append("Total Cost muss > 0 sein.")
    if total < round(lines_sum, 2):
        errors.append("Total Cost ist kleiner als Summe der Positionen. Bitte prüfen (Versand/Steuer fehlen?).")

    return errors


# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="Procurement Request System", layout="wide")
st.title("Procurement Request System (MVP)")

init_db()

tab_intake, tab_overview = st.tabs(["1) Intake (Neu)", "2) Overview (Procurement)"])

defaults = {
    "requestor_name": "",
    "department": "",
    "title": "",
    "currency": "EUR",
    "vendor_name": "",
    "vendor_vat_id": "",
    "positions_net": None,
    "shipping_net": None,
    "tax_amount": None,
    "total_gross": None,
    "cg_id": None,
    "cg_name": None,
    "cg_conf": None,
    "cg_reason": None,
    "cg_source": "noch nicht berechnet",
}
for k, v in defaults.items():
    st.session_state.setdefault(k, v)

st.session_state.setdefault("lines", [{"description": "", "unit_price": 0.0, "quantity": 1.0, "unit": "pcs"}])

with tab_intake:
    st.subheader("Neuen Request erstellen")

    if get_clean_openai_key():
        st.caption("✅ OPENAI_API_KEY gefunden.")
    else:
        st.caption("⚠️ OPENAI_API_KEY nicht gefunden. KI-Funktionen sind dann deaktiviert.")

    st.markdown("### Datenschutz (DSGVO)")
    st.info(
        "Wenn du Auto-Fill nutzt, wird der Dokumenttext zur Extraktion an einen externen KI-Dienst übertragen. "
        "Wir maskieren typische personenbezogene Daten (z.B. E-Mail, Telefon, IBAN) automatisch. "
        "Bitte lade trotzdem keine unnötigen personenbezogenen Daten hoch."
    )
    consent = st.checkbox("Ich bin berechtigt, dieses Dokument hochzuladen, und habe den Datenschutzhinweis gelesen. *")

    # ---------- Upload + Auto-Fill ----------
    with st.expander("📎 Dokument hochladen (Auto-Fill) – empfohlen", expanded=True):
        uploaded = st.file_uploader("Dokument auswählen (PDF/TXT/DOCX)", type=["pdf", "txt", "docx"])
        do_file_autofill = st.button("Auto-Fill aus Datei")

        if do_file_autofill:
            if not consent:
                st.error("Bitte zuerst die Checkbox zum Datenschutzhinweis aktivieren.")
            elif uploaded is None:
                st.error("Bitte zuerst ein Dokument auswählen.")
            else:
                raw_text = extract_text_from_uploaded_file(uploaded)
                raw_text = normalize_offer_text(raw_text)

                if not raw_text.strip():
                    st.error("Aus dem Dokument konnte kein Text gelesen werden (vermutlich Scan-PDF ohne OCR).")
                else:
                    try:
                        # DSGVO: Redaction vor KI
                        redacted_text = redact_personal_data(raw_text)

                        extracted = extract_offer_with_openai(redacted_text)

                        if extracted.vendor_name:
                            st.session_state["vendor_name"] = extracted.vendor_name
                        if extracted.vendor_vat_id:
                            st.session_state["vendor_vat_id"] = extracted.vendor_vat_id
                        if extracted.department:
                            st.session_state["department"] = extracted.department
                        if extracted.currency in ["EUR", "USD", "GBP"]:
                            st.session_state["currency"] = extracted.currency

                        st.session_state["positions_net"] = parse_de_number_to_float(extracted.positions_net)
                        st.session_state["shipping_net"] = parse_de_number_to_float(extracted.shipping_net)
                        st.session_state["tax_amount"] = parse_de_number_to_float(extracted.tax_amount)
                        st.session_state["total_gross"] = parse_de_number_to_float(extracted.total_gross)

                        new_lines = []
                        for ol in extracted.order_lines or []:
                            new_lines.append({
                                "description": ol.description or "",
                                "unit_price": float(parse_de_number_to_float(ol.unit_price) or 0.0),
                                "quantity": float(parse_de_number_to_float(ol.quantity) or 0.0),
                                "unit": (ol.unit or "").strip() or "pcs",
                            })
                        if new_lines:
                            st.session_state["lines"] = new_lines

                        # Title generieren (neu)
                        if not st.session_state.get("title", "").strip():
                            st.session_state["title"] = generate_title_with_openai(
                                vendor=st.session_state.get("vendor_name", ""),
                                lines=st.session_state.get("lines", []),
                                department=st.session_state.get("department", ""),
                            )

                        st.success("Auto-Fill aus Datei erfolgreich. Formular wurde gefüllt.")
                        st.rerun()
                    except Exception as e:
                        st.error("Auto-Fill aus Datei hat nicht geklappt.")
                        st.caption("Details (ohne Dokumentinhalt):")
                        st.write(str(e))

    # ---------- Optional: Copy/Paste Auto-Fill ----------
    with st.expander("📄 Angebot einfügen (Copy/Paste) – optional", expanded=False):
        offer_text = st.text_area("Vendor Offer Text", height=220)
        if st.button("Auto-Fill aus Text"):
            if not consent:
                st.error("Bitte zuerst die Checkbox zum Datenschutzhinweis aktivieren.")
            elif not offer_text.strip():
                st.error("Bitte zuerst Text einfügen.")
            else:
                try:
                    raw_text = normalize_offer_text(offer_text)
                    redacted_text = redact_personal_data(raw_text)

                    extracted = extract_offer_with_openai(redacted_text)

                    if extracted.vendor_name:
                        st.session_state["vendor_name"] = extracted.vendor_name
                    if extracted.vendor_vat_id:
                        st.session_state["vendor_vat_id"] = extracted.vendor_vat_id
                    if extracted.department:
                        st.session_state["department"] = extracted.department
                    if extracted.currency in ["EUR", "USD", "GBP"]:
                        st.session_state["currency"] = extracted.currency

                    st.session_state["positions_net"] = parse_de_number_to_float(extracted.positions_net)
                    st.session_state["shipping_net"] = parse_de_number_to_float(extracted.shipping_net)
                    st.session_state["tax_amount"] = parse_de_number_to_float(extracted.tax_amount)
                    st.session_state["total_gross"] = parse_de_number_to_float(extracted.total_gross)

                    new_lines = []
                    for ol in extracted.order_lines or []:
                        new_lines.append({
                            "description": ol.description or "",
                            "unit_price": float(parse_de_number_to_float(ol.unit_price) or 0.0),
                            "quantity": float(parse_de_number_to_float(ol.quantity) or 0.0),
                            "unit": (ol.unit or "").strip() or "pcs",
                        })
                    if new_lines:
                        st.session_state["lines"] = new_lines

                    if not st.session_state.get("title", "").strip():
                        st.session_state["title"] = generate_title_with_openai(
                            vendor=st.session_state.get("vendor_name", ""),
                            lines=st.session_state.get("lines", []),
                            department=st.session_state.get("department", ""),
                        )

                    st.success("Auto-Fill aus Text erfolgreich.")
                    st.rerun()
                except Exception as e:
                    st.error("Extraktion hat nicht geklappt.")
                    st.caption("Details (ohne Dokumentinhalt):")
                    st.write(str(e))

    st.caption("Tipp: Requestor Name ist intern und wird nicht aus Angeboten extrahiert.")

    col1, col2, col3 = st.columns(3)
    with col1:
        requestor_name = st.text_input("Requestor Name *", key="requestor_name")
        department = st.text_input("Department *", key="department", placeholder="z.B. Creative Marketing Department")
    with col2:
        title = st.text_input("Title/Short Description *", key="title")
        currency = st.selectbox("Currency *", ["EUR", "USD", "GBP"], index=["EUR", "USD", "GBP"].index(st.session_state["currency"]))
        st.session_state["currency"] = currency
    with col3:
        vendor_name = st.text_input("Vendor Name *", key="vendor_name")
        vendor_vat_id = st.text_input("Umsatzsteuer-ID (VAT ID) *", key="vendor_vat_id", placeholder="z.B. DE987654321")

    st.markdown("### Order Lines (Positionen)")
    edited = st.data_editor(
        st.session_state["lines"],
        num_rows="dynamic",
        use_container_width=True,
        key="lines_editor",
        column_config={
            "description": st.column_config.TextColumn("Position Description", required=True),
            "unit_price": st.column_config.NumberColumn("Unit Price", min_value=0.0, step=1.0),
            "quantity": st.column_config.NumberColumn("Amount (Quantity)", min_value=0.0, step=0.01),
            "unit": st.column_config.TextColumn("Unit (z.B. m2, Lfm, Stk)")
        }
    )
    st.session_state["lines"] = edited

    cleaned_lines, sum_lines = calc_lines(st.session_state["lines"])
    st.info(f"Summe der Positionen (aus Lines berechnet): {sum_lines:.2f} {currency}")

    st.markdown("### Kostenübersicht (aus Angebot)")
    cA, cB, cC, cD = st.columns(4)
    with cA:
        positions_net = st.number_input("Positionen netto (optional)", min_value=0.0, step=10.0,
                                        value=float(st.session_state["positions_net"] or 0.0))
    with cB:
        shipping_net = st.number_input("Versand netto (optional)", min_value=0.0, step=5.0,
                                       value=float(st.session_state["shipping_net"] or 0.0))
    with cC:
        tax_amount = st.number_input("Steuern (USt) (optional)", min_value=0.0, step=5.0,
                                     value=float(st.session_state["tax_amount"] or 0.0))
    with cD:
        default_total = st.session_state["total_gross"]
        if default_total is None or default_total == 0:
            default_total = float(sum_lines)
        total_cost = st.number_input("Total Cost / Endsumme (inkl. Versand+Steuer) *", min_value=0.0, step=10.0,
                                     value=float(default_total))

    st.caption("Hinweis: Total Cost ist die Endsumme. Sie muss NICHT der Summe der Positionen entsprechen.")

    st.markdown("### Commodity Group (automatisch)")
    fallback_id, fallback_name = simple_commodity_group_guess(title, vendor_name, cleaned_lines)

    if st.button("Commodity Group automatisch bestimmen (KI)"):
        try:
            pick = pick_commodity_group_with_openai(title, vendor_name, cleaned_lines)
            st.session_state["cg_id"] = pick.commodity_group_id
            st.session_state["cg_name"] = pick.commodity_group_name
            st.session_state["cg_conf"] = float(pick.confidence)
            st.session_state["cg_reason"] = pick.reasoning_short
            st.session_state["cg_source"] = "KI"
            st.rerun()
        except Exception:
            st.session_state["cg_id"] = fallback_id
            st.session_state["cg_name"] = fallback_name
            st.session_state["cg_source"] = "Fallback"
            st.rerun()

    cg_id = st.session_state["cg_id"] or fallback_id
    cg_name = st.session_state["cg_name"] or fallback_name
    st.write(f"**Vorschlag:** {cg_id} – {cg_name}")

    def build_header(submit_status: str):
        return {
            "requestor_name": requestor_name.strip(),
            "department": department.strip(),
            "title": title.strip(),
            "vendor_name": vendor_name.strip(),
            "vendor_vat_id": vendor_vat_id.strip(),
            "commodity_group_id": cg_id,
            "commodity_group_name": cg_name,
            "total_cost": float(total_cost),
            "currency": currency,
            "submit_status": submit_status,
            "process_status": "Open",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "positions_net": float(positions_net) if positions_net > 0 else None,
            "shipping_net": float(shipping_net) if shipping_net > 0 else None,
            "tax_amount": float(tax_amount) if tax_amount > 0 else None,
            "total_is_gross": "yes",
        }

    colA, colB = st.columns(2)
    with colA:
        if st.button("Als Draft speichern"):
            request_id = insert_request(build_header("Draft"), cleaned_lines)
            st.success(f"Draft gespeichert. Request ID: {request_id}")

    with colB:
        if st.button("Absenden (Submitted)"):
            header = build_header("Submitted")
            errors = validate_for_submit(header, cleaned_lines, sum_lines)
            if errors:
                st.error("Request kann nicht abgesendet werden:")
                for e in errors:
                    st.write("- " + e)
            else:
                request_id = insert_request(header, cleaned_lines)
                st.success(f"Request erfolgreich abgesendet. Request ID: {request_id}")

with tab_overview:
    st.subheader("Requests (Overview)")
    rows = load_requests()
    if not rows:
        st.info("Noch keine Requests gespeichert.")
    else:
        table = []
        for r in rows:
            table.append({
                "ID": r[0],
                "Title": r[1],
                "Vendor": r[2],
                "Total (Endsumme)": f"{r[3]} {r[4]}",
                "Submit": r[5],
                "Status": r[6],
                "Created": r[7],
                "Commodity ID": r[8],
                "Commodity Name": r[9],
                "Pos. netto": r[10],
                "Versand netto": r[11],
                "Steuer": r[12],
            })
        st.dataframe(table, use_container_width=True)

        st.markdown("### Request-Details anzeigen")
        selected_id = st.number_input("Request ID", min_value=1, step=1, value=int(rows[0][0]))
        lines = load_order_lines(int(selected_id))
        if lines:
            st.dataframe(
                [{"Description": l[0], "Unit Price": l[1], "Qty": l[2], "Unit": l[3], "Line Total": l[4]} for l in lines],
                use_container_width=True
            )
        else:
            st.info("Keine Order Lines gefunden (oder falsche ID).")

        st.markdown("### Status ändern (Procurement)")
        current_status = get_request_status(int(selected_id))
        if current_status:
            options = ["Open", "In Progress", "Closed"]
            new_status = st.selectbox("Neuer Status", options, index=options.index(current_status) if current_status in options else 0)
            note = st.text_input("Kommentar (optional)", placeholder="z.B. Prüfung gestartet")
            if st.button("Status speichern"):
                ok, old_status = update_request_status(int(selected_id), new_status, note)
                if ok and old_status != new_status:
                    st.success(f"Status geändert: {old_status} → {new_status}")
                    st.rerun()

        st.markdown("### Status-Historie")
        history = load_status_history(int(selected_id))
        if history:
            st.dataframe(
                [{"Von": h[0], "Zu": h[1], "Zeitpunkt": h[2], "Kommentar": h[3]} for h in history],
                use_container_width=True
            )
        else:
            st.info("Noch keine Statusänderungen.")
