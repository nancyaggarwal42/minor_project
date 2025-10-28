# file: lid_segmenter.py
# This script detects language spans in a piece of text. It:
# 1) Splits text into runs of the same Unicode script (Latin, Devanagari, Arabic, etc.)
# 2) Predicts language for each run (or per-token for Latin/Cyrillic to handle code-switching)
# 3) Returns spans with start/end offsets, script name, language code, and confidence
#
# Install dependencies before running:
#   pip install regex fasttext
# Download fastText LID model (put in same folder as this script):
#   https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz

import regex as re          # 'regex' supports advanced Unicode properties (better than built-in 're' for this use-case)
import fasttext             # fastText provides a pre-trained multilingual language ID model
from collections import Counter  # Counter simplifies weighted voting for language decisions

# Path to the fastText language ID model (compressed .ftz file).
# Make sure the file exists in your project folder, or update the path accordingly.
FT_MODEL_PATH = "lid.176.ftz"

# Load the language ID model once at startup.
# This is relatively fast and avoids reloading on every function call.
ft_lid = fasttext.load_model(FT_MODEL_PATH)

# Build a single regular expression that breaks input text into "script runs":
# - Each run is a continuous sequence of characters that share the same Unicode script
# - We also capture punctuation/whitespace as separate runs
# The (?P<Name>...) syntax names each capturing group, so we can later tell which script matched.
SCRIPT_RUN_RE = re.compile(
    r"(?P<Latin>\p{Script=Latin}+)"         # Latin script (English, Spanish, French, etc.)
    r"|(?P<Cyrillic>\p{Script=Cyrillic}+)"  # Cyrillic script (Russian, Ukrainian, etc.)
    r"|(?P<Arabic>\p{Script=Arabic}+)"      # Arabic script (Arabic, Persian, Urdu in Arabic script)
    r"|(?P<Devanagari>\p{Script=Devanagari}+)"  # Devanagari (Hindi, Marathi, etc.)
    r"|(?P<Han>\p{Script=Han}+)"            # Han ideographs (Chinese characters)
    r"|(?P<Hiragana>\p{Script=Hiragana}+)"  # Japanese Hiragana
    r"|(?P<Katakana>\p{Script=Katakana}+)"  # Japanese Katakana
    r"|(?P<Hangul>\p{Script=Hangul}+)"      # Korean Hangul
    r"|(?P<Greek>\p{Script=Greek}+)"        # Greek
    r"|(?P<Hebrew>\p{Script=Hebrew}+)"      # Hebrew
    r"|(?P<Thai>\p{Script=Thai}+)"          # Thai
    r"|(?P<Bengali>\p{Script=Bengali}+)"    # Bengali
    r"|(?P<Gurmukhi>\p{Script=Gurmukhi}+)"  # Punjabi (Gurmukhi)
    r"|(?P<Gujarati>\p{Script=Gujarati}+)"  # Gujarati
    r"|(?P<Oriya>\p{Script=Oriya}+)"        # Odia (Oriya)
    r"|(?P<Tamil>\p{Script=Tamil}+)"        # Tamil
    r"|(?P<Telugu>\p{Script=Telugu}+)"      # Telugu
    r"|(?P<Kannada>\p{Script=Kannada}+)"    # Kannada
    r"|(?P<Malayalam>\p{Script=Malayalam}+)"# Malayalam
    r"|(?P<Sinhala>\p{Script=Sinhala}+)"    # Sinhala
    r"|(?P<Lao>\p{Script=Lao}+)"            # Lao
    r"|(?P<Khmer>\p{Script=Khmer}+)"        # Khmer
    r"|(?P<Myanmar>\p{Script=Myanmar}+)"    # Burmese (Myanmar)
    r"|(?P<Tibetan>\p{Script=Tibetan}+)"    # Tibetan
    r"|(?P<Punct>[\p{P}\p{S}\p{Z}\p{N}]+)"  # Punctuation (P), Symbols (S), Separators/spaces (Z), Numbers (N)
)

