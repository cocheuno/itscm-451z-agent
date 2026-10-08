# Getting started: the tools, the words, and the daily routine

Read this once before Module 2, and come back to it whenever a lecture uses a word you do not recognise.
Every lecture assumes you have done the setup at the bottom of this page.

Commands are written for Windows (PowerShell). Where a Mac differs, a box like this follows:

> **Mac:** the Mac version of the command.

## The pieces, in plain words

- **The course repository.** A folder of files that lives on GitHub at
  `https://github.com/cocheuno/itscm-451z-agent`. It holds the program you are building, the data it
  learns from, and these lectures. The instructor is the only person who changes it. You read from it.
- **Your clone.** A copy of that folder on your laptop. You work inside your clone. Nothing you do in it
  changes GitHub.
- **Your PDI.** Your personal ServiceNow instance, a real service-desk system in the cloud with your own
  login. The program reads tickets from it. It starts empty; a script fills it.
- **The data.** Two spreadsheet-like files under `data/eval/`: `incidents_history.csv`, 4,242 closed
  tickets from March to August 2026, and `incidents_open.csv`, 150 open tickets. Every analysis and every
  model in the course uses these files. They were generated for the course, so the right answers are known.
- **`.env`.** A small text file in your clone that holds your PDI address, the service-account password,
  and later an API key. It is private to your laptop and is never copied anywhere.

## The terminal

A terminal is a window where you type a command, press Enter, and read the result. Every lecture step is a
command plus what you should see. You do not need to understand the command to run it; you do need to type
it exactly, and read what comes back.

**Open a terminal in the right folder.** In Windows Explorer, open your clone folder, click in the address
bar, type `powershell` and press Enter. A blue or black window opens with a prompt that ends in the folder
name and a `>`. That prompt is where you type.

> **Mac:** in Finder, right-click the clone folder, choose **New Terminal at Folder**. The prompt ends in
> `%` or `$`.

Three habits:

1. **Look at the prompt before typing.** It must show your clone folder, and once the virtual environment is
   active (below), it starts with `(.venv)`. If either is missing, the command will fail in a confusing way.
2. **Read the whole output.** The last few lines usually say whether it worked. The lecture tells you what
   those lines should say. If they say something else, stop there.
3. **When asking for help, paste everything.** The command you typed and every line it printed, not a
   summary. The exact wording of an error is the clue.

## Folders and paths

A path is the address of a file. `src\agent\rung0_poller.py` means: the folder `src`, inside it `agent`,
inside that the file `rung0_poller.py`. Windows writes paths with backslashes; the lectures use them in
commands you type. Inside Python and git, forward slashes work on every system, which is why you will see
both.

`cd` means "change directory", that is, go to a folder. `cd ..` goes up one level. `dir` lists what is in
the current folder.

> **Mac:** `ls` instead of `dir`.

## Python, pip, and the virtual environment

**Python** runs the program. **pip** installs the libraries the program needs (pandas for tables,
scikit-learn for models, and so on). A **virtual environment** is a private copy of Python inside your
clone, in a folder called `.venv`, so the libraries this course needs do not collide with anything else on
your laptop.

You must **activate** the virtual environment every time you open a new terminal. After activation the
prompt starts with `(.venv)`. If you forget, commands fail with `ModuleNotFoundError`.

```
.venv\Scripts\activate
```

> **Mac:** `source .venv/bin/activate`

**Running the program's pieces.** Commands that start `python -m something` run one module of the program by
its name. `python -m pytest -q` runs the tests. Always write `python -m` in front; it guarantees the Python
in your virtual environment is the one that runs.

## What "the tests" are

The repository contains checks, written as small programs, that prove the code does what it should. You
run them all with:

```
python -m pytest -q
```

They print a row of dots and a summary line such as `70 passed, 1 skipped`. "Passed" means fine. "Skipped"
means a check for something you have not written yet; the lecture tells you which. "Failed" means something
is broken, and the output above the summary names what.

## Git, in the words you need

Git keeps the history of a folder. Every word below appears in the lectures.

- **Repository (repo):** a folder whose history git keeps. Your clone is one.
- **Commit:** a saved snapshot of the files, with a one-line message saying what changed. Think of it as a
  named save point.
- **`main`:** the name of the instructor's line of commits. In your clone, `main` is a copy of the
  instructor's work. You never change it; you only update it.
- **Branch:** your own line of commits, started from `main`, with a name you choose. Your work for each
  module lives on a branch. Branches are how your changes and the instructor's stay apart.
- **Pull:** update your copy of `main` with whatever the instructor has merged since you last looked.
- **Tag:** a label on one commit, such as `v0.0`, marking a finished rung.
- **Status:** `git status` lists the files you have changed since the last commit. Read it before every
  commit.

