"""
Shared UI constants for kolay-cli.
"""
from __future__ import annotations


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


STATUS_STYLES: dict[str, str] = {
    "active":    f"[{SUCCESS}]● Active[/{SUCCESS}]",
    "inactive":  f"[{ERROR}]○ Inactive[/{ERROR}]",
    "approved":  f"[{SUCCESS}]✔ Approved[/{SUCCESS}]",
    "waiting":   f"[{WARNING}]⏳ Waiting[/{WARNING}]",
    "rejected":  f"[{ERROR}]✘ Rejected[/{ERROR}]",
    "cancelled": "[grey62]⊘ Cancelled[/grey62]",
    "pending":   f"[{WARNING}]⏳ Pending[/{WARNING}]",
}


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

# Kept here for UI constants.
HTTP_ERRORS: dict[int, str] = {
    400: "Bad request — please check your input.",
    401: "Not authorized. Run 'kolay auth login' to set your API token.",
    403: "You don't have permission to perform this action.",
    404: "Not found. Double-check the ID and try again.",
    429: "You're being rate-limited. Slow down and try again in a moment.",
    500: "Kolay API returned a server error. Try again later.",
    503: "Kolay API is temporarily unavailable. Try again later.",
}

_PICKER_QUIPS = ["Select a person:"]
_LEAVE_PICKER_QUIPS = ["Select a leave record:"]
_TRX_PICKER_QUIPS = ["Select a transaction:"]
_EVENT_PICKER_QUIPS = ["Select an event:"]
_TIMELOG_PICKER_QUIPS = ["Select a timelog:"]
_TRAINING_PICKER_QUIPS = ["Select a training:"]
_PERSON_TRAINING_PICKER_QUIPS = ["Select a training assignment:"]
_FILE_PICKER_QUIPS = ["Select a file:"]


KOLAY_LOGO = f"""
[bold {PRIMARY}]      █████████████████[/bold {PRIMARY}]
[bold {PRIMARY}]     ████         ████[/bold {PRIMARY}]
[bold {PRIMARY}]    ████         ████    ██ ██  ████  ██     ████  ██  ██[/bold {PRIMARY}]
[bold {PRIMARY}]   ████         ████     ████  ██  ██ ██    ██████  ████[/bold {PRIMARY}]
[bold {PRIMARY}]    ████       █████     ████  ██  ██ ██    ██  ██   ██[/bold {PRIMARY}]
[bold {PRIMARY}]     ██████████████      ██ ██  ████  █████ ██  ██  ███[/bold {PRIMARY}]
[bold {PRIMARY}]      ████████████                                 ███[/bold {PRIMARY}]
"""
