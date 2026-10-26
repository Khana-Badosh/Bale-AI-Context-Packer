# Bale - AI Context Packer



## Introduction
Bale is a command-line tool that packs a project folder into something an AI assistant can use. It can print a directory tree, combine every source file into one Markdown document, or copy all files into a single flat folder for upload. It follows your `.gitignore`, skips build output, lockfiles and binaries, and never includes credential files such as `.env`.
```
$ bale bundle
Saved bundle to .bale/bundle.md
Bundled 12 files · 1,181 chars · ≈295 tokens (rough estimate)
Skipped: 1 binary; 1 lockfile
```



## How It Works
```
Your project folder
│
├─ bale tree     → Prints the folder structure in the terminal
├─ bale bundle   → Saves everything as one Markdown file   (.bale/bundle.md)
└─ bale flatten  → Copies every file into one flat folder  (.bale/flat/)
```
1. Open a terminal in your project folder.
2. Run one of the three commands.
3. Bale reads your `.gitignore` and skips clutter such as `node_modules`, `dist`, lockfiles and images.
4. Credential files such as `.env` are always left out, and the summary names each one.
5. The result is saved in a `.bale/` folder inside your project. Git ignores that folder automatically.
6. Paste the bundle into your AI chat, or upload the files from the flat folder.

| Command        | Use It To                            | Output                      |
| :------------- | :----------------------------------- | :-------------------------- |
| `bale tree`    | See the project structure            | Printed in the terminal     |
| `bale bundle`  | Paste the whole project into a chat  | One file: `.bale/bundle.md` |
| `bale flatten` | Upload the project as separate files | One folder: `.bale/flat/`   |



