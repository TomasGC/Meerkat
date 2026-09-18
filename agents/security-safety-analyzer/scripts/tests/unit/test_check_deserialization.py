"""Unit tests for checkers/check_deserialization.py — mechanical layer only (server patched off)."""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from checkers import check_deserialization


def _run(tmp_path: Path, name: str, content: str, language: str) -> list[dict]:
    f = tmp_path / name
    f.write_text(content)
    with patch("lib.engine.hybrid.check_server_available", return_value=False):
        result = check_deserialization.run(tmp_path, language, files=[f])
    assert result["success"] is True
    assert result["principle"] == "Deserialization"
    return result["violations"]


class TestPythonChecks:
    def test_detects_pickle_loads(self, tmp_path):
        v = _run(tmp_path, "load.py", "obj = pickle.loads(payload)\n", "python")
        assert any("remote code execution" in x["message"] for x in v)

    def test_detects_marshal_loads(self, tmp_path):
        v = _run(tmp_path, "load.py", "obj = marshal.loads(blob)\n", "python")
        assert v and v[0]["severity"] == "high"

    def test_detects_shelve_open(self, tmp_path):
        v = _run(tmp_path, "store.py", "db = shelve.open('cache')\n", "python")
        assert v and v[0]["severity"] == "medium"

    def test_detects_unsafe_yaml_load(self, tmp_path):
        v = _run(tmp_path, "cfg.py", "cfg = yaml.load(stream)\n", "python")
        assert any("SafeLoader" in x["message"] for x in v)

    def test_safe_loader_is_clean(self, tmp_path):
        code = "cfg = yaml.load(stream, Loader=yaml.SafeLoader)\n"
        assert _run(tmp_path, "cfg.py", code, "python") == []

    def test_safe_load_helper_is_clean(self, tmp_path):
        assert _run(tmp_path, "cfg.py", "cfg = yaml.safe_load(stream)\n", "python") == []

    def test_detects_xml_entity_resolution(self, tmp_path):
        v = _run(tmp_path, "parse.py", "doc = etree.fromstring(body)\n", "python")
        assert any("XXE" in x["message"] for x in v)

    def test_hardened_parser_is_clean(self, tmp_path):
        code = "doc = etree.fromstring(body, resolve_entities=False)\n"
        assert _run(tmp_path, "parse.py", code, "python") == []

    def test_json_loads_is_clean(self, tmp_path):
        assert _run(tmp_path, "load.py", "obj = json.loads(payload)\n", "python") == []


class TestCSharpChecks:
    def test_detects_binary_formatter(self, tmp_path):
        v = _run(tmp_path, "Load.cs", "var f = new BinaryFormatter();\n", "csharp")
        assert any("remote code execution" in x["message"] for x in v)

    def test_detects_permissive_type_name_handling(self, tmp_path):
        code = "settings.TypeNameHandling = TypeNameHandling.All;\n"
        v = _run(tmp_path, "Json.cs", code, "csharp")
        assert any("TypeNameHandling" in x["message"] for x in v)

    def test_type_name_handling_none_is_clean(self, tmp_path):
        code = "settings.TypeNameHandling = TypeNameHandling.None;\n"
        assert _run(tmp_path, "Json.cs", code, "csharp") == []

    def test_detects_dtd_processing_parse(self, tmp_path):
        v = _run(tmp_path, "Xml.cs", "settings.DtdProcessing = DtdProcessing.Parse;\n", "csharp")
        assert any("XXE" in x["message"] for x in v)

    def test_detects_xml_url_resolver(self, tmp_path):
        v = _run(tmp_path, "Xml.cs", "reader.XmlResolver = new XmlUrlResolver();\n", "csharp")
        assert any("XXE" in x["message"] for x in v)


class TestJavaScriptChecks:
    def test_detects_node_serialize(self, tmp_path):
        v = _run(tmp_path, "load.js", "const s = require('node-serialize');\n", "javascript")
        assert any("remote code execution" in x["message"] for x in v)

    def test_detects_eval_of_request_payload(self, tmp_path):
        v = _run(tmp_path, "load.js", "const data = eval(req.body.payload);\n", "javascript")
        assert any("evaluated as code" in x["message"] for x in v)

    def test_detects_entity_expansion_enabled(self, tmp_path):
        v = _run(tmp_path, "xml.js", "libxml.parseXml(body, { noent: true });\n", "javascript")
        assert any("XXE" in x["message"] for x in v)

    def test_typescript_shares_javascript_rules(self, tmp_path):
        v = _run(tmp_path, "load.ts", "const s = unserialize(payload);\n", "typescript")
        assert v and v[0]["severity"] == "high"

    def test_json_parse_is_clean(self, tmp_path):
        assert _run(tmp_path, "load.js", "const data = JSON.parse(body);\n", "javascript") == []


class TestOtherLanguages:
    def test_detects_import_clixml(self, tmp_path):
        v = _run(tmp_path, "load.ps1", "$obj = Import-Clixml -Path $file\n", "powershell")
        assert v and v[0]["principle"] == "Deserialization"

    def test_detects_psserializer_deserialize(self, tmp_path):
        code = "$o = [System.Management.Automation.PSSerializer]::Deserialize($xml)\n"
        v = _run(tmp_path, "load.ps1", code, "powershell")
        assert len(v) == 1

    def test_detects_gob_decoder(self, tmp_path):
        v = _run(tmp_path, "load.go", "dec := gob.NewDecoder(conn)\n", "go")
        assert v and v[0]["severity"] == "medium"

    def test_go_json_decoder_is_clean(self, tmp_path):
        assert _run(tmp_path, "load.go", "dec := json.NewDecoder(r.Body)\n", "go") == []
