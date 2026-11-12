from __future__ import annotations


class ShipCrewError(Exception):
    """Base application error."""


class NotFoundError(ShipCrewError):
    pass


class ValidationError(ShipCrewError):
    pass


class AuthError(ShipCrewError):
    pass


class RunnerError(ShipCrewError):
    pass


class OrchestratorError(ShipCrewError):
    pass
