import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from services.models import ModelError, find_file, find_ollama, import_gguf, ollama_name, scan, validate  # noqa: E402

GGUF = b"GGUF\x03\x00\x00\x00"


class ModelsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def write(self, name, data=GGUF):
        (path := self.dir / name).parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def test_ollama_name(self):
        self.assertEqual(ollama_name("Qwen2.5-7B.Q4_K_M.gguf"), "qwen2.5-7b.q4_k_m")
        self.assertEqual(ollama_name("big-00001-of-00002.gguf"), "big")

    def test_find_ollama(self):
        names = ["llama3:latest", "qwen:7b", "qwen:14b"]
        self.assertEqual(find_ollama("llama3", names), "llama3:latest")
        self.assertEqual(find_ollama("Llama3.gguf", names), "llama3:latest")
        self.assertEqual(find_ollama("LLAMA3", names), "llama3:latest")
        self.assertEqual(find_ollama("Qwen:7B", names), "qwen:7b")
        self.assertIsNone(find_ollama("mistral", names))
        with self.assertRaises(ModelError):
            find_ollama("qwen", names)

    def test_scan_and_find(self):
        self.write("A.gguf")
        self.write("sub/big-00001-of-00002.gguf")
        self.write("sub/big-00002-of-00002.gguf")
        self.write("mmproj-a.gguf")
        self.write("C.GGUF")
        groups = scan(self.dir)
        self.assertEqual(list(groups), ["A.gguf", "C.GGUF", "big.gguf"])
        self.assertEqual(len(groups["big.gguf"]), 2)
        self.assertEqual(find_file("a", self.dir)[0], "A.gguf")
        self.assertEqual(find_file("big-00002-of-00002.gguf", self.dir)[0], "big.gguf")
        direct = find_file(str(self.dir / "sub/big-00001-of-00002.gguf"), self.dir)
        self.assertEqual((direct[0], len(direct[1])), ("big.gguf", 2))
        with self.assertRaises(ModelError):
            scan(self.dir / "nao-existe")

    def test_validate(self):
        for name, data in [("html.gguf", b"<html>"), ("vazio.gguf", b"")]:
            with self.assertRaises(ModelError):
                validate([self.write(name, data)])
        with self.assertRaisesRegex(ModelError, "1 de 3"):
            validate([self.write("x-00001-of-00003.gguf")])


    def test_unreadable_file_is_model_error(self):
        path = self.write("sem-permissao.gguf")
        path.chmod(0)
        self.addCleanup(path.chmod, 0o644)
        with self.assertRaisesRegex(ModelError, "Não foi possível ler"):
            import_gguf(path.name, [path])


if __name__ == "__main__":
    unittest.main()
