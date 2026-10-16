"""Custom exceptions for the susu application."""


class SusuError(Exception):
    """Base exception for all susu errors."""


class InvalidAmountError(SusuError):
    """Raised when a monetary amount is invalid."""


class DuplicateMemberError(SusuError):
    """Raised when adding a member whose ID already exists in the group."""


class UnknownMemberError(SusuError):
    """Raised when referencing a member ID that does not exist."""


class OverpaymentError(SusuError):
    """Raised when a contribution exceeds the expected weekly amount."""


class WeekNotCompleteError(SusuError):
    """Raised when advancing the week before all members have contributed."""


class GroupLockedError(SusuError):
    """Raised when trying to add members after contributions have started."""


class GroupCompletedError(SusuError):
    """Raised when trying to operate on a group that has already finished."""
