"""
UI package for kolay-cli.
Provides formatting, constants, and interactive pickers.
"""
from .formatters import (
    console, short_id, display_status, fmt_val, fmt_num, label,
    print_error, print_api_error, print_success, print_fetching, print_empty, kv_table,
    spinner, api_call, recoverable_api_call, no_command_help, print_next_steps, print_pagination_footer,
    confirm_destructive_action, print_irreversible_warning, validate_date, prompt_date, fmt_datetime,
)
from .constants import (
    PRIMARY, ACCENT, SUCCESS, WARNING, ERROR,
    STATUS_STYLES, FIELD_LABELS, HTTP_ERRORS,
    _PICKER_QUIPS, _LEAVE_PICKER_QUIPS, _TRX_PICKER_QUIPS,
    _EVENT_PICKER_QUIPS, _TIMELOG_PICKER_QUIPS, _TRAINING_PICKER_QUIPS,
    _PERSON_TRAINING_PICKER_QUIPS
)
from .pickers import (
    pick_person, pick_leave, pick_transaction, pick_event,
    pick_timelog, pick_training, pick_person_training,
    pick_person_file
)
from .search import filter_items, filter_items_silent
from .output import (
    is_json_mode, is_yes_mode, json_output, json_error, strip_markup,
    require_arg, resolve_row, global_to_page_relative,
)
from .page_state import save_page_state, load_page_state, clear_page_state

__all__ = [
    "console", "short_id", "display_status", "fmt_val", "fmt_num", "label",
    "print_error", "print_success", "print_fetching", "print_empty", "print_next_steps",
    "print_pagination_footer", "confirm_destructive_action", "print_irreversible_warning",
    "validate_date", "prompt_date", "fmt_datetime",
    "kv_table",
    "spinner", "api_call", "recoverable_api_call",
    "PRIMARY", "ACCENT", "SUCCESS", "WARNING", "ERROR",
    "STATUS_STYLES", "FIELD_LABELS", "HTTP_ERRORS",
    "pick_person", "pick_leave", "pick_transaction", "pick_event",
    "pick_timelog", "pick_training", "pick_person_training", "pick_person_file",
    "filter_items", "filter_items_silent",
    "is_json_mode", "is_yes_mode", "json_output", "json_error", "strip_markup",
    "require_arg", "resolve_row", "global_to_page_relative",
    "save_page_state", "load_page_state", "clear_page_state",
]

