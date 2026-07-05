try:
    from .agent import root_agent
except ModuleNotFoundError as exc:
    if exc.name != "google":
        raise
    root_agent = None

__all__ = ["root_agent"]
