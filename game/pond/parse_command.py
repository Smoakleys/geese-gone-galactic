# BUILT BY ICARUS (gpt-oss:20b) for OP-29 (command parser) via the full gate. tests/test_parse_command.py
def parse_command(text):
    """
    Split the input text on whitespace and return a tuple (verb, target).
    The verb is the first word lowercased; the target is the second word lowercased.
    If there are fewer than two words, missing elements are empty strings.
    An empty or blank string returns ('', '').

    Parameters:
        text (str): The input command string.

    Returns:
        tuple[str, str]: A 2-tuple of lowercased verb and target.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    words = text.split()
    if len(words) == 0:
        return ("", "")
    verb = words[0].lower()
    target = words[1].lower() if len(words) > 1 else ""
    return (verb, target)