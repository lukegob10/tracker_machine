import getpass
import os


def get_default_user_id() -> str:
    """Return a best-effort user id based on the machine's username or overrides."""
    env_user = (
        os.getenv("JIRA_LITE_USER_ID")
        or os.getenv("USER")
        or os.getenv("USERNAME")
        or os.getenv("LOGNAME")
    )
    if env_user:
        return env_user
    try:
        return getpass.getuser()
    except Exception:
        return "unknown"
