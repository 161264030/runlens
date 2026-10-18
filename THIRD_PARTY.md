# Third-party dependencies

Runtime: Python standard library only. No vendored code.

Build: setuptools 80.9.0 (MIT).

Development: pytest 8.3.5 (MIT), Ruff 0.11.13 (MIT), mypy 1.15.0 (MIT).
Transitive dependencies pinned in constraints-dev.txt: iniconfig (MIT), packaging
(Apache-2.0/BSD-2-Clause), pluggy (MIT), typing_extensions (PSF-2.0),
mypy_extensions (MIT), exceptiongroup (MIT), tomli (MIT), colorama (BSD-3-Clause).

Future external capture tools: strace (LGPL-2.1-or-later), readelf from GNU
binutils (GPL-3.0-or-later). M0 only checks their presence on PATH.
