# \# Procurement Request System (MVP)

# 

# A lightweight, locally deployable \*\*Procurement Request System\*\* with a web-based user interface.  

# Employees can create procurement requests, upload vendor offers, and automatically extract relevant information using AI.  

# The procurement department maintains full visibility and control over request statuses.

# 

# ---

# 

# \## 🎯 Purpose of the Project

# 

# Procurement processes often fail not because of complexity, but because:

# \- requestors do not know which information is required,

# \- commodity groups are selected incorrectly,

# \- manual data entry from offers is time-consuming and error-prone.

# 

# This project demonstrates how \*\*AI-assisted intake\*\* can significantly simplify procurement workflows while keeping \*\*control and compliance\*\* with procurement.

# 

# ---

# 

# \## 🧩 Key Features

# 

# \### 1) Intake – Create a Procurement Request

# \- Web form to create new procurement requests

# \- Flexible \*\*order line\*\* input (positions from an offer)

# \- Save requests as \*\*Draft\*\* (incomplete allowed)

# \- \*\*Submit\*\* requests only when validation rules are met

# 

# ---

# 

# \### 2) Automatic Offer Extraction (AI)

# Users typically already have a vendor offer available.  

# Instead of manually copying data, the system supports:

# 

# \- Uploading \*\*PDF / TXT / DOCX\*\* documents  

# \- Alternatively: \*\*Copy \& Paste\*\* offer text

# 

# The AI automatically extracts:

# \- Vendor name

# \- VAT ID

# \- Department (if stated in the offer)

# \- Order lines (description, unit price, quantity, unit)

# \- Cost structure:

# &nbsp; - Net positions

# &nbsp; - Shipping costs

# &nbsp; - Tax amount

# &nbsp; - Total gross amount (final price)

# 

# ➡️ \*\*Title / Short Description\*\* is automatically generated,  

# because real-world offers usually do \*\*not\*\* contain such a field.

# 

# ---

# 

# \### 3) Automatic Commodity Group Assignment

# Selecting the correct commodity group is a frequent source of errors.

# 

# In this system:

# \- Users \*\*do not select\*\* a commodity group

# \- The AI assigns the most appropriate group based on:

# &nbsp; - Request title

# &nbsp; - Vendor

# &nbsp; - Order lines (purpose of purchase)

# 

# A fallback heuristic is used if AI is unavailable.

# 

# ---

# 

# \### 4) Overview – Procurement View

# For the procurement department:

# \- Overview of all requests

# \- Detailed view including order lines

# \- Status management:

# &nbsp; - Open

# &nbsp; - In Progress

# &nbsp; - Closed

# \- \*\*Full status history\*\* is automatically logged

# 

# ---

# 

# \## 🔐 Data Protection \& GDPR (Technical Measures)

# 

# The system is designed with \*\*data minimisation and GDPR awareness\*\* in mind:

# 

# \- ✔ Explicit user consent before any AI-based extraction

# \- ✔ \*\*Redaction before AI processing\*\*:

# &nbsp; - Email addresses

# &nbsp; - Phone numbers

# &nbsp; - IBAN / BIC

# &nbsp; - Named contact persons

# \- ✔ No storage of:

# &nbsp; - Original uploaded documents

# &nbsp; - Full unstructured offer texts

# \- ✔ Only structured procurement-relevant data is stored

# \- ✔ Local data storage (SQLite)

# 

# \*\*Important:\*\*  

# This is a technical MVP. For productive use, organisational measures  

# (e.g. DPA/AVV, role concepts) would still be required.

# 

# ---

# 

# \## 🛠 Technology Stack

# 

# \- \*\*Python 3.12\*\*

# \- \*\*Streamlit\*\* – web frontend

# \- \*\*SQLite\*\* – local database

# \- \*\*OpenAI API\*\* – data extraction \& classification

# \- \*\*PyPDF / python-docx\*\* – document parsing

# 

# ---

# 

# \## 🚀 Local Setup \& Run

# 

# \### 1) Clone the repository

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























