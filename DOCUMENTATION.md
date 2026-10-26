# Bale-AI-Context-Packer Documentation



## Introduction
This document is the complete reference for Bale. It covers every command and option, the exact rules for how files are selected, the list of protected secret files, troubleshooting, and a development guide for contributors. For installation and everyday use, see the [README](README.md).

| Section                                                          | What It Covers                                  |
| :--------------------------------------------------------------- | :---------------------------------------------- |
| [Installing from Source](#installing-from-source)                | Installing from a clone or running without pip  |
| [Command Reference](#command-reference)                          | Every command, option and pattern               |
| [How Files Are Selected](#how-files-are-selected)                | What is included, skipped and why               |
| [Secret Files](#secret-files)                                    | The files Bale never reads by default           |
| [Output Location](#output-location)                              | Where Bale writes its results                   |
| [Bundle Format](#bundle-format)                                  | The structure of `.bale/bundle.md`              |
| [Exit Codes](#exit-codes)                                        | What each exit status means                     |
| [Troubleshooting](#troubleshooting)                              | Common problems and solutions                   |
| [Upgrading & Uninstalling](#upgrading--uninstalling)             | Keeping Bale up to date or removing it          |
| [Development](#development)                                     | Setup, tests, project structure and releases    |



## Installing from Source
### Method A: Install from a Clone
```
git clone https://github.com/Khana-Badosh/Bale-AI-Context-Packer
cd Bale-AI-Context-Packer
python -m pip install .
```
Use an editable install if you intend to change the code. Edits then take effect immediately:
```
python -m pip install -e ".[dev]"
```
### Method B: Run Without Installing
Run the package directly from a clone. The `pathspec` package must be installed first.
```
python -m pip install pathspec
```
Then, on macOS and Linux:
```
PYTHONPATH=src python3 -m bale tree
```
Or, on Windows (PowerShell):
```
$env:PYTHONPATH = "src"; py -m bale tree
```



## Command Reference
```
bale <command> [project-folder] [options]
```
The project folder defaults to the current directory. Run `bale <command> --help` to see the same information in the terminal.
### bale tree
Prints a directory tree. Folders are listed before files, and both are sorted alphabetically. The tree is printed to the terminal unless `-o` or `--copy` is given.

| Option                     | Description                                                        |
| :------------------------- | :----------------------------------------------------------------- |
| `-d N`, `--depth N`        | Limit the tree to `N` levels                                       |
| `--dirs-only`              | Show folders only                                                  |
| `--ascii`                  | Use plain ASCII characters instead of box-drawing symbols and emoji |
| `--no-header`              | Omit the `Project Structure` heading                               |
| `-o FILE`, `--output FILE` | Write to `FILE` instead of the terminal                            |
| `--copy`                   | Copy to the clipboard instead of printing                          |

If the clipboard is unavailable, the tree is printed to the terminal so the result is never lost.
### bale bundle
Writes one Markdown document containing the directory tree and the contents of every text file. See [Bundle Format](#bundle-format) for the layout.

| Option                     | Description                                                                |
| :------------------------- | :------------------------------------------------------------------------- |
| `-o FILE`, `--output FILE` | Save to `FILE` instead of `.bale/bundle.md`                                |
| `--stdout`                 | Print to the terminal instead of saving a file. Cannot be combined with `-o` |
| `--copy`                   | Also copy the result to the clipboard. The file is still saved             |
| `--no-tree`                | Omit the directory tree section                                            |
| `--include PATTERN`        | Include only files matching the pattern. Can be repeated                   |
| `--max-size KB`            | Skip files larger than `KB` kilobytes (default: `1024`)                    |
| `--include-lockfiles`      | Include lockfiles such as `pnpm-lock.yaml`                                 |
| `--include-secrets`        | Include credential files. See [Secret Files](#secret-files)                |

Examples:
```
bale bundle --include "src/" --include "package.json"
bale bundle --ignore "*.sql" --ignore "migrations/"
bale bundle --max-size 200
bale bundle --stdout | less
```
### bale flatten
Copies every file into one folder with no subdirectories. Original files are never modified.

| Option                                                                  | Description                                                                                                |
| :---------------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------------- |
| `-o DIR`, `--output DIR`                                                | Use `DIR` as the destination instead of `.bale/flat/`                                                      |
| `--names {path,name}`                                                   | `path` (default) names files `src__app.js`. `name` keeps `app.js` and appends `_1`, `_2` on name clashes   |
| `--clean`                                                               | With `-o`: empty the destination first. Works only on folders created by a previous `bale flatten`         |
| `--dry-run`                                                             | List what would be copied without writing anything                                                         |
| `--include-binary`                                                      | Also copy images and other binary files                                                                    |
| `--include`, `--max-size`, `--include-lockfiles`, `--include-secrets`   | Same behaviour as for `bundle`                                                                             |

#### Destination Rules
- The default `.bale/flat/` folder is replaced on every run.
- A custom `-o` folder must be empty, unless `--clean` is given.
- `--clean` only operates on folders that `bale flatten` created. Bale identifies them by a marker file named `.bale-flatten`. Any other folder is refused, so a mistyped path cannot delete unrelated files.
- The destination cannot be the project folder or one of its parent folders.
### Options Common to All Commands
| Option               | Description                                          |
| :------------------- | :--------------------------------------------------- |
| `--ignore PATTERN`   | Skip files and folders matching a pattern. Can be repeated |
| `--no-gitignore`     | Do not read `.gitignore` files                       |
| `--no-defaults`      | Do not apply the built-in ignore list                |
| `-q`, `--quiet`      | Suppress the summary                                 |
| `--version`          | Print the version and exit                           |
| `-h`, `--help`       | Show help                                            |
### Patterns
`--ignore` and `--include` use `.gitignore` syntax.

| Pattern     | Matches                                      |
| :---------- | :------------------------------------------- |
| `*.log`     | Any `.log` file                              |
| `docs/`     | The `docs` folder and everything inside it   |
| `/build`    | The `build` folder at the project root only  |
| `!keep.txt` | An exception to an earlier pattern           |



## How Files Are Selected
Bale decides what to include in three stages.
### 1. Always Excluded
- `.git`, `.hg`, `.svn` and `.bale`.
### 2. Excluded Unless You Opt Out
| What                                                                                                                                                           | Opt Out With            |
| :------------------------------------------------------------------------------------------------------------------------------------------------------------- | :---------------------- |
| Anything matched by `.gitignore`, including nested files, a parent repository's file and `!` exceptions                                                        | `--no-gitignore`        |
| Dependency, cache, build and editor folders: `node_modules`, `.venv`, `venv`, `__pycache__`, `dist`, `build`, `target`, `out`, `.next`, `.nuxt`, `coverage`, `.idea`, `.vscode`, `*.egg-info` and similar | `--no-defaults` |
| Patterns you provide                                                                                                                                           | Remove the `--ignore` flag |
### 3. Excluded from File Contents Only
These still appear in `bale tree`, but their contents are not read by `bale bundle` or `bale flatten`.

| What                                                                                                      | Include With                          |
| :-------------------------------------------------------------------------------------------------------- | :------------------------------------ |
| [Secret files](#secret-files)                                                                             | `--include-secrets`                   |
| Lockfiles: `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `Cargo.lock`, `poetry.lock`, `go.sum` and others | `--include-lockfiles`            |
| Binary files: images, archives, PDFs, executables, or anything containing null bytes                      | `--include-binary` (`flatten` only)   |
| Files larger than 1 MB                                                                                    | `--max-size KB`                       |
| Empty files and symbolic links                                                                            | Not configurable                      |

Each run reports what was skipped, so nothing is dropped silently:
```
Skipped: 1 secret (.env); 2 binary; 1 lockfile
```



## Secret Files
Bale never reads the following files unless `--include-secrets` is passed. This holds even when `--no-gitignore` is set.
- `Environment files:` `.env` and `.env.*` (such as `.env.local` and `.env.production`). Templates named `.env.example`, `.env.sample`, `.env.template` and `.env.dist` are not treated as secrets.
- `Keys and certificates:` `*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.jks` and `*.keystore`.
- `SSH keys:` `id_rsa`, `id_dsa`, `id_ecdsa` and `id_ed25519`.
- `Package manager credentials:` `.npmrc`, `.pypirc` and `.netrc`.
- `Other credential files:` `credentials.json`, `secrets.json`, `*.tfstate` and `*.tfvars`.

When a secret file is skipped, Bale names it:
```
Skipped: 1 secret (.env)
  Secret files are excluded by default. Use --include-secrets to override.
```
> [!IMPORTANT]
> Detection is based on file names only. A credential written into an ordinary source file cannot be detected, so review the output before sharing it. The `--include` option does not override this protection. Only `--include-secrets` does.



## Output Location
Everything Bale writes goes into a `.bale/` folder inside the project:
```
my-project/
├── .bale/
│   ├── .gitignore       Contains "*", so git ignores the whole folder
│   ├── bundle.md        Created by bale bundle
│   └── flat/            Created by bale flatten
└── ...
```
- Nothing is written to Downloads, your home directory, or anywhere outside the project, unless you pass `-o` with such a path.
- `.bale/` is excluded from git by its own `.gitignore`. Your project's `.gitignore` is not modified.
- `.bale/` is never scanned, so running `bale bundle` twice does not include the previous bundle.
- It is safe to delete at any time.



## Bundle Format
The bundle begins with the project name and the directory tree, followed by each file under its relative path:
````
# notes-app

## Directory structure

```text
├── public
│   ├── index.html
│   └── logo.png
├── src
│   └── index.js
...
```

## Files

### src/index.js

```js
import { Home } from "./pages/Home";
```
````
If a file contains triple backticks, the surrounding fence is lengthened so the document stays valid. The summary and token estimate (characters ÷ 4) are printed to the terminal and are never written into the file.



## Exit Codes
| Code | Meaning                         |
| :--- | :------------------------------ |
| `0`  | Success                         |
| `1`  | Error. A message is printed     |
| `2`  | Invalid command-line usage      |



## Troubleshooting
| Problem                                                    | Cause and Solution                                                                                                                                                                                  |
| :--------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `bale: command not found` or `'bale' is not recognized`    | The install folder is not on your `PATH`. Restart the terminal. With pipx, run `pipx ensurepath` and restart. Alternatively, run `python -m bale` (`py -m bale` on Windows), which does not depend on `PATH`. |
| `python` is not recognized (Windows)                       | Use the launcher: `py -m pip install ...` and `py -m bale ...`. If `py` is also missing, reinstall Python with **Add python.exe to PATH** enabled.                                                  |
| `git` is not recognized                                    | Git is required to install straight from GitHub. Install it, or download the ZIP and run `pipx install .` inside the extracted folder.                                                              |
| `error: externally-managed-environment`                    | Your system Python blocks global `pip` installs. Use pipx or uv instead.                                                                                                                            |
| `requires a different Python`                              | Python is older than 3.8. Upgrade it, or let uv fetch one: `uv tool install --python 3.12 git+https://github.com/Khana-Badosh/Bale-AI-Context-Packer`.                                              |
| `could not copy to clipboard`                              | On Linux, install `xclip` (X11) or `wl-clipboard` (Wayland). macOS and Windows need nothing extra. If copying fails, the result is printed to the terminal instead.                                 |
| Garbled characters in `bale tree` output                   | The terminal cannot display box-drawing characters. Use `bale tree --ascii`, or switch to Windows Terminal.                                                                                         |
| `destination ... is not empty`                             | The `-o` folder already contains files. Choose a new folder, or add `--clean` if it was created by an earlier `bale flatten`.                                                                       |
| `refusing to replace ...`                                  | The folder was not created by `bale flatten`, so Bale will not delete it. Remove it yourself or choose another path.                                                                                |
| A file is missing from the output                          | Check the `Skipped:` line. Then try `--no-gitignore`, `--no-defaults`, `--include-lockfiles` or a larger `--max-size`.                                                                              |
| The bundle is too large for the AI                         | Run `bale tree` to decide what matters, then narrow the bundle with `--include`, `--ignore` or a lower `--max-size`, or bundle a sub-folder. Check the token estimate after each run.                |



## Upgrading & Uninstalling
| Installed With | Upgrade                                                                                       | Uninstall                      |
| :------------- | :-------------------------------------------------------------------------------------------- | :----------------------------- |
| With pipx      | `pipx upgrade bale`                                                                           | `pipx uninstall bale`          |
| With uv        | `uv tool upgrade bale`                                                                        | `uv tool uninstall bale`       |
| With pip       | `python -m pip install --upgrade git+https://github.com/Khana-Badosh/Bale-AI-Context-Packer`  | `python -m pip uninstall bale` |

Delete any remaining `.bale/` folders manually. They contain only generated output.



## Development
This section is for anyone who wants to change Bale's code, run its tests or publish a new version.
### Prerequisites
#### Software Requirements
1.  `Python 3.8 or newer:` Bale supports every version from 3.8 onwards.
    * Download from [python.org](https://www.python.org/downloads/).
2.  `Git:` Used to clone the repository and to publish releases.
    * Download from [git-scm.com](https://git-scm.com/downloads).
3.  `uv (Optional):` Downloads other Python versions so you can test on 3.8 without installing it system-wide.
    * Install instructions are on [docs.astral.sh/uv](https://docs.astral.sh/uv/).
### 1. Get the Source Code
```
git clone https://github.com/Khana-Badosh/Bale-AI-Context-Packer
cd Bale-AI-Context-Packer
```
### 2. Create a Virtual Environment and Install
A virtual environment keeps the development install separate from your other Python projects.
- On macOS and Linux:
  ```
  python3 -m venv .venv
  source .venv/bin/activate
  ```
- On Windows (PowerShell):
  ```
  py -m venv .venv
  .venv\Scripts\Activate.ps1
  ```
Then install Bale in editable mode with the test dependencies:
```
python -m pip install -e ".[dev]"
```
Confirm that it worked:
```
bale --version
```
> [!TIP]
> In editable mode, changes to the files in `src/bale/` take effect immediately. There is no need to reinstall.
### 3. Run the Tests
```
python -m pytest
```
The tests use only Python's built-in `unittest` module, so they also run without pytest installed.

On macOS and Linux:
```
PYTHONPATH=src:tests python -m unittest discover -s tests
```
On Windows (PowerShell):
```
$env:PYTHONPATH = "src;tests"; python -m unittest discover -s tests
```
| Test File               | What It Checks                                                                                  |
| :---------------------- | :---------------------------------------------------------------------------------------------- |
| `tests/test_rules.py`   | Secret detection, default ignores, lockfiles and binary detection                               |
| `tests/test_walk.py`    | Folder scanning, `.gitignore` handling (nested, negated and anchored patterns) and file filters |
| `tests/test_commands.py`| The tree, bundle and flatten output, destination safety checks and the command-line interface   |
| `tests/helpers.py`      | Shared fixtures, including a sample project with a `.env` file and a nested `.gitignore`        |
> [!IMPORTANT]
> The secret-protection tests must always pass. They prove that `.env` files and keys stay out of the output, even when `.gitignore` is disabled.
### 4. Test on Older Python Versions
Bale declares support for Python 3.8, so test on it before releasing. With uv:
```
uv python install 3.8
uv venv --python 3.8 .venv38
uv pip install --python .venv38/bin/python -e ".[dev]"
.venv38/bin/python -m pytest
```
On Windows, replace `.venv38/bin/python` with `.venv38\Scripts\python`. The installer picks the newest `pathspec` release that supports the Python version in use.
### Project Structure
```
Bale-AI-Context-Packer/
├── src/
│ └── bale/
│   ├── __init__.py                      Package version
│   ├── __main__.py                      Enables python -m bale
│   ├── cli.py                           Argument parsing and the three command handlers
│   ├── walk.py                          .gitignore-aware folder scan and content filtering
│   ├── rules.py                         Built-in ignores, secret patterns, binary detection
│   ├── tree.py                          Tree rendering
│   ├── bundle.py                        Markdown bundle builder
│   ├── flatten.py                       Flat-copy logic and destination safety checks
│   └── util.py                          Clipboard, token estimate and path helpers
│
├── tests/
│ ├── helpers.py                         Shared fixtures
│ ├── test_rules.py                      Rule and detection tests
│ ├── test_walk.py                       Scanner and filter tests
│ └── test_commands.py                   Command and command-line tests
│
├── .github/
│ └── workflows/
│   └── tests.yml                        Runs the tests on every push
│
├── DOCUMENTATION.md                     This file
├── LICENSE
├── pyproject.toml                       Package metadata and the bale command
└── README.md
```
### How the Code Fits Together
1. `cli.py` parses the command line and picks the command handler.
2. `walk.scan()` walks the project folder and builds a tree, applying `.gitignore` files, the built-in ignores from `rules.py` and any `--ignore` patterns.
3. `walk.collect_files()` filters the tree down to the files whose contents may be read, and records why each other file was skipped.
4. `tree.py`, `bundle.py` or `flatten.py` turns the result into output.
5. `cli.py` saves or prints the output and prints the summary.
### Making Common Changes
#### Adding an Ignored Folder
1. Open `src/bale/rules.py` and add the folder name to `DEFAULT_IGNORE_DIRS`:
```python
DEFAULT_IGNORE_DIRS = frozenset(
    {
        # existing entries...
        "my_build_output",
    }
)
```
2. Add a check to `DefaultIgnoreTests` in `tests/test_rules.py`.
3. Run the tests.
#### Adding a Secret File Pattern
1. Add a lowercase pattern to `SECRET_PATTERNS` in `src/bale/rules.py`. Patterns use `fnmatch` syntax and are matched against the lowercase file name.
```python
SECRET_PATTERNS = (
    # existing entries...
    "*.secret",
)
```
2. If a template file with a matching name should stay visible, add its exact name to `SECRET_SAFE`.
3. Add the new name to `SecretTests` in `tests/test_rules.py`, then run the tests.
#### Adding a Lockfile or Binary Extension
1. Add the file name to `LOCKFILES`, or the extension (with its leading dot) to `BINARY_EXTENSIONS`, in `src/bale/rules.py`.
2. Add a check to `tests/test_rules.py` and run the tests.
#### Adding a Code Fence Language
1. Add the extension and its Markdown language name to `LANGUAGES` in `src/bale/bundle.py`:
```python
LANGUAGES = {
    # existing entries...
    ".lua": "lua",
}
```
### Python 3.8 Compatibility Rules
Follow these rules so Bale keeps working on older Python versions.
- `Path.write_text(newline=...):` Not available before Python 3.10. Use `write_text_file()` from `util.py`.
- `Path.resolve()` on paths that do not exist yet: Behaves differently on Windows before Python 3.10. Use `abspath()` from `util.py`.
- `Type hints:` Keep `from __future__ import annotations` at the top of each module and import generic types from `typing` (`List`, `Optional`), not the built-in `list[str]` form, anywhere it would be evaluated at runtime.
- `Newer syntax:` Avoid `match` statements, `X | Y` type unions at runtime and `str.removeprefix()`.
- `Dependencies:` `pathspec` is the only runtime dependency. Avoid adding another.
### Continuous Integration
The workflow in `.github/workflows/tests.yml` runs on every push to `main` and on every pull request.
- Operating systems: Linux, Windows and macOS.
- Python versions: 3.9 and 3.13 on all three systems, plus 3.8 on Ubuntu 22.04 and Windows. The latest macOS and Ubuntu runners no longer provide Python 3.8.
- Each job installs Bale with `python -m pip install -e ".[dev]"` and runs `python -m pytest`.
### Releasing a New Version
1. Update the version number in both places:
   * `version` in `pyproject.toml`
   * `__version__` in `src/bale/__init__.py`
2. Run the tests, then commit the change:
```
git add .
git commit -m "Release 0.1.1"
```
3. Tag the release and push it:
```
git tag v0.1.1
git push origin main --tags
```
4. On GitHub, open **Releases**, click **Draft a new release**, choose the tag and publish it.
