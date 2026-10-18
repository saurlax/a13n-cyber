import hashlib
import io
import json
import runpy
import subprocess
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent


class PackagingTests(unittest.TestCase):
    def test_rea_check_failure_prevents_image_export(self):
        main = runpy.run_path(str(ROOT / "scripts/build-image.py"))["main"]
        with patch("subprocess.run") as run:
            run.side_effect = [
                None,
                None,
                None,
                None,
                subprocess.CalledProcessError(1, "check-rea"),
            ]
            with self.assertRaises(subprocess.CalledProcessError):
                main(["--rea", "--image", "fixture:rea", "--export"])
        commands = [call.args[0] for call in run.call_args_list]
        self.assertIn("fixture:rea-base", commands[0])
        self.assertIn("CYBER_BASE_IMAGE=fixture:rea-base", commands[1])
        self.assertEqual(commands[-1][-1], "/app/scripts/check-rea.py")
        for command in commands[2:]:
            self.assertEqual(command[3:5], ["--network", "none"])
        self.assertFalse(
            any(command[:3] == ["docker", "image", "save"] for command in commands)
        )

    def test_ghidra_checksum_is_verified_before_installation(self):
        main = runpy.run_path(str(ROOT / "scripts/install-ghidra.py"))["main"]
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as bundle:
            bundle.writestr(
                "ghidra_fixture/support/analyzeHeadless", "fixture launcher"
            )
        contents = archive.getvalue()
        with TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifest.json"
            destination = root / "installed"
            manifest = {
                "url": "https://example.test/fixture.zip",
                "directory": "ghidra_fixture",
                "sha256": "incorrect",
            }
            manifest_path.write_text(json.dumps(manifest))
            with patch("urllib.request.urlopen", return_value=io.BytesIO(contents)):
                with self.assertRaisesRegex(RuntimeError, "checksum mismatch"):
                    main([str(manifest_path), str(destination)])
            self.assertFalse(destination.exists())
            manifest["sha256"] = hashlib.sha256(contents).hexdigest()
            manifest_path.write_text(json.dumps(manifest))
            with patch("urllib.request.urlopen", return_value=io.BytesIO(contents)):
                main([str(manifest_path), str(destination)])
            self.assertEqual(
                (destination / "support/analyzeHeadless").read_text(),
                "fixture launcher",
            )
