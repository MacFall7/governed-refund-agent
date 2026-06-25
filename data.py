"""Mock CRM. In-memory only — no database, by design (build-to-demo).

`TODAY` is pinned so every demo run is reproducible no matter when it is
recorded. The orders flagged "DEMO:" below are the ones to use on camera.
"""
from datetime import date

# Pinned "now" so the 30-day / 90-day windows never drift between takes.
TODAY = date(2026, 6, 25)

# 15 customer profiles.
CUSTOMERS = {
    "C001": {"id": "C001", "name": "Alice Nguyen",   "email": "alice@example.com",   "tier": "standard"},
    "C002": {"id": "C002", "name": "Ben Carter",     "email": "ben@example.com",     "tier": "standard"},
    "C003": {"id": "C003", "name": "Carmen Diaz",    "email": "carmen@example.com",  "tier": "gold"},
    "C004": {"id": "C004", "name": "Dan Okafor",     "email": "dan@example.com",     "tier": "standard"},
    "C005": {"id": "C005", "name": "Eve Larsson",    "email": "eve@example.com",     "tier": "gold"},
    "C006": {"id": "C006", "name": "Fiona Reilly",   "email": "fiona@example.com",   "tier": "standard"},
    "C007": {"id": "C007", "name": "Greg Tanaka",    "email": "greg@example.com",    "tier": "standard"},
    "C008": {"id": "C008", "name": "Hana Park",      "email": "hana@example.com",    "tier": "gold"},
    "C009": {"id": "C009", "name": "Ivan Petrov",    "email": "ivan@example.com",    "tier": "standard"},
    "C010": {"id": "C010", "name": "Julia Mendes",   "email": "julia@example.com",   "tier": "standard"},
    "C011": {"id": "C011", "name": "Kofi Mensah",    "email": "kofi@example.com",    "tier": "gold"},
    "C012": {"id": "C012", "name": "Lena Schmidt",   "email": "lena@example.com",    "tier": "standard"},
    "C013": {"id": "C013", "name": "Marco Rossi",    "email": "marco@example.com",   "tier": "standard"},
    "C014": {"id": "C014", "name": "Nadia Hassan",   "email": "nadia@example.com",   "tier": "gold"},
    "C015": {"id": "C015", "name": "Omar Said",      "email": "omar@example.com",    "tier": "standard"},
}

# Orders. `status` is "active" or "refunded". `last_refund_date` lives on the
# customer-level summary below for the 90-day rule.
ORDERS = {
    # DEMO: clean APPROVE — 13 days old, not final sale, never refunded.
    "1001": {"id": "1001", "customer_id": "C001", "item": "Wireless Headphones", "amount": 129.99, "purchase_date": date(2026, 6, 12), "final_sale": False, "status": "active"},

    "1002": {"id": "1002", "customer_id": "C002", "item": "USB-C Cable",        "amount": 14.99,  "purchase_date": date(2026, 6, 20), "final_sale": False, "status": "active"},
    "1003": {"id": "1003", "customer_id": "C003", "item": "Mechanical Keyboard","amount": 89.00,  "purchase_date": date(2026, 6, 5),  "final_sale": False, "status": "active"},

    # DEMO: DENY (final sale) — recent, but flagged final sale. Holding the line.
    "1007": {"id": "1007", "customer_id": "C004", "item": "Clearance Jacket",   "amount": 89.00,  "purchase_date": date(2026, 6, 18), "final_sale": True,  "status": "active"},

    "1008": {"id": "1008", "customer_id": "C005", "item": "Desk Lamp",          "amount": 39.95,  "purchase_date": date(2026, 6, 22), "final_sale": False, "status": "active"},

    # DEMO: DENY (outside 30-day window) — purchased 66 days ago.
    "1010": {"id": "1010", "customer_id": "C006", "item": "Blender",            "amount": 59.50,  "purchase_date": date(2026, 4, 20), "final_sale": False, "status": "active"},

    "1011": {"id": "1011", "customer_id": "C007", "item": "Yoga Mat",           "amount": 24.00,  "purchase_date": date(2026, 6, 10), "final_sale": False, "status": "active"},

    # DEMO: DENY (already refunded).
    "1012": {"id": "1012", "customer_id": "C008", "item": "Bluetooth Speaker",  "amount": 49.99,  "purchase_date": date(2026, 6, 14), "final_sale": False, "status": "refunded"},

    "1013": {"id": "1013", "customer_id": "C009", "item": "Phone Case",         "amount": 19.99,  "purchase_date": date(2026, 6, 1),  "final_sale": False, "status": "active"},

    # DEMO: DENY (one-refund-per-90-days) — customer C010 was refunded 20 days ago.
    "1015": {"id": "1015", "customer_id": "C010", "item": "Backpack",           "amount": 74.00,  "purchase_date": date(2026, 6, 19), "final_sale": False, "status": "active"},

    "1016": {"id": "1016", "customer_id": "C011", "item": "Monitor Stand",      "amount": 45.00,  "purchase_date": date(2026, 6, 8),  "final_sale": False, "status": "active"},
    "1017": {"id": "1017", "customer_id": "C012", "item": "Water Bottle",       "amount": 22.50,  "purchase_date": date(2026, 6, 21), "final_sale": False, "status": "active"},
    "1018": {"id": "1018", "customer_id": "C013", "item": "Running Shoes",      "amount": 110.00, "purchase_date": date(2026, 5, 30), "final_sale": False, "status": "active"},
    "1019": {"id": "1019", "customer_id": "C014", "item": "Sunglasses",         "amount": 65.00,  "purchase_date": date(2026, 6, 17), "final_sale": True,  "status": "active"},
    "1020": {"id": "1020", "customer_id": "C015", "item": "Travel Pillow",      "amount": 18.00,  "purchase_date": date(2026, 6, 23), "final_sale": False, "status": "active"},
}

# Rolling-window refund history per customer (drives R4). Date of most recent
# completed refund, or None. C010 has a recent refund to trigger the 90-day deny.
REFUND_HISTORY = {
    "C008": date(2026, 6, 15),  # the already-refunded order 1012
    "C010": date(2026, 6, 5),   # 20 days ago -> blocks order 1015
}
