"""Transliteration client using Google Input Tools API.

This module provides functions to transliterate English (Roman) text to Devanagari
using Google's Input Tools API.
"""

import requests
from typing import List


def transliterate_word(text: str, num_suggestions: int = 5) -> List[str]:
    """Transliterate English text to Devanagari using Google IME API.

    Args:
        text: English text to transliterate (e.g., "namaste").
        num_suggestions: Number of suggestions to return (default: 5).

    Returns:
        List of Devanagari suggestions. Returns empty list if transliteration fails.
    """
    if not text.strip():
        return []

    url = "https://inputtools.google.com/request"
    params = {
        "text": text,
        "itc": "hi-t-i0-und",  # Hindi input method
        "num": num_suggestions,
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()

        # Parse response
        # Format: ["SUCCESS", [["input", ["suggestion1", "suggestion2", ...]]]]
        if data[0] == "SUCCESS":
            suggestions = data[1][0][1]
            return suggestions
    except requests.exceptions.RequestException as e:
        # Network error - return empty list
        pass
    except (IndexError, KeyError) as e:
        # Invalid response format
        pass

    return []


def transliterate_sentence(text: str) -> str:
    """Transliterate a sentence word by word.

    Args:
        text: English sentence to transliterate.

    Returns:
        Transliterated Devanagari text.
    """
    words = text.split()
    transliterated_words = []

    for word in words:
        suggestions = transliterate_word(word, num_suggestions=1)
        if suggestions:
            transliterated_words.append(suggestions[0])
        else:
            # If transliteration fails, keep original word
            transliterated_words.append(word)

    return " ".join(transliterated_words)


def get_transliteration_candidates(text: str, num_suggestions: int = 5) -> dict:
    """Get transliteration candidates for each word in text.

    Args:
        text: English text to transliterate.
        num_suggestions: Number of suggestions per word.

    Returns:
        Dictionary mapping each word to its list of candidates.
    """
    words = text.split()
    candidates = {}

    for word in words:
        candidates[word] = transliterate_word(word, num_suggestions)

    return candidates
