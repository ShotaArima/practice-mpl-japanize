# `import japanize_matplotlib` は何をしているのか

## 概要

`japanize_matplotlib` は、Matplotlib で日本語を描画できるようにするための小さな package です。

今回確認した version は `1.1.3` です。

package metadata:

```text
name: japanize-matplotlib
version: 1.1.3
home-page: https://github.com/uehara1414/japanize-matplotlib
summary: matplotlibのフォント設定を自動で日本語化する
```

この package の重要な特徴は、Linux の system font や fontconfig に頼らず、package に同梱されたフォントを Matplotlib に直接登録することです。

## 同梱されているもの

`japanize_matplotlib` package の中には、次のようなファイルが含まれています。

```text
japanize_matplotlib/
  __init__.py
  japanize_matplotlib.py
  fonts/
    ipaexg.ttf
    IPA_Font_License_Agreement_v1.0.txt
    Readme_ipaexg00301.txt
```

使われるフォントは `IPAexGothic` です。

```python
FONT_NAME = "IPAexGothic"
FONT_TTF = "ipaexg.ttf"
```

つまり、Google Fonts から `Noto Sans JP` をダウンロードして使う方式とは、フォントの入手元も、登録方法も違います。

## import 時に実行される処理

`japanize_matplotlib.__init__.py` は次の関数を import しています。

```python
from japanize_matplotlib.japanize_matplotlib import japanize, get_font_path, get_font_ttf_path
```

そして `japanize_matplotlib.py` の末尾で、次が実行されます。

```python
japanize()
```

そのため、ユーザーが次のように import しただけで、

```python
import japanize_matplotlib
```

内部では `japanize()` が自動実行されます。

処理の流れは概ね次の通りです。

```text
import japanize_matplotlib
  ↓
package 内の fonts/ ディレクトリを探す
  ↓
fonts/ipaexg.ttf を Matplotlib の fontManager に追加する
  ↓
matplotlib.rc('font', family='IPAexGothic') を実行する
  ↓
以後の Matplotlib 描画で IPAexGothic が使われる
```

Matplotlib 3.2 以降では、実装上は次の API が使われます。

```python
font_manager.fontManager.addfont(fpath)
```

その後、rcParams に相当する設定が変更されます。

```python
matplotlib.rc("font", family="IPAexGothic")
```

## 自分で `.fonts` と `matplotlibrc` を作る方式との違い

今回試した自前方式は、次のような構成でした。

```text
notebooks/
  .fonts/
    NotoSansJP[wght].ttf
  .fontconfig/
    fonts.conf
  matplotlibrc
```

この方式では、`matplotlibrc` に次のような設定を書きました。

```text
font.family: sans-serif
font.sans-serif: Noto Sans JP, DejaVu Sans
axes.unicode_minus: False
```

しかし、`matplotlibrc` はフォント名の優先順位を指定するだけです。ローカルの `.ttf` ファイルを Matplotlib に登録するわけではありません。

そのため、次のどれかが必要になります。

```text
OS/fontconfig から Noto Sans JP が見える
Matplotlib の font cache に Noto Sans JP が発見される
Python から font_manager.addfont() で直接登録する
```

一方、`japanize_matplotlib` は package 内の `ipaexg.ttf` を Python から直接登録します。

比較すると次のようになります。

| 観点 | 自前 `.fonts` + `matplotlibrc` | `import japanize_matplotlib` |
|---|---|---|
| フォント | Noto Sans JP | IPAexGothic |
| フォントの置き場所 | project local | Python package 内 |
| OS fontconfig への依存 | 依存しやすい | 基本的に依存しない |
| Matplotlib への登録 | 自動ではされない | import 時に `addfont()` される |
| rcParams の変更 | `matplotlibrc` が読み込まれた時 | import 時 |
| fresh Notebook での手軽さ | 環境設定が必要 | `import japanize_matplotlib` だけ |
| 「何もしなくても」動くか | OS 側に入れば可能 | import は必要 |

## `japanize_matplotlib` は「全部」を日本語化するのか

厳密には、`japanize_matplotlib` が直接変更するのは Matplotlib の font 設定です。

そのため、Matplotlib を内部で使うライブラリでは効果が出ることがあります。

代表例:

```text
pandas.DataFrame.plot()
seaborn
Matplotlib を backend として使う可視化処理
```

ただし、すべての描画ライブラリを日本語化するわけではありません。

例えば、次のようなものは別系統です。

```text
Plotly
Bokeh
Altair / Vega-Lite
browser 側 CSS font に依存する可視化
画像生成系ライブラリ
PDF/LaTeX text rendering
```

つまり、`japanize_matplotlib` の効く範囲は次のように理解するとよいです。

```text
Matplotlib の rcParams を使って text を描くものには効く。
Matplotlib を使わない描画エンジンには効かない。
```

## import 順序の注意

`japanize_matplotlib` は import 時に rcParams を変更します。

そのため、通常は描画前に import します。

```python
import matplotlib.pyplot as plt
import japanize_matplotlib

plt.title("日本語")
plt.plot([1, 2, 3])
plt.show()
```

既に作成済みの figure や text object がある場合、後から import しても、その既存 object の font 設定に必ず反映されるとは限りません。基本は「描画コードの前に import」です。

また、後から `plt.rcParams` や style を変更すると、`japanize_matplotlib` の設定が上書きされることがあります。

## 何が解決され、何が解決されないのか

`japanize_matplotlib` が解決するもの:

```text
Matplotlib が日本語フォントを見つけられない
OS に日本語フォントを入れていない
fontconfig が使えない
Notebook ごとに簡単に日本語描画したい
```

`japanize_matplotlib` だけでは解決しないもの:

```text
import なしで完全に自動化したい
Matplotlib 以外の描画ライブラリも日本語化したい
Noto Sans JP など特定のフォントを使いたい
OS 全体の font discovery を整えたい
PDF/SVG など出力形式ごとの font embedding 問題を完全に管理したい
```

## 今回の実験との関係

今回の実験で目指していたのは、次の理想状態でした。

```text
fresh Notebook
  ↓
何も追加設定しない
  ↓
Matplotlib で日本語が描画できる
```

`japanize_matplotlib` は、この理想にかなり近い体験を提供します。

ただし、完全な「何もしない」ではありません。

```python
import japanize_matplotlib
```

という 1 行は必要です。

この 1 行がやっていることは、要するに次の 2 つです。

```text
package 同梱フォントを Matplotlib に登録する
Matplotlib の default font family を IPAexGothic に変える
```

つまり、`japanize_matplotlib` は「Linux の fontconfig を正しく整える」解決策ではありません。

むしろ、次のような shortcut です。

```text
OS/fontconfig 経由の font discovery を迂回して、
Python package 内のフォントを Matplotlib に直接渡す。
```

この違いは、Python 可視化スタックの境界を説明するうえで非常に重要です。
