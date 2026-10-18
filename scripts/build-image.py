"""Build and verify the container, optionally exporting the verified image."""

import argparse
import hashlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="a13n-cyber:dev")
    parser.add_argument("--python-base-image", default="python:3.13-slim-bookworm")
    parser.add_argument("--export", action="store_true")
    parser.add_argument("--rea", action="store_true", help="Include REA and Ghidra")
    args = parser.parse_args(argv)
    base_image = args.image + "-base" if args.rea else args.image

    subprocess.run(
        [
            "docker",
            "build",
            "--platform",
            "linux/amd64",
            "--build-arg",
            f"PYTHON_BASE_IMAGE={args.python_base_image}",
            "-t",
            base_image,
            ".",
        ],
        cwd=ROOT,
        check=True,
    )
    if args.rea:
        subprocess.run(
            [
                "docker",
                "build",
                "--platform",
                "linux/amd64",
                "-f",
                "Dockerfile.rea",
                "--build-arg",
                f"CYBER_BASE_IMAGE={base_image}",
                "-t",
                args.image,
                ".",
            ],
            cwd=ROOT,
            check=True,
        )
    subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "-e",
            "LLM_BASE_URL=http://127.0.0.1:9/v1",
            "-e",
            "LLM_MODEL=offline-check",
            "-e",
            "LLM_API_KEY=offline-check",
            args.image,
            "doctor",
        ],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--entrypoint",
            "python",
            args.image,
            "/app/scripts/check-image.py",
        ],
        cwd=ROOT,
        check=True,
    )
    if args.rea:
        subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "--entrypoint",
                "python",
                args.image,
                "/app/scripts/check-rea.py",
            ],
            cwd=ROOT,
            check=True,
        )
    if args.export:
        archive = ROOT / "dist" / "a13n-cyber.tar"
        archive.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["docker", "image", "save", "-o", str(archive), args.image],
            cwd=ROOT,
            check=True,
        )
        with archive.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        print(f"{digest}  {archive}")


if __name__ == "__main__":
    main()
