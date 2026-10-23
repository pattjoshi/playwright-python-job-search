"""Auto-apply: fill in (and submit) applications on company career pages, using your Answer Bank."""

from job_search.services.auto_apply.manager import AutoApplyManager
from job_search.services.auto_apply.service import AutoApplyError, AutoApplyService, clean_settings, open_browser

__all__ = ["AutoApplyError", "AutoApplyManager", "AutoApplyService", "clean_settings", "open_browser"]
