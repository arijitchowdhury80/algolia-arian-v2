"""Pure-function tests for _norm and _match_slug in prism-report-qa.

Uses a fake in-memory index — no filesystem, no network, no Hermes.
"""

import importlib.util
import os
import sys
import unittest
from unittest.mock import patch

# Load plugin from file (hyphenated directory cannot be imported directly)
_PLUGIN_INIT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "__init__.py")
)
_spec = importlib.util.spec_from_file_location("prism_report_qa", _PLUGIN_INIT)
plugin = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(plugin)

_norm = plugin._norm
_match_slug = plugin._match_slug

# Fake index: two entries that cover the interesting edge cases
FAKE_INDEX = [
    {
        "slug": "homedepot-mexico",
        "domain": "homedepot.com.mx",
        "company": "The Home Depot México",
    },
    {
        "slug": "petsmart",
        "domain": "petsmart.com",
        "company": "PetSmart",
    },
]


class TestNorm(unittest.TestCase):
    """_norm: NFKD-decompose, drop combining marks, lowercase, strip."""

    def test_accent_removal(self):
        self.assertEqual(_norm("México"), "mexico")

    def test_multi_accent(self):
        self.assertEqual(_norm("Ñoño"), "nono")

    def test_lowercase(self):
        self.assertEqual(_norm("PetSmart"), "petsmart")

    def test_strip_whitespace(self):
        self.assertEqual(_norm("  home  "), "home")

    def test_combined_accented_phrase(self):
        self.assertEqual(_norm("The Home Depot México"), "the home depot mexico")

    def test_already_clean(self):
        self.assertEqual(_norm("homedepot"), "homedepot")

    def test_empty(self):
        self.assertEqual(_norm(""), "")


class TestMatchSlug(unittest.TestCase):
    """_match_slug: alias-token matching with fake index, conservative binding."""

    def setUp(self):
        self.patcher = patch.object(plugin, "_load_index", return_value=FAKE_INDEX)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    # --- positive matches ---

    def test_two_word_brand(self):
        """'home depot' matches via 'depot' company-word token (len 5)."""
        self.assertEqual(_match_slug("home depot"), "homedepot-mexico")

    def test_slug_as_one_word(self):
        """'homedepot' matches via domain-root token 'homedepot'."""
        self.assertEqual(_match_slug("homedepot"), "homedepot-mexico")

    def test_full_accented_name(self):
        """'the home depot méxico' matches via exact normalized company string."""
        self.assertEqual(_match_slug("the home depot méxico"), "homedepot-mexico")

    def test_case_insensitive(self):
        """Case should not matter."""
        self.assertEqual(_match_slug("The Home Depot"), "homedepot-mexico")

    def test_petsmart_exact(self):
        self.assertEqual(_match_slug("petsmart"), "petsmart")

    def test_petsmart_in_sentence(self):
        self.assertEqual(_match_slug("tell me about petsmart's search"), "petsmart")

    def test_domain_match(self):
        self.assertEqual(_match_slug("homedepot.com.mx"), "homedepot-mexico")

    # --- negative: must NOT bind ---

    def test_generic_word_home_no_bind(self):
        """'home' alone is 4 chars and MUST NOT bind — too generic."""
        self.assertIsNone(_match_slug("home"))

    def test_unrelated_message(self):
        self.assertIsNone(_match_slug("i like cats"))

    def test_empty_string(self):
        self.assertIsNone(_match_slug(""))

    def test_none_input(self):
        self.assertIsNone(_match_slug(None))

    def test_generic_search_word_no_bind(self):
        """A one-word generic query should not bind."""
        self.assertIsNone(_match_slug("search"))

    def test_stopword_only(self):
        """Stopwords like 'inc' must not cause a bind."""
        self.assertIsNone(_match_slug("inc"))


if __name__ == "__main__":
    unittest.main()
