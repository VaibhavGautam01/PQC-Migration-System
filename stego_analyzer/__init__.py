"""Stego Analyzer (Team Task Plan v3, Section 10A; design in docs/analyzer_spec.md).

Upload a stego image made by our own image project; the analyzer detects how the message was hidden,
extracts it, identifies the cipher, breaks it where a method applies (real Shor circuit at toy size, or the
existing small-key attack), gives a labelled estimate for larger keys, and scores the result with the SAME
risk engine as the rest of the project. Anything outside our formats is "unrecognised"; it is never guessed.

Every stage lives in its own module with one function. A stage that is not built yet raises
NotImplementedStage; the pipeline then stops and says which stage, and it never invents a result.
"""


class NotImplementedStage(Exception):
    """Raised by a stage module that has not been written yet."""
