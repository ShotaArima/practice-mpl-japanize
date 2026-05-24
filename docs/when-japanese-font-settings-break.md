# 日本語フォント設定はいつ切れるのか

## 目的

Matplotlib の日本語設定は、一度効いたように見えても、次のような場面で切れることがあります。

- Google Colab の runtime / session が切れた。
- Jupyter / IPython kernel を再起動した。
- `plt.style.use(...)` を実行した。
- `plt.rcdefaults()` や `matplotlib.rc_file_defaults()` を実行した。
- 他のライブラリや自分のコードが `rcParams` を上書きした。
- 日本語フォント設定前に figure / axes / text object を作成していた。
- package install は残っているが、kernel process は新しくなった。

この doc では、どの場面でどのおまじないを実行すべきかを整理します。

## まず知っておくべきこと

`import japanize_matplotlib` は、単なる設定読み込みではありません。

import 時に次を実行します。

```text
japanize_matplotlib package 内の ipaexg.ttf を Matplotlib に addfont() する
Matplotlib の font.family を IPAexGothic にする
```

ただし Python の import は一度だけ実行されます。

```python
import japanize_matplotlib
import japanize_matplotlib
import japanize_matplotlib
```

このように複数回 import しても、通常は初回 import 時の副作用しか起きません。

そのため、後から `rcParams` が壊れた場合は、次のように明示的に再適用します。

```python
import japanize_matplotlib
japanize_matplotlib.japanize()
```

## 状態確認コード

Notebook で「いま日本語設定が効いているか」を見るには、次を実行します。

```python
import sys

import matplotlib
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt

print("matplotlib:", matplotlib.__version__)
print("backend:", matplotlib.get_backend())
print("matplotlibrc:", matplotlib.matplotlib_fname())
print("font.family:", plt.rcParams["font.family"])
print("japanize imported:", "japanize_matplotlib" in sys.modules)

matches = [font for font in fm.fontManager.ttflist if font.name == "IPAexGothic"]
print("IPAexGothic in ttflist:", len(matches))

try:
    print("findfont:", fm.findfont("IPAexGothic", fallback_to_default=False))
except Exception as exc:
    print("findfont failed:", type(exc).__name__, exc)
```

最低限、次の状態なら `japanize_matplotlib` による日本語化は効いています。

```text
font.family: ['IPAexGothic']
IPAexGothic in ttflist: 1 以上
findfont: .../japanize_matplotlib/fonts/ipaexg.ttf
```

## よくあるケースと必要な再実行

| ケース | 何が消えるか | 何を実行するか |
|---|---|---|
| Colab runtime が切れた | install した package、import 状態、rcParams、fontManager 状態 | `!pip install japanize-matplotlib` から再実行し、その後 `import japanize_matplotlib` |
| Jupyter kernel を再起動した | import 状態、rcParams、fontManager 状態 | `import japanize_matplotlib` |
| `plt.style.use("default")` を実行した | rcParams の font.family | `japanize_matplotlib.japanize()` |
| `plt.rcdefaults()` を実行した | rcParams の font.family | `japanize_matplotlib.japanize()` |
| `matplotlib.rc_file_defaults()` を実行した | rcParams の font.family | `japanize_matplotlib.japanize()` |
| 自分で `plt.rcParams["font.family"] = ...` を上書きした | rcParams の font.family | `japanize_matplotlib.japanize()` または自分で `IPAexGothic` を再指定 |
| `import japanize_matplotlib` 前に figure を作った | 既存 text object の font 設定が古い可能性 | figure を作り直すか、既存 text object に font family を設定 |
| `pip install japanize-matplotlib` だけ実行した | package は入るが Matplotlib 設定は変わらない | `import japanize_matplotlib` |

## Colab での基本セル

Colab では runtime が切れると、package install から消えることがあります。そのため、先頭付近に次のセルを置くのが分かりやすいです。

```python
import importlib.util
import sys
import subprocess

if importlib.util.find_spec("japanize_matplotlib") is None:
    subprocess.check_call([
        sys.executable,
        "-m",
        "pip",
        "install",
        "japanize-matplotlib",
    ])

import japanize_matplotlib
japanize_matplotlib.japanize()
```

単に次だけでも、多くの場合は十分です。

```python
!pip install japanize-matplotlib
import japanize_matplotlib
```

ただし、途中で style や rcParams を変更する notebook では、描画直前に再適用用セルを置くと安全です。

```python
import japanize_matplotlib
japanize_matplotlib.japanize()
```

## 「import 済みなのに効いていない」理由

次のような流れでは、`import japanize_matplotlib` 済みでも日本語設定が切れます。

```python
import japanize_matplotlib

import matplotlib.pyplot as plt
plt.style.use("default")
```

`plt.style.use("default")` が rcParams を上書きするためです。

ここで再び次を実行しても、通常は副作用が再実行されません。

```python
import japanize_matplotlib
```

Python は import 済み module を `sys.modules` から返すだけだからです。

この場合は、明示的に関数を呼びます。

```python
japanize_matplotlib.japanize()
```

`importlib.reload(japanize_matplotlib)` も、通常は再適用の方法としては分かりにくく、期待通りに戻らないことがあります。`japanize_matplotlib` package の reload では、実際に `japanize()` を呼んでいる submodule が再実行されない場合があるためです。再適用したいときは、素直に `japanize_matplotlib.japanize()` を呼ぶのが一番明確です。

## 描画オブジェクトを作るタイミング

原則として、日本語化は figure / axes / title / label を作る前に実行します。

推奨:

```python
import japanize_matplotlib
japanize_matplotlib.japanize()

import matplotlib.pyplot as plt

fig, ax = plt.subplots()
ax.set_title("日本語タイトル")
```

避けたい流れ:

```python
import matplotlib.pyplot as plt

fig, ax = plt.subplots()
ax.set_title("日本語タイトル")

import japanize_matplotlib
```

既存の text object がすでに古い font 設定を持っていることがあるためです。迷ったら、フォント設定後に figure を作り直すのが一番確実です。

## 判断のコツ

問題を切り分けるときは、次の 3 つを分けて考えます。

```text
package が install されているか
  importlib.util.find_spec("japanize_matplotlib")

font file が Matplotlib に登録されているか
  IPAexGothic in fm.fontManager.ttflist

rcParams が IPAexGothic を使う状態か
  plt.rcParams["font.family"]
```

`japanize_matplotlib` で日本語が出るためには、少なくとも次の 2 つが必要です。

```text
IPAexGothic が fontManager に登録されている
font.family が IPAexGothic になっている
```

どちらか片方だけでは、期待通りに描画されないことがあります。

## 検証 Notebook

このリポジトリでは、次の Notebook で状態の破壊と再適用を検証できます。

```text
notebooks/04_when_japanese_font_settings_break.ipynb
```

この Notebook は subprocess を使い、fresh kernel に近い状態で各シナリオを比較します。
