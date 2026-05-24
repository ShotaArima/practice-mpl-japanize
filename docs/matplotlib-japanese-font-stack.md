# Linux, uv, Jupyter, and Matplotlib Font Rendering

## Goal

The ideal environment is one where a fresh notebook can run ordinary Matplotlib code and render Japanese text without per-notebook setup:

```python
import matplotlib.pyplot as plt

plt.plot([1, 2, 3], [10, 20, 15])
plt.title("日本語タイトル")
plt.xlabel("回数")
plt.ylabel("値")
plt.show()
```

This looks like a Matplotlib problem, but it is really a boundary problem across four layers:

```text
Linux OS / fontconfig
  ↓
uv-created Python virtual environment
  ↓
Jupyter / IPython kernel process
  ↓
Matplotlib font manager and backend
```

Japanese text renders only when the kernel process can see a Japanese-capable font and Matplotlib can resolve the configured font family to that font file.

## Observed Environment

The PyCharm notebook kernel reported:

```text
Python executable:
/home/ubuntu-server/PycharmProjects/practice-mpl-japanize/.venv/bin/python

Python version:
3.13.9

Virtual env:
/home/ubuntu-server/PycharmProjects/practice-mpl-japanize/.venv

sys.base_prefix:
/home/ubuntu-server/.local/share/uv/python/cpython-3.13.9-linux-x86_64-gnu

Backend:
module://matplotlib_inline.backend_inline

Matplotlib config dir:
/home/ubuntu-server/.config/matplotlib

Matplotlib cache dir:
/home/ubuntu-server/.cache/matplotlib
```

This tells us several important things:

- The notebook is not using the system Python. It is using the project `.venv`.
- The base interpreter was installed by `uv`.
- The notebook backend is the inline Jupyter backend, not a GUI backend.
- Matplotlib configuration and font cache live outside the `.venv`, under the user's home directory.
- The current notebook process is a long-lived kernel. Changes made after Matplotlib is imported may not affect that already-running process.

## The Rendering Pipeline

### 1. Linux Provides Fonts

On Linux, fonts are usually exposed through standard directories and fontconfig.

Common font locations include:

```text
/usr/share/fonts
/usr/local/share/fonts
~/.local/share/fonts
~/.fonts
```

fontconfig tools such as `fc-cache`, `fc-list`, and `fc-match` are commonly used to build and inspect the OS-level font database:

```bash
fc-cache -fv
fc-match "Noto Sans JP"
fc-list | grep -i noto
```

If these commands do not exist, the environment may still contain font files, but it is missing the normal command-line inspection and cache tools. In the observed environment:

```text
fc-cache was not found
fc-match was not found
```

That does not prove Matplotlib cannot render Japanese. It means the OS/fontconfig path cannot be verified or refreshed in the usual way.

### 2. uv Provides Python, Not Fonts

`uv` creates and manages the Python interpreter and virtual environment:

```text
project/.venv/bin/python
```

It installs Python packages such as:

```text
matplotlib
numpy
jupyter
ipykernel
```

But `uv` does not install OS fonts, refresh fontconfig caches, or automatically make a downloaded `.ttf` visible to Matplotlib.

This distinction is central:

```text
uv manages Python packages.
Linux/fontconfig manages system fonts.
Matplotlib bridges from Python into font discovery.
```

Installing `matplotlib` with `uv` gives you the plotting library. It does not guarantee that the runtime environment has Japanese fonts.

### 3. Jupyter Runs a Kernel Process

When a notebook is opened in PyCharm, the code runs inside a Jupyter/IPython kernel process. The important value is:

```python
import sys
print(sys.executable)
```

For this project, the desired result is:

```text
/home/ubuntu-server/PycharmProjects/practice-mpl-japanize/.venv/bin/python
```

That confirms that the notebook is using the `uv` project environment.

The kernel also owns process environment variables:

```python
import os
print(os.environ.get("FONTCONFIG_FILE"))
print(os.environ.get("MPLCONFIGDIR"))
```

If these are set inside a notebook cell after Matplotlib has already been imported, it may be too late. Matplotlib reads configuration and initializes font state early.

That is why kernel restarts matter:

```text
create font files
set environment variables
start or restart kernel
import matplotlib
draw plot
```

### 4. Matplotlib Reads Configuration

Matplotlib looks for configuration in a known order. In a notebook running from `notebooks/`, a local file can be picked up:

```text
notebooks/matplotlibrc
```

You can check which file was loaded:

```python
import matplotlib
print(matplotlib.matplotlib_fname())
```

