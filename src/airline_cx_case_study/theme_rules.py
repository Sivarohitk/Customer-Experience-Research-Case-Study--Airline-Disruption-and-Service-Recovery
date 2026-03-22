"""Rule definitions for the first-pass qualitative theme coding workflow.

Edit this file to refine the theme dictionaries later. Each theme contains:

- `description`: a plain-language explanation of the theme
- `keywords`: exact words or phrases matched with word-boundary regex logic
- `regex`: optional custom regex patterns for flexible phrasing
- `exclude_keywords`: optional phrases that suppress false-positive matches
"""

THEME_RULES = {
    "delay frustration": {
        "description": "Frustration caused by long waits, rolling delays, missed connections, or extended time at the gate.",
        "keywords": [
            "delay",
            "delayed",
            "hours late",
            "late departure",
            "rolling delay",
            "gate wait",
            "tarmac wait",
            "missed connection",
            "departure kept moving",
        ],
        "regex": [
            r"\b\d+\s+hours?\s+late\b",
            r"\bwait(?:ed|ing)?\s+(?:at|in)\s+the\s+gate\b",
        ],
        "exclude_keywords": [],
    },
    "cancellation stress": {
        "description": "Stress and disruption caused by cancellations, overnight stranding, and unclear next steps.",
        "keywords": [
            "cancelled",
            "canceled",
            "cancellation",
            "stranded",
            "overnight",
            "hotel guidance",
            "same day cancellation",
            "flight was cancelled",
        ],
        "regex": [
            r"\bflight\s+was\s+cancel(?:led|ed)\b",
            r"\bno\s+clear\s+next\s+steps\b",
        ],
        "exclude_keywords": [],
    },
    "refund difficulty": {
        "description": "Difficulty getting money back, understanding voucher policies, or securing reimbursement.",
        "keywords": [
            "refund",
            "refunded",
            "voucher",
            "travel credit",
            "credit",
            "reimburse",
            "reimbursement",
            "claim form",
            "refund request",
        ],
        "regex": [
            r"\btook\s+\d+\s+days\s+to\s+get\s+the\s+money\s+back\b",
            r"\brefund\s+process\b",
        ],
        "exclude_keywords": [],
    },
    "rebooking friction": {
        "description": "Friction in changing itineraries, standing by, or securing replacement seats after disruption.",
        "keywords": [
            "rebook",
            "rebooking",
            "standby",
            "new itinerary",
            "alternate flight",
            "seat assignment",
            "missed connection",
            "kiosk",
            "re accommodated",
        ],
        "regex": [
            r"\bwait(?:ed|ing)?\s+\w*\s*minutes?\s+in\s+line\b",
            r"\bapp\s+kept\s+removing\s+the\s+seat\b",
        ],
        "exclude_keywords": [],
    },
    "poor communication": {
        "description": "Lack of timely, accurate, or consistent updates during disruption and recovery.",
        "keywords": [
            "no updates",
            "conflicting information",
            "no proactive communication",
            "unclear",
            "no explanation",
            "not informed",
            "announcements",
            "status updates",
            "communication",
        ],
        "regex": [
            r"\bapp\s+showed\s+one\s+itinerary\b",
            r"\bgate\s+(?:agents|staff|team)\s+had\s+no\s+consistent\s+script\b",
            r"\bapp\s+kept\s+(?:changing|refreshing)\b",
        ],
        "exclude_keywords": [
            "clear communication",
            "clear updates",
            "good communication",
        ],
    },
    "baggage problems": {
        "description": "Problems with lost, delayed, misrouted, or poorly tracked baggage.",
        "keywords": [
            "baggage",
            "luggage",
            "checked bag",
            "lost bag",
            "lost luggage",
            "bag claim",
            "carousel",
            "tracing number",
            "delivery driver",
        ],
        "regex": [
            r"\bbag\s+did\s+not\s+arrive\b",
            r"\barrived\s+\d+\s+days?\s+later\b",
        ],
        "exclude_keywords": [],
    },
    "staff helpfulness": {
        "description": "Helpful, empathetic, or professional staff behavior that shaped the customer experience.",
        "keywords": [
            "helpful",
            "kind",
            "professional",
            "apologized",
            "took ownership",
            "desk agent",
            "went out of their way",
            "solved the problem",
            "stayed with it",
        ],
        "regex": [
            r"\bagent\s+\w*\s*(?:helped|rebooked|resolved)\b",
            r"\bstaff\s+\w*\s*(?:helped|resolved|sorted)\b",
        ],
        "exclude_keywords": [
            "not helpful",
            "unhelpful",
            "no one offered a useful recovery option",
        ],
    },
    "customer support responsiveness": {
        "description": "Responsiveness, delays, or friction in phone, chat, or email support channels.",
        "keywords": [
            "customer support",
            "phone support",
            "call center",
            "chat agent",
            "on hold",
            "hold time",
            "transferred",
            "multiple contacts",
            "email response",
        ],
        "regex": [
            r"\b\d+\s+minutes?\s+on\s+hold\b",
            r"\bdisconnected\s+me\s+twice\b",
        ],
        "exclude_keywords": [],
    },
    "pricing / compensation dissatisfaction": {
        "description": "Dissatisfaction with vouchers, reimbursement, extra spend, or perceived unfair compensation.",
        "keywords": [
            "meal voucher",
            "hotel voucher",
            "compensation",
            "paid for my own hotel",
            "no voucher",
            "no reimbursement",
            "extra fee",
            "travel credit",
        ],
        "regex": [
            r"\bpaid\s+for\s+my\s+own\s+hotel\b",
            r"\bvoucher\s+policy\s+was\s+confusing\b",
        ],
        "exclude_keywords": [],
    },
    "digital / app / website issues": {
        "description": "Problems with self-service digital tools such as apps, websites, portals, and kiosks.",
        "keywords": [
            "portal",
            "kiosk could not",
            "booking page",
            "login",
            "online check in failed",
            "could not check in",
            "website crashed",
            "website failed",
        ],
        "regex": [
            r"\bapp\s+kept\s+(?:changing|refreshing|removing)\b",
            r"\bapp\s+\w*\s*(?:failed|crashed|froze)\b",
            r"\bkiosk\s+could\s+not\b",
        ],
        "exclude_keywords": [],
    },
    "trust / loyalty damage": {
        "description": "Statements that the disruption damaged trust, repeat purchase intent, or brand loyalty.",
        "keywords": [
            "lost trust",
            "lost my business",
            "status means nothing",
            "avoid this airline",
            "no confidence",
            "will not return",
        ],
        "regex": [
            r"\bnever\s+fly\s+(?:this\s+airline\s+)?again\b",
            r"\bwon\s+t\s+book\s+again\b",
        ],
        "exclude_keywords": [],
    },
    "successful recovery experience": {
        "description": "The airline ultimately resolved the disruption in a way the customer viewed positively.",
        "keywords": [
            "handled well",
            "recovered well",
            "resolved quickly",
            "clear updates",
            "rebooked me",
            "confirmed the refund",
            "delivered the luggage",
            "made it right",
            "better than expected",
            "solid recovery",
        ],
        "regex": [
            r"\bwithin\s+\d+\s+minutes\s+the\s+desk\s+agent\s+rebooked\s+me\b",
            r"\brecovery\s+was\s+well\s+handled\b",
        ],
        "exclude_keywords": [
            "not resolved",
            "never resolved",
            "did not resolve",
        ],
    },
}
