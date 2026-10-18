# Container Toolkit

## Packaging

The Linux amd64 image includes the application, uv, the locked `toolkit` Python extra, and Debian's signed packages for the basic CLI toolchain. Python dependencies remain in `uv.lock`; the toolkit extra pins pwntools. The image records installed OS package versions in `/usr/local/share/a13n-cyber/system-packages.tsv`. The manifest describes the built image; it does not pin subsequent Debian repository resolution.

The toolchain includes Bash, curl, jq, Git, ripgrep, file, tar, unzip, zip, OpenSSL, xxd, netcat, Nmap, ffuf, GNU binutils, GDB, GCC, and Make. Python and pwntools share the application's virtual environment, which is first on PATH. No CLI installs packages or contacts an evaluation target during container startup. Browser automation and template scanners are separate extensions, not dependencies of the basic image.

The optional [REA image](04-rea.md) extends this base with its own locked tool integration and decompiler.

Model and platform credentials are supplied only at runtime. The image's default command remains CLI help. Installing tools does not grant additional container capabilities; restricted debugging or raw-packet operations may be unavailable in the deployment environment.

## Built-in Skills

The package owns `assets/skills/` and `assets/toolkit.json`. Package data is included in wheels and editable source installs. These assets are mounted through Harness as the file-only `builtin` Environment with a read-only permission ceiling in both general and benchmark modes. Skill bodies and supporting files are loaded on demand through ordinary Harness file tools.

The three built-in skills cover toolkit selection, bounded HTTP inspection, and binary inspection. They are application-owned Agent Skills, independent of Claude plugins or other agent CLIs. The toolkit skill points to `/environment/builtin/toolkit.json`, whose tool and dependency lists describe the basic container rather than promising availability on arbitrary hosts. Project skills remain discoverable through the existing workspace/project mount. Skill names must be unique across both sources; conflicts fail preparation rather than silently changing instructions.

## Verification

`scripts/check-image.py` runs inside the image without model credentials or network access. It checks CLI executability, Python/pwntools imports and harmless packing/ELF/assembler operations, the packaged skill catalog, reading a built-in skill through native Harness tools, denial of file mutations on the built-in mount, and shell execution through Harness using an offline model.

`uv run --locked python scripts/build-image.py` builds the image from the repository root regardless of the caller's working directory, runs `doctor` with explicit offline configuration, and executes the toolkit check with `--network none`. Any failed command stops the workflow. `--image` selects the image tag and `--python-base-image` selects the Python base image. `--export` saves `dist/a13n-cyber.tar` and prints its SHA256 digest only after both checks succeed.
