# practice-mpl-japanize

Matplotlib font rendering experiments with uv and Jupyter.

See `docs/matplotlib-japanese-font-stack.md` for the stack-level explanation of how Linux, uv, Jupyter kernels, and Matplotlib combine to render Japanese text.

## Setup

```bash
uv sync
```

## Run Jupyter

```bash
uv run jupyter notebook
```

Open `notebooks/01_alphabet_plot.ipynb` first. It intentionally uses only alphabet text so it can serve as the baseline before testing Japanese font rendering.

## Test Japanese Font Rendering

Open `notebooks/02_japanese_font_via_matplotlibrc.ipynb` from PyCharm or Jupyter.

The notebook downloads Noto Sans JP from the Google Fonts repository into the current directory's `.fonts` directory, generates a local `.fontconfig/fonts.conf`, and writes `matplotlibrc` with:

```txt
font.family: sans-serif
font.sans-serif: Noto Sans JP, DejaVu Sans
axes.unicode_minus: False
```

If Matplotlib has already been imported in the running kernel, restart the kernel after the setup cell. Matplotlib reads `matplotlibrc` and builds its font list early, so a stale kernel can keep using the old state.

You can also run the setup from the terminal:

```bash
cd notebooks
uv run python ../scripts/setup_noto_sans_jp.py
```

For PyCharm/Jupyter, make sure the kernel starts with this environment variable if `fc-match "Noto Sans JP"` does not find the local font:

```bash
FONTCONFIG_FILE=/path/to/practice-mpl-japanize/notebooks/.fontconfig/fonts.conf
```

If `fc-cache` and `fc-match` are not found, the environment does not have the fontconfig command line tools installed. In that case this experiment should show two separate facts:

- `matplotlibrc` can request `Noto Sans JP`.
- Matplotlib still cannot discover `notebooks/.fonts/NotoSansJP[wght].ttf` unless fontconfig can expose it, the font is installed into a standard font directory, or the font is registered from Python with `font_manager.addfont()`.
