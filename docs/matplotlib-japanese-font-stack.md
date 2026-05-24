# Linux、uv、Jupyter、Matplotlib による日本語フォント描画の仕組み

## 目標

理想は、新しい Notebook で特別な設定コードを書かなくても、普通の Matplotlib コードだけで日本語が描画できる環境です。

```python
import matplotlib.pyplot as plt

plt.plot([1, 2, 3], [10, 20, 15])
plt.title("日本語タイトル")
plt.xlabel("回数")
plt.ylabel("値")
plt.show()
```

一見すると Matplotlib だけの問題に見えます。しかし実際には、次の 4 つの層をまたぐ境界問題です。

```text
Linux OS / fontconfig
  ↓
uv が作成した Python 仮想環境
  ↓
Jupyter / IPython kernel プロセス
  ↓
Matplotlib の font manager と backend
```

日本語テキストが描画されるためには、kernel プロセスから日本語グリフを持つフォントが見えていて、さらに Matplotlib が指定されたフォントファミリー名を実際のフォントファイルへ解決できる必要があります。

## 観測した環境

PyCharm の Notebook kernel では、次のような情報が得られました。

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

ここから、いくつか重要なことが分かります。

- Notebook は system Python ではなく、プロジェクトの `.venv` を使っている。
- base interpreter は `uv` によってインストールされた Python である。
- Notebook の backend は GUI backend ではなく、Jupyter の inline backend である。
- Matplotlib の設定ディレクトリとフォントキャッシュは `.venv` の中ではなく、ユーザーの home directory 配下にある。
- Notebook のコードは、長く生き続ける kernel プロセスの中で実行される。Matplotlib import 後に加えた変更は、すでに動いている kernel には反映されないことがある。

## 描画までの流れ

### 1. Linux がフォントを提供する

Linux では通常、フォントは標準ディレクトリと fontconfig を通じて提供されます。

代表的なフォント配置場所は次の通りです。

```text
/usr/share/fonts
/usr/local/share/fonts
~/.local/share/fonts
~/.fonts
```

fontconfig では、`fc-cache`、`fc-list`、`fc-match` などのコマンドを使って、OS 側のフォントデータベースを更新・確認できます。

```bash
fc-cache -fv
fc-match "Noto Sans JP"
fc-list | grep -i noto
```

これらのコマンドが存在しない場合でも、フォントファイル自体は存在しているかもしれません。しかし、OS/fontconfig 経由でそのフォントが見えているかを通常の方法で確認したり、キャッシュを更新したりできない状態です。

今回観測した環境では、次のような状態でした。

```text
fc-cache was not found
fc-match was not found
```

これは「Matplotlib が絶対に日本語を描画できない」という意味ではありません。通常の OS/fontconfig 経由の検証やキャッシュ更新ができない、という意味です。

### 2. uv は Python を提供するが、フォントは提供しない

`uv` は Python interpreter と仮想環境を作成・管理します。

```text
project/.venv/bin/python
```

そして、次のような Python package をインストールします。

```text
matplotlib
numpy
jupyter
ipykernel
```

しかし、`uv` は OS フォントをインストールしません。fontconfig のキャッシュも更新しません。ダウンロードした `.ttf` ファイルを Matplotlib から自動的に見えるようにすることもありません。

ここが重要です。

```text
uv は Python package を管理する。
Linux/fontconfig は system font を管理する。
Matplotlib は Python からフォント探索へ橋をかける。
```

`uv` で `matplotlib` をインストールすると、描画ライブラリは使えるようになります。しかし、その実行環境に日本語フォントが存在し、Matplotlib から発見できるとは限りません。

### 3. Jupyter は kernel プロセスを実行する

PyCharm で Notebook を開くと、セルのコードは Jupyter/IPython kernel プロセスの中で実行されます。まず確認すべき値はこれです。

```python
import sys
print(sys.executable)
```

このプロジェクトで期待する値は次のようなものです。

```text
/home/ubuntu-server/PycharmProjects/practice-mpl-japanize/.venv/bin/python
```

これにより、Notebook が `uv` プロジェクトの仮想環境を使っていることを確認できます。

kernel プロセスは環境変数も保持しています。

```python
import os
print(os.environ.get("FONTCONFIG_FILE"))
print(os.environ.get("MPLCONFIGDIR"))
```

これらの環境変数を Notebook セル内で設定したとしても、すでに Matplotlib が import 済みなら遅い場合があります。Matplotlib は設定やフォント状態を比較的早い段階で読み込みます。

そのため、kernel の再起動が重要になります。

```text
フォントファイルを作成する
環境変数を設定する
kernel を起動または再起動する
matplotlib を import する
グラフを描画する
```

### 4. Matplotlib が設定を読む

Matplotlib は決められた順序で設定ファイルを探します。Notebook を `notebooks/` から実行している場合、ローカルの設定ファイルが読み込まれることがあります。

```text
notebooks/matplotlibrc
```

どの設定ファイルが読み込まれたかは、次のコードで確認できます。