# Helper function: Wrap fastText prediction and return a list of (lang_code, probability) tuples.
# fastText returns labels like "__label__en"; we strip the prefix to get "en".
def _ft_predict_lang(text, k=2):
    labels, probs = ft_lid.predict(text, k=k)                 # Ask for top-k language predictions
    langs = [lbl.replace("__label__", "") for lbl in labels]  # Remove "__label__" prefix
    return list(zip(langs, probs))                            # Pair each lang with its probability

# Tokenization regex:
# - \p{L}+ matches one or more letters (a word)
# - |\P{L} matches any single non-letter character (punctuation, space, emoji, etc.)
# This keeps every character and helps us preserve exact offsets in the original text.
TOKEN_RE = re.compile(r"\p{L}+|\P{L}")

# Tokenize text while keeping original character offsets.
# Returns a list of tuples: (token_string, start_offset, end_offset)
def _tokenize_with_offsets(text, start_offset=0):
    tokens = []                                               # Accumulate (token, start, end)
    for m in TOKEN_RE.finditer(text):                         # Iterate all tokens matched by TOKEN_RE
        tok = m.group(0)                                      # The token text
        start = start_offset + m.start()                      # Start index in the full original text
        end = start_offset + m.end()                          # End index in the full original text
        tokens.append((tok, start, end))                      # Store token with offsets
    return tokens

# Determine if a token should be considered a "word" (contains at least one alphabetic char).
# Non-words (spaces, punctuation) are handled differently in span building.
def _is_word(tok):
    return any(ch.isalpha() for ch in tok)

# Given a list of tokens (with offsets), estimate the dominant language via weighted voting.
# We:
# - Skip very short/non-word tokens (noisy for LID)
# - Predict language for each token
# - Weight votes by token length (capped) * prediction confidence
# - Return the winning language and a rough confidence ratio
def _dominant_lang_for_tokens(tokens):
    votes = []                                                # Collect (lang, weight) pairs
    for tok, _, _ in tokens:                                  # Iterate tokens, ignore offsets here
        t = tok.strip()                                       # Trim whitespace
        if len(t) < 2 or not _is_word(t):                     # Skip single letters and non-words
            continue
        pred = _ft_predict_lang(t, k=1)                       # Get top-1 language for the token
        if pred:
            lang, prob = pred[0]                              # Unpack lang code and probability
            # Downweight very short tokens; cap length at 10 to avoid excessive weight
            weight = min(len(t), 10) * float(prob)
            votes.append((lang, weight))                      # Add weighted vote
    if not votes:                                             # If no usable tokens, return 'und' (undetermined)
        return ("und", 0.0)
    counter = Counter()                                       # Sum weights per language
    for lang, w in votes:
        counter[lang] += w
    lang, total = counter.most_common(1)[0]                   # Get the language with the highest total weight
    # Compute a rough confidence as the winner's share of all weights
    conf = total / (sum(counter.values()) + 1e-9)
    return (lang, float(conf))

