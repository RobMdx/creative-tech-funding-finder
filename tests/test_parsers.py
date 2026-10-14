"""Offline tests for the page readers. Run: python3 -m unittest discover tests"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from common import money, page_text, parse_date, parse_ifs, parse_ukri  # noqa: E402

UKRI_DL = """<html><body><h1>CoSTAR Satellite Labs</h1><dl>
<dt>Opportunity status:</dt><dd>Open</dd><dt>Funders:</dt><dd>Arts and Humanities Research Council (AHRC)</dd>
<dt>Funding type:</dt><dd>Grant</dd><dt>Total fund:</dt><dd>£4,000,000</dd><dt>Maximum award:</dt><dd>£2,000,000</dd>
<dt>Publication date:</dt><dd>24 August 2026</dd><dt>Opening date:</dt><dd>24 August 2026 9:00am UK time</dd>
<dt>Closing date:</dt><dd>29 October 2026 4:00pm UK time</dd></dl><script>var x='Closing date: 1 January 2020'</script></body></html>"""
UKRI_INLINE = """<div><p><strong>Opportunity status: </strong>Open</p><p><strong>Award range: </strong>£100,000 - £300,000</p>
<p><strong>Opening date: </strong>23 September 2026 9:00am UK time</p><p><strong>Closing date: </strong>Open - no closing date</p></div>"""
IFS = """<main><p><strong>Competition opens:</strong> Wednesday 21 October 2026</p>
<p><strong>Competition closes:</strong> Tuesday 8 December 2026 11:00am</p><p>This competition has not yet opened.</p></main>"""


class Parsers(unittest.TestCase):
    def test_ukri_definition_list(self):
        i = parse_ukri(page_text(UKRI_DL))
        self.assertEqual(i["status"], "Open")
        self.assertEqual(i["closing"], "2026-10-29")
        self.assertEqual(i["opening"], "2026-08-24")
        self.assertEqual(i["total_fund"], [4000000])
        self.assertEqual(i["maximum"], [2000000])
        self.assertFalse(i["always_open"])

    def test_ukri_inline_always_open(self):
        i = parse_ukri(page_text(UKRI_INLINE))
        self.assertTrue(i["always_open"])
        self.assertIsNone(i["closing"])
        self.assertEqual(i["award_range"], [100000, 300000])

    def test_ifs(self):
        i = parse_ifs(page_text(IFS))
        self.assertEqual(i["opening"], "2026-10-21")
        self.assertEqual(i["closing"], "2026-12-08")
        self.assertTrue(i["not_open_yet"])

    def test_helpers(self):
        self.assertEqual(parse_date("Tuesday 8 December 2026 11:00am"), "2026-12-08")
        self.assertIsNone(parse_date("soon"))
        self.assertEqual(money("£2.5m and £150k"), [2500000, 150000])


if __name__ == "__main__":
    unittest.main()