## Prerequisites
#### Software Requirements
1.  `Python 3.8 or newer:` Bale is written in Python.
    * Download from [python.org](https://www.python.org/downloads/).
    * During installation, make sure to check **"Add python.exe to PATH"**.
    * Check your version by running `python --version` (`py --version` on Windows, `python3 --version` on macOS and Linux).
2.  `Git:` Needed only for the recommended install method, which downloads Bale directly from GitHub.
    * Download from [git-scm.com](https://git-scm.com/downloads).
    * Skip this if you plan to use Method B (Download ZIP) below.
3.  `pipx:` Installs command-line tools in isolated environments and puts them on your `PATH`. It is installed in Step 1 below.
#### Supported Systems
- `Windows, macOS and Linux:` Any terminal works, such as PowerShell, Windows Terminal, macOS Terminal or a Linux shell.
> [!TIP]
> Not sure whether Python is installed? Open a terminal and run `python --version`. A version number means you are ready.



## Step-by-Step Installation & Setup
Follow these steps to install Bale and confirm that it works.
### 1. Install pipx
Skip this step if `pipx --version` already prints a version number.

| System          | Commands                                                               |
| :-------------- | :--------------------------------------------------------------------- |
| Windows         | `py -m pip install --user pipx` <br> `py -m pipx ensurepath`           |
| Mac (macOS)     | `brew install pipx` <br> `pipx ensurepath`                             |
| Debian / Ubuntu | `sudo apt install pipx` <br> `pipx ensurepath`                         |
| Other Linux     | `python3 -m pip install --user pipx` <br> `python3 -m pipx ensurepath` |

> [!IMPORTANT]
> Close and reopen your terminal after running `ensurepath`. Otherwise the `PATH` change does not take effect.
### 2. Install Bale
- **Method A (Recommended, requires Git):**
  Open a terminal and run:
  ```
  pipx install git+https://github.com/Khana-Badosh/Bale-AI-Context-Packer
  ```
- **Method B (Without Git):**
  * Scroll to the top of this GitHub page.
  * Click the green **Code** button on the right side.
  * Click **Download ZIP** from the dropdown menu.
  * Extract the ZIP file into a folder.
  * Open a terminal inside the extracted folder (the one that contains `pyproject.toml`) and run:
  ```
  pipx install .
  ```
- **Method C (uv or pip):**
  If you prefer [uv](https://docs.astral.sh/uv/), run:
  ```
  uv tool install git+https://github.com/Khana-Badosh/Bale-AI-Context-Packer
  ```
  Or, with plain pip:
  ```
  python -m pip install --user git+https://github.com/Khana-Badosh/Bale-AI-Context-Packer
  ```
### 3. Verify the Installation
Run the following command in any terminal:
```
bale --version
```
If it prints `bale 0.1.0`, the installation was successful. If your terminal says the command was not found, see [Troubleshooting](#troubleshooting).



## Using Bale
Open a terminal **inside the project folder** you want to share, then run one of the commands below. To work on a different folder, add its path to the end of the command:
```
bale bundle ~/code/my-app
bale bundle "C:\Users\Me\code\my-app"
```
### 1. Print the Folder Structure (`bale tree`)
Prints a directory tree. Lockfiles, `.env` files and images are listed as well, so the AI sees the real structure of the project.
```
$ bale tree
📁 Project Structure: notes-app
├── public
│   ├── index.html
│   └── logo.png
├── src
│   ├── components
│   │   ├── Header.js
│   │   └── NoteList.js
│   ├── pages
│   │   ├── Home.js
│   │   └── Settings.js
│   ├── utils
│   │   └── format.js
│   └── index.js
├── tests
│   └── format.test.js
├── .env.example
├── .gitignore
├── package.json
├── pnpm-lock.yaml
└── README.md
```
| Command                      | Description                    |
| :--------------------------- | :----------------------------- |
| `bale tree -d 2`             | Limit the tree to two levels   |
| `bale tree --dirs-only`      | Show folders only              |
| `bale tree --copy`           | Copy the tree to the clipboard |
| `bale tree -o structure.txt` | Save the tree to a file        |
### 2. Bundle the Project into One File (`bale bundle`)
Combines the directory tree and the contents of every text file into a single Markdown document. Open `.bale/bundle.md`, copy its contents and paste them into your AI chat. Alternatively, add `--copy` to put the result on your clipboard automatically.
```
$ bale bundle
Saved bundle to .bale/bundle.md
Bundled 12 files · 1,181 chars · ≈295 tokens (rough estimate)
Skipped: 1 binary; 1 lockfile
```
| Command                        | Description                                  |
| :----------------------------- | :------------------------------------------- |
| `bale bundle`                  | Save the bundle to `.bale/bundle.md`         |
| `bale bundle --copy`           | Save the bundle and copy it to the clipboard |
| `bale bundle --include "*.js"` | Include only JavaScript files                |
| `bale bundle src`              | Bundle one sub-folder only                   |
| `bale bundle --stdout`         | Print to the terminal instead of saving      |
### 3. Flatten the Project into One Folder (`bale flatten`)
Copies every file into one folder with no subfolders, which suits AI tools that accept file uploads but not folders. Each file is named after its path, so names never collide. For example, `src/components/Header.js` becomes `src__components__Header.js`.
```
$ bale flatten
Copied 12 files into .bale/flat
Skipped: 1 binary; 1 lockfile
```
The resulting folder:
```
.bale/flat/
├── README.md
├── package.json
├── public__index.html
├── src__components__Header.js
├── src__components__NoteList.js
├── src__index.js
├── src__pages__Home.js
├── src__pages__Settings.js
├── src__utils__format.js
└── tests__format.test.js
```
| Command                         | Description                                     |
| :------------------------------ | :---------------------------------------------- |
| `bale flatten`                  | Copy all files into `.bale/flat/`               |
| `bale flatten --dry-run`        | Preview what would be copied without copying it |
| `bale flatten --include "*.js"` | Copy only JavaScript files                      |
| `bale flatten --names name`     | Keep original names (`Header.js`, `Home.js`)    |
> [!NOTE]
> Running `bale flatten` again replaces the previous result. Your original files are never modified. A small hidden file named `.bale-flatten` is also created in the folder so that Bale can replace it safely next time. Do not upload it.
### Options That Work Everywhere
| Option                | Description                                                 |
| :-------------------- | :---------------------------------------------------------- |
| `--include "PATTERN"` | Use only files that match, for example `--include "*.js"`   |
| `--ignore "PATTERN"`  | Leave out files that match, for example `--ignore "tests/"` |
| `--max-size KB`       | Skip files larger than this size (default: 1024)            |
| `-o PATH`             | Write the output to a different location                    |
| `-q`                  | Suppress the summary                                        |
| `--help`              | Show help, for example `bale bundle --help`                 |
> [!TIP]
> Patterns use `.gitignore` syntax. Wrap them in quotes so your terminal does not expand them.



## Understanding the Output
### The Summary Line
Every run prints a short summary to the terminal. It is never written into the output file.
- **Files bundled:** How many files were included.
- **Token estimate:** A rough size guide (characters ÷ 4) so you can tell whether the result fits in an AI chat. It is not an exact token count.
- **Skipped:** What was left out and why, for example `1 binary; 1 lockfile`.
### What Bale Leaves Out
- **Ignored files:** Anything matched by your `.gitignore`, plus folders such as `node_modules`, `dist`, `.venv` and caches.
- **Lockfiles and binary files:** `pnpm-lock.yaml`, images, archives and similar files are not read, although they still appear in the tree.
- **Large files:** Files over 1 MB.
- **Secret files:** `.env` files, private keys and similar credential files.
> [!IMPORTANT]
> Secret files are never included, even if you disable `.gitignore`. Every run names the secret files it skipped. Bale detects secrets by file name only, so a password pasted into an ordinary source file cannot be detected. Review the output before sharing it.
### Where the Output Is Saved
- **Inside your project:** Everything goes into a `.bale/` folder in the project you ran Bale on.
- **Ignored by git:** The folder contains its own `.gitignore`, so your repository stays clean. Your own `.gitignore` is never edited.
- **Never in Downloads:** Nothing is written outside the project unless you choose a path with `-o`.
- **Safe to delete:** `.bale/` only contains generated output.



## Troubleshooting
| Problem                                 | Solution                                                                                                               |
| :-------------------------------------- | :--------------------------------------------------------------------------------------------------------------------- |
| `bale: command not found`               | Restart the terminal. With pipx, run `pipx ensurepath` and restart. Or run `python -m bale` (`py -m bale` on Windows). |
| `python` is not recognized (Windows)    | Use `py` instead of `python`. If `py` is also missing, reinstall Python with **Add python.exe to PATH** enabled.       |
| `error: externally-managed-environment` | Your system Python blocks global `pip` installs. Use pipx or uv instead.                                               |
| `git` is not recognized                 | Install Git, or use Method B (Download ZIP) in the installation steps.                                                 |
| A file is missing from the output       | Read the `Skipped:` line printed after each run.                                                                       |
| `could not copy to clipboard` (Linux)   | Install `xclip` or `wl-clipboard`. The result is printed to the terminal instead.                                      |
> [!TIP]
> More problems and fixes are listed in [DOCUMENTATION.md](DOCUMENTATION.md#troubleshooting).



## Documentation
[DOCUMENTATION.md](DOCUMENTATION.md) covers every option, the exact rules for how files are selected, the list of protected secret files, upgrading and uninstalling, and a development guide for contributors.
