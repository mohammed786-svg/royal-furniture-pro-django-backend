"""Canonical store / company details — invoices, Shiprocket, CMS."""

COMPANY_NAME = "Royal Furniture Pro"
COMPANY_ADDRESS_LINE1 = "1st Cross, Azam Nagar,"
COMPANY_ADDRESS = "1st Cross, Azam Nagar, Belagavi, Karnataka 590010"
COMPANY_CITY = "Belagavi"
COMPANY_STATE = "Karnataka"
COMPANY_PINCODE = "590010"
COMPANY_COUNTRY = "India"
COMPANY_PHONE = "080730 93766"
COMPANY_EMAIL = "customercare@royalfurniturepro.com"

COMPANY_INFO = {
    "name": COMPANY_NAME,
    "address": COMPANY_ADDRESS,
    "state": COMPANY_STATE,
    "phone": COMPANY_PHONE,
    "email": COMPANY_EMAIL,
}

SHIPROCKET_WAREHOUSE_DEFAULTS = {
    "name": COMPANY_NAME,
    "address": COMPANY_ADDRESS_LINE1,
    "address_2": f"{COMPANY_CITY}, {COMPANY_STATE} {COMPANY_PINCODE}",
    "city": COMPANY_CITY,
    "state": COMPANY_STATE,
    "pincode": COMPANY_PINCODE,
    "country": COMPANY_COUNTRY,
    "email": COMPANY_EMAIL,
    "phone": COMPANY_PHONE.replace(" ", ""),
}
