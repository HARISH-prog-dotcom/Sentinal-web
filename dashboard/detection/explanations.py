"""Plain-language explanations shown on the dashboard for each event category.

An AI model could write these later, but treat its output as advice, not as the security decision.
"""
from dashboard.detection.models import Category

EXPLANATIONS = {
    Category.SQL_INJECTION: "The input contains text shaped like SQL code. Attackers use this to try to change a database query. "
                            "This is a pattern match, so a human should review it.",
    Category.SQL_INJECTION_ML: "No fixed rule matched, but the trained model scored this input as very similar to known SQL injection "
                               "examples. This is a statistical guess, so it is flagged for human review and not blocked.",
    Category.XSS: "The input contains HTML or script-like text. If a page displayed it unsafely, a browser might run it as code. "
                  "This is a pattern match, so review it.",
    Category.REPEATED_FAILED_LOGINS: "Many failed login attempts hit one account in a short time. This can mean password guessing, "
                                     "so the account was temporarily rate-limited.",
    Category.FAILED_LOGIN: "A single failed login is normal. It is recorded so repeated attempts can be counted.",
    Category.API_FLOOD: "One client sent far more requests than normal in a short window, so it was temporarily rate-limited.",
    Category.NORMAL: "No detection rule matched this request.",
}


def explain(category: str) -> str:
    """Explanation text for a category (empty string for unknown categories)."""
    return EXPLANATIONS.get(category, "")