```python
import matplotlib
print(matplotlib.matplotlib_fname())
```

今回の実行では、次のように表示されました。

```text
matplotlibrc loaded from: matplotlibrc
```

これは、Matplotlib がローカルの `matplotlibrc` を見つけたことを意味します。

ただし、`matplotlibrc` が読まれることと、フォントファイルが発見されることは別問題です。

次の設定は、

```text
font.family: sans-serif
font.sans-serif: Noto Sans JP, DejaVu Sans
axes.unicode_minus: False
```

Matplotlib に対して、次のように指示しています。

```text
sans-serif の文字を描画するときは、Noto Sans JP を優先する。
必要なら DejaVu Sans に fallback する。
```

しかし、次のような意味ではありません。

```text
./notebooks/.fonts/NotoSansJP[wght].ttf も追加で scan する。
```

Matplotlib 公式の例でも、`font.family` と `font.sans-serif` のような family-specific list は、すでに Matplotlib から発見可能なフォントの中から選ぶために使われています。また Matplotlib の font manager API では、`font_manager.addfont()` で手動追加したフォントはキャッシュに永続化されず、Matplotlib を import するたびに追加する必要があると説明されています。

参考:

- [Matplotlib: Configure the font family](https://matplotlib.org/stable/gallery/text_labels_and_annotations/font_family_rc.html)
- [Matplotlib: font_manager API](https://matplotlib.org/stable/api/font_manager_api.html?highlight=fontproperties)

## なぜ `.fonts` と `matplotlibrc` だけでは動かなかったのか

プロジェクトでは、次のファイルを作成しました。

```text
notebooks/.fonts/NotoSansJP[wght].ttf
notebooks/.fontconfig/fonts.conf
notebooks/matplotlibrc
```

ダウンロードしたフォントファイルは存在していました。

```text
/home/ubuntu-server/PycharmProjects/practice-mpl-japanize/notebooks/.fonts/NotoSansJP[wght].ttf 9589900
```

しかし Matplotlib は次のように報告しました。

```text
font.family: ['sans-serif']
cache dir: /home/ubuntu-server/.cache/matplotlib
```

さらに、`matplotlib.font_manager.fontManager.ttflist` に `Noto Sans JP` は現れませんでした。

これは、次のような失敗の流れを示しています。

```text
フォントファイルは存在する。
  ↓
fontconfig CLI tools が存在しない。
  ↓
local .fontconfig/fonts.conf だけでは十分ではない。
  ↓
Matplotlib の font manager が local .ttf を発見できない。
  ↓
matplotlibrc は Noto Sans JP を要求するが、一致するフォントが登録されていない。
  ↓
Matplotlib は DejaVu Sans などの default font に fallback する。
  ↓
日本語グリフが存在せず、文字化けや豆腐になる。
```

ここでの重要な学びはこれです。

```text
matplotlibrc はフォント名を選択する。
任意の local font file をインストール・登録するわけではない。
```

## Positive Control としての `addfont()`

フォントファイル自体が正しいかどうかを確認するには、Python から直接登録します。

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

その後、描画します。

```python
fig, ax = plt.subplots()
ax.plot([1, 2, 3], [10, 20, 15])
ax.set_title("日本語フォントの検証")
ax.set_xlabel("回数")
ax.set_ylabel("値")
plt.show()
```

これで動く場合、次のことが分かります。

```text
Noto Sans JP のフォントファイルは正しい。
この kernel の Matplotlib は日本語を描画できる。
失敗しているのは描画そのものではなく、自動的なフォント発見である。
```

ただし、これは理想の環境ではありません。kernel ごとに Python 側のセットアップが必要だからです。

## 理想の環境

新しい Notebook で追加コードなしに日本語を描画するには、Matplotlib が起動する前にフォントが発見可能になっている必要があります。

実用的な道筋は 3 つあります。

## Path A: OS レベルにフォントをインストールする

「Notebook で何もしなくてもよい」環境にするなら、これが最も素直な方法です。

Ubuntu 系の環境では、例えば次のようにします。

```bash
sudo apt update
sudo apt install -y fontconfig fonts-noto-cjk
fc-cache -fv
fc-match "Noto Sans CJK JP"
```

その上で、Matplotlib の設定を global または project ごとに指定します。

```text
font.family: sans-serif
font.sans-serif: Noto Sans CJK JP, Noto Sans JP, DejaVu Sans
axes.unicode_minus: False
```

結果として、次の流れで日本語が描画されるようになります。

```text
新しい Notebook
  ↓
import matplotlib.pyplot as plt
  ↓
日本語が描画される
```

この方法では、フォント管理を OS に任せます。Linux desktop や server 環境としては自然な構成です。

## Path B: project-local font と fontconfig を使う

フォントを project 内に閉じ込めたい場合の方法です。ただし、fontconfig が利用できることに依存します。

想定する project layout は次のようになります。

```text
notebooks/
  .fonts/
    NotoSansJP[wght].ttf
  .fontconfig/
    fonts.conf
  matplotlibrc
```

`fonts.conf` の例です。

```xml
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">
<fontconfig>
  <dir>/absolute/path/to/notebooks/.fonts</dir>
</fontconfig>
```

kernel プロセスは次の環境変数付きで起動される必要があります。

```bash
FONTCONFIG_FILE=/absolute/path/to/notebooks/.fontconfig/fonts.conf
```

その上で Matplotlib が import されると、project-local なフォントを発見できる可能性があります。

この方法は教育的です。環境変数、kernel 起動、fontconfig、Matplotlib がどのように関係するかを観察できるからです。一方で、IDE が kernel の環境変数を確実に設定できない場合は壊れやすい方法でもあります。

## Path C: Python からフォントを登録する

最も portable な方法です。

```python
fm.fontManager.addfont(font_path)
```

この方法は fontconfig がなくても動きます。

ただし、「何もしなくても動く」環境ではありません。fresh kernel ごとに、描画前にフォント登録コードを実行する必要があります。ライブラリや project bootstrap code が内部で実行する処理として理解するとよいです。

## Cache はどこに関係するのか

Matplotlib は独自の cache を持っています。

```python
import matplotlib
print(matplotlib.get_cachedir())
```

今回の環境では次の場所でした。

```text
/home/ubuntu-server/.cache/matplotlib
```

この cache は `.venv` の外にあります。

つまり、次のようなことが起きます。

- `.venv` を作り直しても、Matplotlib の font cache は消えない。
- フォントを追加しても、実行中の kernel には反映されないことがある。
- 実験中は cache 削除が有効な場合がある。

```bash
rm -rf ~/.cache/matplotlib
```

ただし、cache 削除はフォントのインストールや登録の代わりにはなりません。Matplotlib が発見できるものを再探索させるだけです。

## Backend は最初に疑う場所ではない

今回観測した backend は次の通りです。

```text
module://matplotlib_inline.backend_inline
```

これは Jupyter Notebook では通常の backend です。inline backend は、完成した figure を Notebook の output cell にどう表示するかを担当します。

多くの場合、backend は Matplotlib がフォントを解決した後の表示形式に関係します。つまり、`Noto Sans JP` が `fontManager.ttflist` に存在しないことが原因なら、backend を変えても解決しない可能性が高いです。

backend が重要になるのは、次のような出力差を調べる段階です。

- Notebook inline PNG/SVG
- 保存した PNG
- 保存した PDF/SVG
- GUI window

最初に確認すべき問いはこれです。

```python
import matplotlib.font_manager as fm
print(fm.findfont("Noto Sans JP", fallback_to_default=False))
```

## 診断チェックリスト

Notebook で以下を実行します。

### Kernel の確認

```python
import os
import sys

print(sys.executable)
print(sys.version)
print(os.getcwd())
print(os.environ.get("VIRTUAL_ENV"))
```

期待する値は次のようなものです。

```text
.../practice-mpl-japanize/.venv/bin/python
```

### Matplotlib の状態

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

### フォント探索

```python
import matplotlib.font_manager as fm

for font in fm.fontManager.ttflist:
    if "Noto" in font.name or "JP" in font.name:
        print(font.name, font.fname)
```

### 正確なフォント解決

```python
import matplotlib.font_manager as fm

try:
    print(fm.findfont("Noto Sans JP", fallback_to_default=False))
except Exception as exc:
    print(type(exc).__name__, exc)
```

## メンタルモデル

整理すると、各層の責務は次のようになります。

```text
uv が答えること:
  どの Python と package を使っているか。

Jupyter が答えること:
  どの長寿命 Python プロセスが Notebook cell を実行しているか。

Linux/fontconfig が答えること:
  どの font file が存在し、それらがどの family name を公開しているか。

Matplotlib が答えること:
  設定された family name がどの font file に解決されるか。

backend が答えること:
  完成した figure をどのように表示・保存するか。
```

日本語が描画されないときは、この順番で確認します。

```text
1. 期待した kernel を使っているか。
2. Matplotlib はすでに import されていないか。
3. どの matplotlibrc が読み込まれているか。
4. 目的のフォントが fontManager.ttflist に存在するか。
5. findfont() はどの font file に解決しているか。
6. backend は表示・保存形式だけに関係していないか。
```

## 結論

「Notebook で何も設定しなくても日本語が表示される」環境は実現できます。ただし、その責務の多くは `uv` ではなく、OS/font discovery の層にあります。

安定した Linux 環境にするなら、次の流れが基本です。

```text
日本語フォントを標準的な OS font location にインストールする。
fontconfig tools をインストールする。
font cache を更新する。
matplotlibrc で Matplotlib の default font を設定する。
Jupyter kernel を再起動する。
```

portable な project demo にするなら、次の流れが現実的です。

```text
フォントを project にダウンロードする。
font_manager.addfont() で描画前に登録する。
rcParams を設定する。
```

前者は理想的な利用体験を作ります。後者は制御された実験として最も分かりやすい方法です。この 2 つの差分にこそ、Linux、uv、Jupyter、Matplotlib の境界があります。
