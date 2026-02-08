# &nbsp;Procurement Request System (MVP)

# 

# A lightweight, locally deployable \*\*Procurement Request System\*\* with a web-based user interface.  

# Employees can create procurement requests, upload vendor offers, and automatically extract relevant information using AI.  

# The procurement department maintains full visibility and control over request statuses.

# 

# ---

# 

# &nbsp;🎯 Purpose of the Project

# 

# Procurement processes often fail not because of complexity, but because:

# \- requestors do not know which information is required,

# \- commodity groups are selected incorrectly,

# \- manual data entry from offers is time-consuming and error-prone.

# 

# This project demonstrates how \*\*AI-assisted intake\*\* can simplify procurement workflows while keeping \*\*control and traceability\*\*.

# 

# ---

# 

# &nbsp;🧩 Key Features

# 

# 1\) Intake – Create a Procurement Request

# \- Web form to create new procurement requests

# \- Flexible \*\*order line\*\* input (positions from an offer)

# \- Save requests as \*\*Draft\*\* (incomplete allowed)

# \- \*\*Submit\*\* requests only when validation rules are met

# 

# &nbsp;2) Automatic Offer Extraction (AI)

# Users typically already have a vendor offer available. Instead of manually copying data, the system supports:

# \- Uploading \*\*PDF / TXT / DOCX\*\* documents

# \- Alternatively: \*\*Copy \& Paste\*\* offer text

# 

# The AI extracts:

# \- Vendor name

# \- VAT ID

# \- Department (if stated in the offer)

# \- Order lines (description, unit price, quantity, unit)

# \- Cost structure (if present in the offer): net positions, shipping, tax amount, total gross

# 

# ➡️ \*\*Title / Short Description\*\* is automatically generated because real-world offers usually do \*\*not\*\* contain such a field.  

# ➡️ \*\*Requestor Name\*\* is not extracted (it usually does not exist in vendor offers); it remains a manual input.

# 

# &nbsp;3) Automatic Commodity Group Assignment

# \- Users do \*\*not\*\* select a commodity group

# \- The AI assigns the most appropriate group based on request context (title/vendor/order lines)

# \- A fallback heuristic is used if AI is unavailable

# 

# &nbsp;4) Overview – Procurement View

# \- Overview of all requests

# \- Detail view including order lines

# \- Status management: \*\*Open / In Progress / Closed\*\*

# \- \*\*Status history\*\* is automatically logged

# 

# ---

# 

# 🔐 Data Protection \& GDPR (Technical Measures)

# 

# The system is designed with \*\*data minimisation\*\* in mind:

# 

# \- Explicit user consent before any AI-based extraction

# \- \*\*Redaction before AI processing\*\* (typical personal data):

# &nbsp; - Email addresses

# &nbsp; - Phone numbers

# &nbsp; - IBAN / BIC

# &nbsp; - Named contact persons

# \- No storage of:

# &nbsp; - original uploaded documents

# &nbsp; - full unstructured offer texts

# \- Only structured, procurement-relevant data is stored locally (SQLite)

# 

# \*\*Note:\*\* This is a technical MVP. For productive use, organisational measures (e.g., DPA/AVV, role concepts) would still be required.

# 

# ---

# 

# 🏗️ System Architecture (High Level)

# 

# flowchart TD

# &nbsp; U\["User / Requestor<br>(Browser)"] --> S\["Streamlit Web App<br>Intake + Overview"]

# 

# &nbsp; S -->|Upload PDF/TXT/DOCX<br>or Copy/Paste text| P\["Local Document Processing<br>Extract text"]

# &nbsp; P --> R\["Redaction / Data Minimisation<br>(email, phone, IBAN, contact names)"]

# &nbsp; R --> AI\["OpenAI API<br>Extraction + Title + Commodity Group"]

# 

# &nbsp; AI -->|Structured result| S

# 

# &nbsp; S --> DB\[("SQLite Database - local file<br>requests / order\_lines / status\_history")]

# &nbsp; DB --> S

# 

# &nbsp; S -->|Status updates| H\["Status History Logging"]

# &nbsp; H --> DB





# &nbsp;🚀 Local Setup \& Run

# 

# &nbsp;1) Clone the repository

# ```bash

# git clone https://github.com/SpaceMaen/procurement-request-system.git

# cd procurement-request-system

# 

# 2\) Activate virtual environment

# .venv\\Scripts\\activate

# 

# 3\) Install dependencies

# pip install -r requirements.txt

# 

# 4\) Set OpenAI API key

# setx OPENAI\_API\_KEY sk-...

# 

# 5\) Run the application

# streamlit run app/app.

# 

# Project Structure

# 

# pyprocurement-request-system/

# │

# ├── app/

# │   └── app.py              # Streamlit application

# │

# ├── docs/

# │   └── BLUEPRINT.md        # Conceptual blueprint (MVP)

# │

# ├── .gitignore

# ├── README.md

# └── LICENSE

