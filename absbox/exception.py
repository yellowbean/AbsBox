
class VersionMismatch(Exception):
    """Exception for version mismatch between client and server"""
    def __init__(self, libVersion, serverVersion) -> None:
        self.libVersion = libVersion
        self.serverVersion = serverVersion
        super().__init__(f"Failed to match version, lib support={libVersion} but server version={serverVersion}")

class EngineError(Exception):
    """Exception for error from engine server"""
    def __init__(self, engineResp) -> None:
        errorMsg = getattr(engineResp, "text", None) or str(engineResp)
        super().__init__(errorMsg)

class AbsboxError(Exception):
    """Exception for error from absbox"""
    def __init__(self, errorMsg) -> None:
        super().__init__(errorMsg)

class LibraryError(Exception):
    """Exception for error from absbox"""
    def __init__(self, errorMsg) -> None:
        super().__init__(errorMsg)

class AbsboxParseError(RuntimeError):
    """Raised when a deal / DSL / response value cannot be parsed into an ADT.

    Subclasses ``RuntimeError`` so callers that already catch ``RuntimeError``
    keep working. The constructor messages intentionally contain a truncated
    preview of the offending value (see ``absbox.local.interface.preview``)
    rather than dumping an entire deal/pool into logs.
    """
