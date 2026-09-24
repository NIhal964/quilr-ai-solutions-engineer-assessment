import re

PII_PATTERN = re.compile(
    r"""
    (?:
        [A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}
        |
        \b\d{3}-\d{2}-\d{4}\b
        |
        \b(?:\d[ -]*?){13,19}\b
    )
    """,
    re.VERBOSE,
)


class StreamingPIIRedactor:
    """
    Incremental redactor that retains an unfinished email token.

    The rolling tail covers fixed-length patterns. An email local part can be
    arbitrarily long in this demo pattern, so it must be held until a delimiter
    arrives; memory then depends on the longest unfinished token.
    """

    def __init__(self, overlap: int = 96):
        self.overlap = overlap
        self.buffer = ""

    def feed(self, text: str) -> str:
        self.buffer += text
        if len(self.buffer) <= self.overlap:
            return ""

        safe_cut = len(self.buffer) - self.overlap
        candidate = self.buffer[:safe_cut]

        # If the cut lands inside a regex match, retain from the start of that
        # match instead of emitting a partial sensitive value.
        for match in PII_PATTERN.finditer(self.buffer):
            if match.start() < safe_cut < match.end():
                safe_cut = match.start()
                break

        # A later chunk may add "@example.com" to a still-unfinished word.
        # Do not emit any prefix of that word before we know whether it is PII.
        if self.buffer and re.match(r"[A-Za-z0-9._%+@-]", self.buffer[-1]):
            token_start = len(self.buffer)
            while token_start and re.match(r"[A-Za-z0-9._%+@-]", self.buffer[token_start - 1]):
                token_start -= 1
            safe_cut = min(safe_cut, token_start)

        candidate = self.buffer[:safe_cut]
        self.buffer = self.buffer[safe_cut:]
        return PII_PATTERN.sub("[REDACTED]", candidate)

    def flush(self) -> str:
        output = PII_PATTERN.sub("[REDACTED]", self.buffer)
        self.buffer = ""
        return output
