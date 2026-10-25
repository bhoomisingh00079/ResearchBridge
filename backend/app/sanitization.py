import nh3


def clean_text(value: str) -> str:
    """Strip markup from user-provided content before storing plain text."""
    return nh3.clean(value, tags=set(), attributes={}, strip_comments=True).strip()
