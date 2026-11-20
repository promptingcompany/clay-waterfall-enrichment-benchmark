"""Helpers shared by the W1 adapters."""
import sys


def find(obj, *names):
    """First non-empty value under any of `names` (case-insensitive), searched breadth-first.
    Vendors nest the same field differently across endpoints, so lookups are by name."""
    wanted = {n.lower() for n in names}
    queue = [obj]
    while queue:
        cur = queue.pop(0)
        if isinstance(cur, dict):
            for k, v in cur.items():
                if k.lower() in wanted and v not in (None, "", [], {}):
                    return v
            queue.extend(cur.values())
        elif isinstance(cur, list):
            queue.extend(cur)
    return None


def text(v):
    return "" if v is None else str(v).strip()


# Vendors return HQ country as a name ("UNITED STATES") or an ISO code ("US"); the answer key uses codes.
# Unlisted country names pass through unmatched and are logged once.
COUNTRY_CODES = {"UNITED STATES": "US", "UNITED STATES OF AMERICA": "US", "USA": "US", "CANADA": "CA", "MEXICO": "MX",
                 "UNITED KINGDOM": "GB", "UK": "GB", "ENGLAND": "GB", "SCOTLAND": "GB", "WALES": "GB", "NORTHERN IRELAND": "GB",
                 "IRELAND": "IE", "GERMANY": "DE", "FRANCE": "FR", "NETHERLANDS": "NL", "BELGIUM": "BE", "SPAIN": "ES",
                 "ITALY": "IT", "PORTUGAL": "PT", "SWITZERLAND": "CH", "AUSTRIA": "AT", "SWEDEN": "SE", "NORWAY": "NO",
                 "DENMARK": "DK", "FINLAND": "FI", "POLAND": "PL", "ISRAEL": "IL", "UNITED ARAB EMIRATES": "AE",
                 "INDIA": "IN", "SINGAPORE": "SG", "AUSTRALIA": "AU", "NEW ZEALAND": "NZ", "JAPAN": "JP", "CHINA": "CN",
                 "HONG KONG": "HK", "SOUTH KOREA": "KR", "BRAZIL": "BR", "SOUTH AFRICA": "ZA", "LUXEMBOURG": "LU",
                 "CAYMAN ISLANDS": "KY", "BERMUDA": "BM"}


_unmapped = set()


def country_code(v):
    v = text(v).upper()
    if len(v) > 2 and v not in COUNTRY_CODES and v not in _unmapped:  # two letters is taken as an ISO code already
        _unmapped.add(v)
        print(f"HQ country {v!r} isn't in COUNTRY_CODES (providers/common.py), so it can't match the answer key: "
              "add it to the map", file=sys.stderr)
    return COUNTRY_CODES.get(v, v)


def fields(email=None, phone=None, company_name=None, employee_count=None, industry=None, hq_country=None):
    return {"email": text(email), "phone": text(phone), "company_name": text(company_name),
            "employee_count": text(employee_count), "industry": text(industry), "hq_country": country_code(hq_country)}
