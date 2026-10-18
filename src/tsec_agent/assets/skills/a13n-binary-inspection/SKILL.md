---
name: a13n-binary-inspection
description: Inspect assigned native binaries with file, GNU binutils, GDB, and pwntools to establish format, architecture, dependencies, and reproducible runtime observations.
---

# Binary Inspection

Identify the artifact before selecting tools. For an ELF binary, begin with static
inspection and keep the original intact:

```sh
file sample
readelf -h -l -d sample
objdump -f sample
```

Use symbol tables, relocations, and targeted string searches to narrow the code or
data worth examining. Account for architecture, byte order, stripping, dynamic
linker paths, and missing libraries before interpreting execution failures.

Use `python` from PATH for pwntools. Choose explicit packing widths and endianness;
do not assume a host-native layout. A minimal metadata check is:

```python
from pwnlib.elf import ELF

artifact = ELF("sample", checksec=False)
print(artifact.arch, artifact.bits, artifact.endian)
```

Run an artifact only when execution is part of the assigned task. Prefer batch GDB
with a finite command sequence for reproducible observations. A failed attach or
trace may be a deployment permission restriction rather than a binary property.
The image does not grant ptrace privileges or provide every architecture's runtime.

Save derived files and scripts in the workspace. Report the observed addresses,
inputs, tool versions, and execution conditions needed to reproduce a conclusion;
distinguish static deductions from runtime confirmation.
