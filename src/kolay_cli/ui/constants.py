"""
Shared UI constants for kolay-cli.

Color palette sourced from the Kolay Design System:
  https://design.kolayik.com/color

Terminal mapping (Rich hex colors):
  Primary   → Blue 600  #376BFB   headings, borders, spinners
  Accent    → Blue 400  #8B9EFD   secondary text, info
  Success   → Cheer 600 #278C3D   confirmations, active status
  Warning   → Orange 300 #F9A623  pending, warnings
  Error     → Red 600   #E62729   errors, rejected, alerts
  Muted     → grey62 / grey85     IDs, timestamps, labels
"""
from __future__ import annotations

# ── Kolay Brand Hex Colors (Rich supports #RRGGBB) ───────────────────────────
PRIMARY = "#376BFB"       # Blue 600 — headings, borders, spinner
PRIMARY_SOFT = "#EFF1FF"  # Blue 50
ACCENT = "#8B9EFD"        # Blue 400 — secondary data
SHADE = "#0E4AC4"         # Blue 900 — dark emphasis

SUCCESS = "#278C3D"       # Cheer 600 — success, active
SUCCESS_SOFT = "#D7FEDC"  # Cheer 50

WARNING = "#F9A623"       # Orange 300 — pending, warnings
WARNING_DARK = "#A36B13"  # Orange 600

ERROR = "#E62729"         # Red 600 — errors, rejected
ERROR_SOFT = "#FDEFEF"    # Red 50

# ── Status Badges ─────────────────────────────────────────────────────────────
STATUS_STYLES: dict[str, str] = {
    "active":    f"[{SUCCESS}]● Active[/{SUCCESS}]",
    "inactive":  f"[{ERROR}]○ Inactive[/{ERROR}]",
    "approved":  f"[{SUCCESS}]✔ Approved[/{SUCCESS}]",
    "waiting":   f"[{WARNING}]⏳ Waiting[/{WARNING}]",
    "rejected":  f"[{ERROR}]✘ Rejected[/{ERROR}]",
    "cancelled": "[grey62]⊘ Cancelled[/grey62]",
    "pending":   f"[{WARNING}]⏳ Pending[/{WARNING}]",
}

# ── Human-Readable Field Labels ──────────────────────────────────────────────
FIELD_LABELS: dict[str, str] = {
    "id":                    "ID",
    "firstName":             "First Name",
    "lastName":              "Last Name",
    "name":                  "Name",
    "workEmail":             "Work Email",
    "email":                 "Email",
    "mobilePhone":           "Phone",
    "birthday":              "Birthday",
    "gender":                "Gender",
    "idNumber":              "ID Number",
    "employmentStartDate":   "Start Date",
    "status":                "Status",
    "createdAt":             "Created",
    "updatedAt":             "Updated",
    "amount":                "Amount",
    "currency":              "Currency",
    "date":                  "Date",
    "type":                  "Type",
    "installmentPlan":       "Installments",
    "description":           "Description",
    "paid":                  "Paid",
    "isGross":               "Gross",
    "affectPayroll":         "Affects Payroll",
    "personId":              "Person ID",
    "startDate":             "Start Date",
    "endDate":               "End Date",
    "leaveTypeId":           "Leave Type ID",
    "reasonCode":            "Reason Code",
    "details":               "Details",
    "isPaid":                "Paid Leave",
    "dayLimit":              "Day Limit",
    "used":                  "Days Used",
    "totalUpcoming":         "Upcoming",
    "unused":                "Remaining",
    "nextAccrualDate":       "Next Accrual",
    "primary":               "Primary",
}

# ── HTTP Error Messages (also in api/errors.py — kept here for UI constants) ─
HTTP_ERRORS: dict[int, str] = {
    400: "Bad request — please check your input.",
    401: "Not authorized. Run 'kolay auth login' to set your API token.",
    403: "You don't have permission to perform this action.",
    404: "Not found. Double-check the ID and try again.",
    429: "You're being rate-limited. Slow down and try again in a moment.",
    500: "Kolay API returned a server error. Try again later.",
    503: "Kolay API is temporarily unavailable. Try again later.",
}

# ── Picker Quips ──────────────────────────────────────────────────────────────

_PICKER_QUIPS = [
    "🤔 Hmm, which of your fine colleagues did you have in mind?",
    "👥 Pick a teammate — they won't know you forgot their ID:",
    "🕵️  Let's narrow it down. Who's the lucky one today?",
    "🎯 No ID? No problem. Here's everyone — take your pick:",
    "😅 Forget someone's ID? It happens. Your team is right here:",
    "🙈 A name rings a bell but the ID… not so much? Fear not:",
    "✨ Let me introduce you to your colleagues (you may recognise a few):",
]

_LEAVE_PICKER_QUIPS = [
    "📋 Which leave request did you have in mind? Here are the recent ones:",
    "🏖️  A holiday record? Let's find it — your recent leaves are below:",
    "📅 No ID? Here are the latest leave records to pick from:",
    "🔍 Let me pull up the leave list so you can find the right one:",
    "✈️  Searching for a leave record? Here's the shortlist:",
]

_TRX_PICKER_QUIPS = [
    "💸 Which transaction are we looking at? Here are the recent ones:",
    "🧾 No ID? No stress. Pick the transaction from the list below:",
    "🔍 Let's find that transaction — here are the latest:",
    "💼 Your recent transactions are waiting. Pick one:",
    "📊 ID-less and fearless — here are the recent transactions:",
]

_EVENT_PICKER_QUIPS = [
    "📅 Which event are you thinking of? Here are the upcoming ones:",
    "🗓️  No ID? No problem — pick an event from the calendar:",
    "🔍 Let me pull up your calendar so you can choose:",
    "✨ Here are your upcoming events — take your pick:",
    "📌 Searching for an event? Here's what's on the schedule:",
]

_TIMELOG_PICKER_QUIPS = [
    "🕒 Which timelog entry? Here are the recent ones:",
    "⏱️  No ID? Here are the latest timelog records:",
    "📋 Let me pull up the timelog list so you can choose:",
    "🔍 Searching for a timelog? Here are the recent entries:",
    "🗂️  Pick a timelog record from the list below:",
]

_TRAINING_PICKER_QUIPS = [
    "🎓 Which training? Here are the ones in the catalogue:",
    "📚 No ID? Pick a training from the list below:",
    "🔍 Let me pull up the training catalogue for you:",
    "✨ Here's what's in the training catalogue — take your pick:",
    "🗂️  Choose a training from the catalogue:",
]

_PERSON_TRAINING_PICKER_QUIPS = [
    "🎓 Which training assignment? Here are the recent ones:",
    "📋 No ID? Pick a training assignment from the list:",
    "🔍 Let me look up the training assignments for you:",
]

_FILE_PICKER_QUIPS = [
    "📁 Which file or folder? Here's what's attached to this employee:",
    "🗂️  No ID? Pick a file from the list below:",
    "🔍 Let me pull up the employee's documents for you:",
    "📎 Here are the attached files — take your pick:",
]
