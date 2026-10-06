class AutomationError(Exception):
    """Base class for framework errors."""


class BotChallengeError(AutomationError):
    """eBay showed a captcha or block page."""


class ItemNotAddableError(AutomationError):
    """Listing cannot be added to cart (auction-only, ended, out of stock...)."""