**The routine for every module**, in full:

```
git checkout main
git pull origin main
git checkout -b module-02
```

Line by line: go to `main`; download the instructor's latest; start a new branch named after the module and
move onto it. From here on, everything you edit is on your branch. At the end of the module:

```
git status
git add <the files the lecture names>
git commit -m "<the message the lecture gives>"
git tag -a v0.0 -m "<the tag message the lecture gives>"
git log --oneline -3
```

`git status` shows what changed; `git add` chooses which files go into the snapshot; `git commit` takes
the snapshot; `git tag` labels it; `git log` shows the last three snapshots so you can see yours on top.
Nothing is sent anywhere. Your work stays on your laptop, and you walk the instructor through it in class
using `git log` and the files themselves.

**Your write-up.** Where the instructor's own work gets a pull request with a description, yours gets a
file: `docs/journal/module-02.md`, `module-03.md`, and so on, committed on your branch. The lecture tells
you what goes in it (usually the tables the harness printed and a few sentences). This file is your record
and the instructor's grading evidence.

**Two things you must never do.** Never run `git add .env`; the password file stays out of git. Never run
`git push`; your work is local, and the repository on GitHub belongs to the instructor.

## Getting the instructor's updates

The instructor changes the repository through the week. To receive those changes:

```
git checkout main
git pull origin main
python -m pip install -r requirements.txt
python -m pytest -q
```

The third line installs any library the update added or changed. The fourth proves the update is healthy.
Then start the next module's branch from this fresh `main`. Your earlier branches are untouched.

If `git pull` says your local changes would be overwritten, you edited a file while on `main` instead of on
a branch. Run `git status` to see which, then either save the edit on a branch
(`git checkout -b stray-edits` then `git add` and `git commit`) or throw it away
(`git checkout -- <file>`), and pull again.

## Setup, once

Do this on a laptop that has Python 3.12 or 3.13 and git installed. If `python --version` or `git --version`
prints an error, install them first (python.org and git-scm.com) and open a new terminal.

1. Open a terminal in the folder where you keep course work (not inside any old clone). Then:

   ```
   git clone https://github.com/cocheuno/itscm-451z-agent.git
   cd itscm-451z-agent
   python -m venv .venv
   .venv\Scripts\activate
   python -m pip install -r requirements.txt -e .
   ```

   > **Mac:** `python3 -m venv .venv` and `source .venv/bin/activate`; after that, `python` works inside the
   > environment.

   The first line downloads the repository into a new folder. The install line takes a few minutes and
   prints a lot; the last line should start with `Successfully installed`. If you already have an older
   clone, give the new one a different folder name by adding it to the end of the `git clone` line, for
   example `git clone https://github.com/cocheuno/itscm-451z-agent.git itscm-451z-agent-fresh`, and copy
   your old `.env` into it.
2. Create your private settings file:

   ```
   copy .env.example .env
   ```

   > **Mac:** `cp .env.example .env`

   Open `.env` in your editor and fill in `SN_INSTANCE`, `SN_USER` and `SN_PASSWORD` (Module 2 Part 1 walks
   through the PDI side). Leave the rest for later lectures.
3. Prove it:

   ```
   python -m agent.config
   python -m pytest -q
   ```

   Expected: a line starting `config ok`, then a test summary ending in `passed` with `1 skipped`.

## When something goes wrong

| What you see | What it means | What to do |
|---|---|---|
| `ModuleNotFoundError: No module named 'pandas'` (or `agent`, `yaml`, `requests`) | The virtual environment is not active, or the install did not finish | Activate it, then rerun `python -m pip install -r requirements.txt -e .` |
| `Fatal error in launcher: Unable to create process` | A leftover `pytest.exe` from an old Python | Use `python -m pytest` instead of `pytest` |
| `fatal: not a git repository` | The terminal is not in the clone folder | `cd` into it; check the prompt |
| `fatal: a branch named 'module-02' already exists` | You created that branch earlier | `git checkout module-02` to switch to it |
| `error: Your local changes ... would be overwritten` on pull | You edited a file on `main` | See "Getting the instructor's updates" above |
| `401` from a ServiceNow command | The service account's password or flags are wrong | Module 2 Part 1, step 4 again |
| `config error: missing environment variable` | A line in `.env` is missing or misspelled | Compare with `.env.example`; names are case-sensitive |

## Two rules for the whole course

- `data/eval/incidents_open.csv` has columns starting `gt_`. They are the answer key. Your code never reads
  them; the scoring program does, on your behalf.
- `data/synthetic/patterns.yaml` is the answer key for patterns hidden in the history data. Do not open it.
  If you do by accident, say so in your journal.
