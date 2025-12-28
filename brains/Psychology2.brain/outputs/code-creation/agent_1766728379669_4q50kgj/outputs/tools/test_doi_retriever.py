import csv, io, json, os, tempfile, unittest
from dataclasses import is_dataclass
from unittest.mock import patch

def _import(mod):
    try:
        return __import__(mod, fromlist=['*'])
    except Exception as e:
        raise AssertionError(f"Failed to import {mod}: {e}")

def _get_any(module, *names):
    for n in names:
        if hasattr(module, n):
            return getattr(module, n)
    raise AssertionError(f"None of {names} found in {module.__name__}")

class TestDoiRetriever(unittest.TestCase):
    def test_normalize_doi(self):
        src = _import('outputs.tools.doi_retriever_sources')
        normalize = _get_any(src, 'normalize_doi', 'canon_doi', 'normalize')
        cases = {
            '10.1000/ABC.DEF': '10.1000/abc.def',
            ' DOI:10.1000/abc.def ': '10.1000/abc.def',
            'https://doi.org/10.1000/ABC.DEF': '10.1000/abc.def',
            'http://dx.doi.org/10.1000/ABC.DEF': '10.1000/abc.def',
        }
        for raw, exp in cases.items():
            self.assertEqual(normalize(raw), exp)
        with self.assertRaises(Exception):
            normalize('not_a_doi')

    def test_schema_serialization_roundtrip(self):
        sch = _import('outputs.tools.doi_retriever_schema')
        Attempt = _get_any(sch, 'RetrievalAttempt', 'Attempt', 'AttemptLog', 'RetrievalLogEntry')
        to_dict = _get_any(sch, 'attempt_to_dict', 'to_dict', 'asdict_attempt', 'serialize_attempt')
        from_dict = _get_any(sch, 'attempt_from_dict', 'from_dict', 'attempt_from', 'deserialize_attempt')
        a = Attempt(doi='10.1000/abc', source='unpaywall', ok=True, url='https://example.com/pdf',
                    license='cc-by', is_oa=True, is_pd=False, failure_code=None, failure_reason=None,
                    status_code=200)
        self.assertTrue(is_dataclass(a))
        d = to_dict(a)
        self.assertIsInstance(d, dict)
        j = json.dumps(d)
        a2 = from_dict(json.loads(j))
        d2 = to_dict(a2)
        for k in ('doi','source','ok','url','license','is_oa','is_pd','failure_code','failure_reason','status_code'):
            self.assertEqual(d.get(k), d2.get(k))

    def test_unpaywall_adapter_parsing_mock_http(self):
        src = _import('outputs.tools.doi_retriever_sources')
        sch = _import('outputs.tools.doi_retriever_schema')
        Attempt = _get_any(sch, 'RetrievalAttempt', 'Attempt', 'AttemptLog', 'RetrievalLogEntry')
        unpaywall = _get_any(src, 'query_unpaywall', 'unpaywall_lookup', 'fetch_unpaywall')
        sample = {
            "doi": "10.1000/abc",
            "is_oa": True,
            "best_oa_location": {"url_for_pdf": "https://repo.org/abc.pdf", "license": "cc-by"},
            "oa_locations": [{"url_for_pdf": "https://repo.org/abc.pdf", "license": "cc-by"}]
        }
        def fake_get_json(url, *args, **kwargs):
            self.assertIn('unpaywall', url.lower())
            return sample, 200, None
        with patch('outputs.tools.doi_retriever_http.get_json', side_effect=fake_get_json):
            att = unpaywall('10.1000/abc', email='x@y.org')
        if isinstance(att, list):
            self.assertTrue(att)
            att = att[0]
        self.assertIsInstance(att, Attempt)
        self.assertTrue(getattr(att, 'ok'))
        self.assertIn('repo.org/abc.pdf', getattr(att, 'url'))
        self.assertIn(getattr(att, 'license'), (None, 'cc-by'))

    def test_crossref_adapter_parsing_mock_http(self):
        src = _import('outputs.tools.doi_retriever_sources')
        sch = _import('outputs.tools.doi_retriever_schema')
        Attempt = _get_any(sch, 'RetrievalAttempt', 'Attempt', 'AttemptLog', 'RetrievalLogEntry')
        crossref = _get_any(src, 'query_crossref', 'crossref_lookup', 'fetch_crossref')
        sample = {"message": {"DOI": "10.1000/abc", "link": [{"URL": "https://pub.com/abc.pdf", "content-type": "application/pdf"}]}}
        def fake_get_json(url, *args, **kwargs):
            self.assertIn('crossref', url.lower())
            return sample, 200, None
        with patch('outputs.tools.doi_retriever_http.get_json', side_effect=fake_get_json):
            att = crossref('10.1000/abc', mailto='x@y.org')
        if isinstance(att, list):
            self.assertTrue(att)
            att = att[0]
        self.assertIsInstance(att, Attempt)
        self.assertIn(getattr(att, 'source'), ('crossref', 'Crossref'))
        self.assertIn('pub.com/abc.pdf', getattr(att, 'url', '') or '')

    def test_output_jsonl_and_csv_generation(self):
        sch = _import('outputs.tools.doi_retriever_schema')
        Attempt = _get_any(sch, 'RetrievalAttempt', 'Attempt', 'AttemptLog', 'RetrievalLogEntry')
        write_jsonl = _get_any(sch, 'write_jsonl', 'dump_jsonl', 'write_attempts_jsonl')
        write_csv = _get_any(sch, 'write_csv', 'dump_csv', 'write_attempts_csv')
        attempts = [
            Attempt(doi='10.1/a', source='unpaywall', ok=True, url='https://x/a.pdf', license='cc0', is_oa=True, is_pd=True,
                    failure_code=None, failure_reason=None, status_code=200),
            Attempt(doi='10.1/b', source='crossref', ok=False, url=None, license=None, is_oa=None, is_pd=None,
                    failure_code='not_found', failure_reason='404', status_code=404),
        ]
        with tempfile.TemporaryDirectory() as td:
            p1 = os.path.join(td, 'out.jsonl')
            p2 = os.path.join(td, 'out.csv')
            write_jsonl(p1, attempts)
            write_csv(p2, attempts)
            txt = Path(p1).read_text(encoding='utf-8').strip().splitlines()
            self.assertEqual(len(txt), 2)
            obj0 = json.loads(txt[0])
            self.assertIn('doi', obj0)
            self.assertIn('source', obj0)
            with open(p2, newline='', encoding='utf-8') as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 2)
            self.assertIn('doi', rows[0])
            self.assertIn('source', rows[0])

if __name__ == '__main__':
    unittest.main()
