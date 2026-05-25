DATA_AXLE_EMAIL_SUFFIX = "@data-axle.com"


def validate_data_axle_email(email: str) -> str:
    normalized = email.strip().lower()
    if not normalized.endswith(DATA_AXLE_EMAIL_SUFFIX):
        raise ValueError(f"Email must end with {DATA_AXLE_EMAIL_SUFFIX}")
    local = normalized[: -len(DATA_AXLE_EMAIL_SUFFIX)]
    if not local or "@" in local:
        raise ValueError("Invalid email address.")
    return normalized
