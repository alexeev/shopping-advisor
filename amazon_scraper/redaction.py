"""Strip per-session identifiers from a saved Amazon page.

This used to live in ``tests/corpus/redact.py`` and be reached from the crawler
by appending the test directory to ``sys.path``. That arrangement had two
faults, and only the second one is obvious:

* a crawl's privacy handling depended on a test directory being importable;
* the import was wrapped in ``except Exception: return html``, so a redaction
  that failed for any reason silently stored the **unredacted** page. A page
  store therefore could not tell you whether what it held was safe to promote
  into the corpus or to hand to anybody.

So the implementation is runtime code, the corpus CLI imports it, and
:func:`redact_page` reports what happened rather than only what came back.
Refusing to store the page at all would be worse -- the bytes are evidence,
and the page cannot be fetched again -- so the caller keeps it and marks it.

Identifiers are found at their canonical declaration and then replaced
literally, rather than matched by shape across the whole document. Shape rules
are what you reach for first and they are wrong here: every UUID also matches
an A+ content image URL, and every twenty-character uppercase token also
matches a German A+ heading (``HERZENSANGELEGENHEIT``). Both mistakes were
made, and both were caught by the corpus test, which is the real guard --
redaction must not change a single extracted value.
"""

import re

SESSION_ID = '000-0000000-0000000'
REQUEST_ID = 'X' * 20
CORRELATION_ID = '00000000-0000-0000-0000-000000000000'

#: Redaction ran and the page may be exported or promoted.
APPLIED = 'applied'
#: Redaction raised. The page is kept as it arrived and must not be exported.
FAILED = 'failed'

# Amazon declares both per-page identifiers once, in the ue_* telemetry
# preamble, and then echoes them into a dozen keys, hidden inputs and query
# strings (session-id, rsid, sid, sessionId, verificationSessionID, rid,
# requestId, uedata URLs, ...). Reading them here and replacing the literal
# catches every echo without having to enumerate the keys.
DECLARED_IDS = (
    (re.compile(r"\bue_sid\s*=\s*'([^']{6,64})'"), SESSION_ID),
    (re.compile(r"\bue_id\s*=\s*'([^']{6,64})'"), REQUEST_ID),
)

SUBSTITUTIONS = (
    # Safety net for a page saved without the ue_* preamble. This shape is
    # distinctive enough not to collide with product text.
    (re.compile(r'\b\d{3}-\d{7}-\d{7}\b'), SESSION_ID),
    # Per-widget correlation ids, anchored to the attribute or key that
    # carries them: the values are opaque and come in two shapes (a UUID and a
    # base64-ish token), and bare UUIDs also appear inside A+ image URLs,
    # which are content. Both the attribute form and the HTML-escaped JSON
    # form appear on the same page.
    (re.compile(r'(data-a?rid=")[^"]{8,64}(")'),
     r'\g<1>' + CORRELATION_ID + r'\g<2>'),
    (re.compile(r'("|&quot;)a?rid\1\s*:\s*("|&quot;)[^"&]{8,64}\2'),
     r'\g<1>arid\g<1>:\g<2>' + CORRELATION_ID + r'\g<2>'),
    # The render service's own IP, echoed into A+ preview metadata.
    (re.compile(r'("|&quot;)ipAddress\1\s*:\s*("|&quot;)[0-9.]+\2'),
     r'\1ipAddress\1:\g<2>0.0.0.0\2'),
)


def redact(html):
    """Return `html` with per-session identifiers replaced by fixed values."""
    for pattern, replacement in DECLARED_IDS:
        match = pattern.search(html)
        if match:
            html = html.replace(match.group(1), replacement)
    for pattern, replacement in SUBSTITUTIONS:
        html = pattern.sub(replacement, html)
    return html


def redact_page(html):
    """``(text, status)`` -- redacted where possible, and always honest.

    ``status`` is :data:`APPLIED` or :data:`FAILED`. On failure the original
    text comes back, because losing an unrepeatable observation to a
    substitution bug would be the worse trade; the status is what stops it
    being exported, promoted into the corpus, or mistaken for a clean page.
    """
    try:
        return redact(html), APPLIED
    except Exception:
        return html, FAILED
