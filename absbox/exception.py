
class VersionMismatch(Exception):
    """Exception for version mismatch between client and server"""
    def __init__(self, libVersion, serverVersion) -> None:
        self.libVersion = libVersion
        self.serverVersion = serverVersion
        super().__init__(f"Failed to match version, lib support={libVersion} but server version={serverVersion}")

class EngineError(Exception):
    """Exception for error from engine server"""
    def __init__(self, engineResp) -> None:
        errorMsg = engineResp.text
        super().__init__(errorMsg)

class AbsboxError(Exception):
    """Exception for error from absbox"""
    def __init__(self, errorMsg) -> None:
        super().__init__(errorMsg)

class LibraryError(Exception):
    """Exception for error from absbox"""
    def __init__(self, errorMsg) -> None:
        super().__init__(errorMsg)