In the observed run:

```text
matplotlibrc loaded from: matplotlibrc
```

That means Matplotlib found a local `matplotlibrc`.

However, reading `matplotlibrc` is not the same as discovering a font file.

This configuration:

```text
font.family: sans-serif
font.sans-serif: Noto Sans JP, DejaVu Sans
axes.unicode_minus: False
```

tells Matplotlib:

```text
Prefer Noto Sans JP when resolving sans-serif text.
Fall back to DejaVu Sans if needed.
```

It does not tell Matplotlib:

```text
Also scan ./notebooks/.fonts/NotoSansJP[wght].ttf.
```

Matplotlib official examples use `font.family` plus family-specific lists such as `font.sans-serif` to select among fonts that are already discoverable by Matplotlib. The Matplotlib font manager API also documents that fonts manually added with `font_manager.addfont()` do not persist in the cache and must be added whenever Matplotlib is imported.

Sources:

- [Matplotlib: Configure the font family](https://matplotlib.org/stable/gallery/text_labels_and_annotations/font_family_rc.html)
- [Matplotlib: font_manager API](https://matplotlib.org/stable/api/font_manager_api.html?highlight=fontproperties)

## Why `.fonts` plus `matplotlibrc` Did Not Work

The project created:

```text
notebooks/.fonts/NotoSansJP[wght].ttf
notebooks/.fontconfig/fonts.conf
notebooks/matplotlibrc
```

The downloaded font existed:

```text
/home/ubuntu-server/PycharmProjects/practice-mpl-japanize/notebooks/.fonts/NotoSansJP[wght].ttf 9589900
```

But Matplotlib reported:

```text
font.family: ['sans-serif']
cache dir: /home/ubuntu-server/.cache/matplotlib
```

And no `Noto Sans JP` font appeared in `matplotlib.font_manager.fontManager.ttflist`.

That points to this failure chain:

```text
The font file exists.
  ↓
fontconfig CLI tools are unavailable.
  ↓
The local .fontconfig/fonts.conf path is not enough by itself.
  ↓
Matplotlib's font manager does not discover the local .ttf.
  ↓
matplotlibrc requests Noto Sans JP, but no matching font is registered.
  ↓
Matplotlib falls back to a default font such as DejaVu Sans.
  ↓
Japanese glyphs are missing or rendered incorrectly.
```

This is the key lesson:

```text
matplotlibrc selects a font by name.
It does not install or register an arbitrary local font file.
```

## The Positive Control: `addfont()`

To prove that the font file itself is valid, register it directly in Python:

```python
from pathlib import Path

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt

font_path = Path.cwd() / ".fonts" / "NotoSansJP[wght].ttf"
font_name = fm.FontProperties(fname=font_path).get_name()

fm.fontManager.addfont(font_path)
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = [font_name, "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

print("font name:", font_name)
print("font file:", fm.findfont(font_name, fallback_to_default=False))
```

Then draw:

```python
fig, ax = plt.subplots()
ax.plot([1, 2, 3], [10, 20, 15])
ax.set_title("日本語フォントの検証")
ax.set_xlabel("回数")
ax.set_ylabel("値")
plt.show()
```

If this works, it proves:

```text
The Noto Sans JP font file is valid.
Matplotlib can render Japanese in this kernel.
The failing part is automatic font discovery, not drawing itself.
```

But this is not the ideal environment. It requires per-kernel Python setup.

## The Ideal Environment

For a fresh notebook to render Japanese without extra code, the font must be discoverable before Matplotlib starts.

There are three practical paths.

## Path A: Install Fonts at the OS Level

This is the cleanest path for "nothing special in notebooks".

On Ubuntu-like systems:

```bash
sudo apt update
sudo apt install -y fontconfig fonts-noto-cjk
fc-cache -fv
fc-match "Noto Sans CJK JP"
```

Then configure Matplotlib globally or per project:

```text
font.family: sans-serif
font.sans-serif: Noto Sans CJK JP, Noto Sans JP, DejaVu Sans
axes.unicode_minus: False
```

Result:

```text
New notebook
  ↓
import matplotlib.pyplot as plt
  ↓
Japanese renders
```

This approach makes the OS responsible for fonts, which matches how Linux desktop and server environments usually work.

## Path B: Use Project-Local Fonts plus fontconfig

This keeps fonts inside the project, but still depends on fontconfig being available.

Project layout:

```text
notebooks/
  .fonts/
    NotoSansJP[wght].ttf
  .fontconfig/
    fonts.conf
  matplotlibrc
```

Example `fonts.conf`:

```xml
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">
<fontconfig>
  <dir>/absolute/path/to/notebooks/.fonts</dir>
</fontconfig>
```

The kernel process must start with:

```bash
FONTCONFIG_FILE=/absolute/path/to/notebooks/.fontconfig/fonts.conf
```

Then Matplotlib can potentially discover the project-local font before import.

This path is educational because it shows how environment variables, kernel startup, fontconfig, and Matplotlib interact. It is also fragile in IDEs unless the IDE lets you reliably set kernel environment variables.

## Path C: Register Fonts in Python

This is the most portable path:

```python
fm.fontManager.addfont(font_path)
```

It works even when fontconfig is missing.

But it is not "zero setup" because every fresh kernel must run the registration before plotting. It is best understood as the mechanism used by libraries or project bootstrap code.

## Where Caches Fit

Matplotlib has its own cache:

```python
import matplotlib
print(matplotlib.get_cachedir())
```

In the observed environment:

```text
/home/ubuntu-server/.cache/matplotlib
```

This cache is outside the `.venv`.

That means:

- Recreating `.venv` does not necessarily clear Matplotlib's font cache.
- Adding fonts may not affect a running kernel.
- Deleting the cache can be useful during experiments:

```bash
rm -rf ~/.cache/matplotlib
```

But cache deletion is not a substitute for installing or registering the font. It only forces Matplotlib to rebuild what it can discover.

## Backend Is Usually Not the First Problem

The observed backend was:

```text
module://matplotlib_inline.backend_inline
```

This is normal for Jupyter notebooks. The inline backend controls how figures are displayed in the notebook output cell.

The backend usually receives text layout after Matplotlib has already resolved fonts. So if Japanese text fails because `Noto Sans JP` is not in `fontManager.ttflist`, changing the backend is unlikely to fix it.

Backend matters later for output differences such as:

- notebook inline PNG/SVG
- saved PNG
- saved PDF/SVG
- GUI windows

But the first question is still:

```python
import matplotlib.font_manager as fm
print(fm.findfont("Noto Sans JP", fallback_to_default=False))
```

## Diagnostic Checklist

Run these in a notebook.

### Kernel Identity

```python
import os
import sys

print(sys.executable)
print(sys.version)
print(os.getcwd())
print(os.environ.get("VIRTUAL_ENV"))
```

Expected:

```text
.../practice-mpl-japanize/.venv/bin/python
```

### Matplotlib State

```python
import matplotlib
import matplotlib.pyplot as plt

print(matplotlib.__version__)
print(matplotlib.get_backend())
print(matplotlib.matplotlib_fname())
print(matplotlib.get_cachedir())
print(plt.rcParams["font.family"])
print(plt.rcParams["font.sans-serif"][:5])
```

### Font Discovery

```python
import matplotlib.font_manager as fm

for font in fm.fontManager.ttflist:
    if "Noto" in font.name or "JP" in font.name:
        print(font.name, font.fname)
```

### Exact Font Resolution

```python
import matplotlib.font_manager as fm

try:
    print(fm.findfont("Noto Sans JP", fallback_to_default=False))
except Exception as exc:
    print(type(exc).__name__, exc)
```

## Mental Model

The clean mental model is:

```text
uv answers:
  Which Python and packages are used?

Jupyter answers:
  Which long-lived Python process is executing notebook cells?

Linux/fontconfig answers:
  Which font files exist and what family names do they expose?

Matplotlib answers:
  Which configured family name resolves to which font file?

The backend answers:
  How is the finished figure displayed or saved?
```

When Japanese text does not render, ask in this order:

```text
1. Is this the expected kernel?
2. Has Matplotlib already been imported?
3. Which matplotlibrc was loaded?
4. Is the desired font visible in fontManager.ttflist?
5. What does findfont() resolve?
6. Is the backend only affecting display/output format?
```

## Conclusion

The goal of "Japanese works without notebook setup" is achievable, but it belongs mostly to the OS/font discovery layer, not to `uv`.

For a stable Linux environment:

```text
Install Japanese fonts into a standard OS font location.
Install fontconfig tools.
Refresh the font cache.
Set Matplotlib defaults through matplotlibrc.
Restart the Jupyter kernel.
```

For a portable project demo:

```text
Download a font into the project.
Use font_manager.addfont() before plotting.
Set rcParams.
```

The first path gives the desired user experience. The second path gives the best controlled experiment. The gap between them is exactly where Linux, uv, Jupyter, and Matplotlib meet.