# Main function: detect language spans in the given text.
# Returns a list of dicts with:
#   - start, end: character offsets in the original string
#   - script: Unicode script name (e.g., "Latin", "Devanagari", "Common" for punctuation)
#   - lang: BCP-47-ish language code from fastText (e.g., 'en', 'es', 'hi'), or 'und' if uncertain
#   - confidence: float 0..1 indicating confidence (heuristic)
def detect_language_spans(text):
    """
    Returns a list of spans:
    {
      'start': int,
      'end': int,
      'script': str,
      'lang': str,         # e.g., 'en', 'es', 'hi', 'und'
      'confidence': float  # 0..1
    }
    """
    spans = []                                                # Collect raw spans before merging

    # Iterate over script runs in the text. Each match corresponds to one continuous block:
    # e.g., "Hola" (Latin), " " (Punct), "你好" (Han), etc.
    for m in SCRIPT_RUN_RE.finditer(text):
        seg = m.group(0)                                      # The matched segment text
        script = None                                         # Will hold which script group matched

        # Determine which named group matched by checking which group has a non-None value
        for k, v in m.groupdict().items():
            if v is not None:
                script = k
                break

        # Calculate start/end offsets of this segment in the original text
        start, end = m.start(), m.end()

        # If it's punctuation/whitespace, mark as 'Common' script and 'und' language with 0 confidence
        if script == "Punct":
            spans.append({
                "start": start, "end": end,
                "script": "Common",
                "lang": "und", "confidence": 0.0
            })
            continue                                          # Move to the next segment

        # For Latin and Cyrillic scripts, code-switching across languages is common (e.g., Spanglish).
        # We classify per token and merge adjacent tokens with the same predicted language.
        if script in ("Latin", "Cyrillic"):
            token_list = _tokenize_with_offsets(seg, start)   # Tokenize this segment with absolute offsets
            current = None                                     # 'current' accumulates a span under construction

            for tok, ts, te in token_list:                    # ts/te are absolute start/end offsets for the token
                if not _is_word(tok):                         # If token is not a word (punct/space/etc.)
                    if current:
                        current["end"] = te                   # Extend current span through this non-word
                    else:
                        # No current span: add a small 'Common/und' span for this non-word
                        spans.append({"start": ts, "end": te, "script": "Common", "lang": "und", "confidence": 0.0})
                    continue

                # Predict language for the token (top-1)
                (lang, prob) = _ft_predict_lang(tok, k=1)[0]
                # If the model is uncertain (< 0.60), treat as undetermined to avoid overconfident labeling
                if prob < 0.60:
                    lang = "und"

                if current and current["lang"] == lang:       # Same language as current span → extend it
                    current["end"] = te
                    # Update confidence with a simple rolling average (keeps it in a reasonable range)
                    current["confidence"] = (current["confidence"] + float(prob)) / 2.0
                else:
                    # Different language (or no current span) → flush previous and start a new one
                    if current:
                        spans.append(current)
                    current = {"start": ts, "end": te, "script": script, "lang": lang, "confidence": float(prob)}

            # After looping tokens, flush any remaining current span
            if current:
                spans.append(current)

        else:
            # For non-Latin/Cyrillic scripts (e.g., Devanagari, Arabic), we usually don't need per-token LID.
            # We'll estimate language for the whole run using majority vote across its word tokens.
            tokens = [t for t in _tokenize_with_offsets(seg, start) if _is_word(t[0])]

            # Get dominant language via weighted vote; fallback to 'und' if no usable tokens
            lang, conf = _dominant_lang_for_tokens(tokens) if tokens else ("und", 0.0)

            # If still undetermined but we have non-empty text, try predicting on the raw segment
            if lang == "und" and len(seg.strip()) > 0:
                cand = _ft_predict_lang(seg, k=1)[0]
                lang, conf = cand[0], float(cand[1])

            # Add the span for this script run
            spans.append({
                "start": start, "end": end,
                "script": script, "lang": lang, "confidence": conf
            })

    # Post-processing: merge adjacent spans that share the same language and script.
    # This reduces fragmentation (e.g., "Hello " + "world" both 'en/Latin' get merged).
    merged = []
    for s in spans:
        if merged and merged[-1]["lang"] == s["lang"] and merged[-1]["script"] == s["script"]:
            merged[-1]["end"] = s["end"]                       # Extend previous span to cover this one
            # Smooth confidence by averaging (simple heuristic)
            merged[-1]["confidence"] = (merged[-1]["confidence"] + s["confidence"]) / 2.0
        else:
            merged.append(s)                                   # Start a new merged span

    return merged                                             # Final list of language spans

# When the script is run directly (not imported), run a quick demo with sample sentences.
if __name__ == "__main__":
    samples = [
        "Hola amigo, how are you?",                           # Spanish + English (Latin)
        "आज मौसम अच्छा है, but it’s cold.",                  # Hindi (Devanagari) + English (Latin)
        "你好，world!",                                       # Chinese Han + English (Latin)
        "السلام عليكم friends",                               # Arabic + English (Latin)
        "yeh plan theek hai? I'm not sure.",                  # Romanized Hindi + English (challenging for LID)
    ]
    for txt in samples:
        print("\nTEXT:", txt)                                 # Show the input text
        for sp in detect_language_spans(txt):                 # Print each detected span dict
            print(sp)