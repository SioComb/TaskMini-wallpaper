# 透明ダッシュボード仕様書
## （Wallpaper Overlay）

> PyQt6 で作成した、壁紙上に固定表示する軽量ダッシュボード。CPU/RAM/GPU/ネットワークの簡易モニタ、濃色カレンダー、アナログ＋デジタル時計を提供します。背面ウィンドウの操作を阻害しない“クリック透過”切替に対応。
> 

---

## 🧾 基本情報

- **名称**：Transparent Dashboard (transparent_clock.py)
- **目的**：Windows の壁紙レイヤー上に、システム指標とカレンダー／時計を常時表示
- **対象 OS**：Windows 10/11
- **フレームワーク**：PyQt6
- **言語／エンコード**：Python 3.11+ / UTF-8
- **表示レイヤー**：`WorkerW`（壁紙の親ウィンドウ）配下に配置

---

## 📦 依存関係

- `PyQt6`
- `psutil`
- `jpholiday`
- `pywin32`（`win32gui`, `win32con`, `win32pdh`）
- GPU カウンタ利用要件：Windows パフォーマンスカウンタで
    - **GPU Engine\Utilization Percentage**
    - **GPU Adapter Memory\Dedicated Usage / Dedicated Limit**
        
        が参照可能であること（環境により非対応の場合あり）
        

> インストール例
> 
> 
> ```bash
> pip install PyQt6 psutil jpholiday pywin32
> 
> ```
> 

---

## 🧭 画面構成とレイアウト

- **グリッド 2行×3列（余白 40 / セル間隔 36）**
    - 1行目：`CPU`｜`Calendar`｜`RAM`
    - 2行目：`GPU`｜`Clock（アナログ＋デジタル）`｜`Wi-Fi`
- **各パネル**は以下を共通表示
    - タイトル、サブタイトル（補足）、右肩の値（大）
    - 下部に追加情報
    - 中央にスパークライン（履歴グラフ）
- **背景**
    - 全体：半透明ダーク（放射状のぼかし）
    - パネル：角丸 14px、淡い枠線

---

## 🎛️ 機能仕様

### 1) CPU パネル

- **値**：`psutil.cpu_percent()` の瞬間値（%）
- **サブタイトル**：CPU 名の推定（取得不可時は汎用表記）
- **グラフ**：0–100%

### 2) RAM パネル

- **値**：`virtual_memory().percent`（%）
- **サブタイトル**：合計メモリ（GB）
- **追加情報**：`Used` / `Free`（GB）
- **グラフ**：0–100%

### 3) GPU パネル

- **値**：GPU Engine 使用率の合算（%）
- **追加情報**：VRAM 使用量（`Used` 単独 or `Used/Total` GB）
- **グラフ**：0–100%
- **取得方法（PDH）**：
    - `GPU Engine\Utilization Percentage`（全インスタンス合算）
    - `GPU Adapter Memory\Dedicated Usage` / `Dedicated Limit`（合算）
- **非対応時**：`-%` 表示、VRAM `-`

> PDH カウンタパスの注意（実装準拠）
> 
> 
> `win32pdh.MakeCounterPath((machine, object, instance, parentInstance, index, counter))`
> 
> 例：`(None, "GPU Engine", inst, None, 0, "Utilization Percentage")`
> 

### 4) ネットワーク（Wi-Fi）パネル

- **値**：下り `bytes_recv` の差分（KB/s or Mb/s）
- **追加情報**：上り `bytes_sent`（KB/s）
- **グラフ**：0–1024（KB/s スケール）
- **備考**：インタフェース名の検出は簡略化（サブタイトル固定文言）

### 5) カレンダー

- **見た目**：濃色、グリッド非表示、日曜始まり
- **色分け**：
    - **土**：`#00B7FF`
    - **日**：`#FF40FF`
    - **祝日**：`#4DE36B`（`jpholiday` 判定）
- **更新**：月内の日付書式を毎秒再適用（表示月基準）

### 6) 時計（中央下段）

- **アナログ**：時・分・秒針（秒針サブピクセル）
- **デジタル**：`HH:MM:SS`＋`YYYY-MM-DD Weekday`
- **レイアウト**：パネル内で自動リサイズ配置

---

## 🖱️ 入力・操作

- **F11**：フルスクリーン ↔ ウィンドウ表示（1460×820）
- **F10**：クリック透過切替（背面の操作を可能に）
- **Esc**：アプリ終了

---

## 🧩 クラス設計

### `SparkGraph(QWidget)`

- 目的：軽量折れ線グラフ
- 主プロパティ：`max_points`, `y_max`, `data (deque)`
- 主メソッド：
    - `push(float v)`：データ追加
    - `paintEvent()`：背景グリッド・折れ線描画

### `Panel(QWidget)`

- 目的：統一パネル UI（タイトル、値、補足、グラフ枠）
- 主プロパティ：`title`, `subtitle`, `value_text`, `extra_text`, `graph`
- 主メソッド：
    - `set_graph(g)`, `set_value(t)`, `set_extra(t)`, `set_subtitle(t)`
    - `paintEvent()`：パネル装飾＋子要素領域設定

### `CustomCalendar(QCalendarWidget)`

- 目的：濃色テーマ＋土日祝着色
- 主メソッド：
    - `update_calendar_colors()`：土日・祝日の書式を設定

### `AnalogClock(QWidget)`

- 目的：アンチエイリアスのアナログ時計
- 主メソッド：`paintEvent()`（針は角度計算で描画）

### `GPUMonitor`

- 目的：PDH で GPU 使用率／VRAM を収集
- フィールド：`query`, `engine_counters`, `mem_counters_usage`, `mem_counters_limit`
- 主メソッド：
    - `__init__()`：カウンタ列挙・追加（初回収集実行）
    - `read()`：最新値を取得し dict 返却（非対応時 `None`）

### `Dashboard(QWidget)`

- 目的：全 UI を構成・更新
- 主責務：
    - 透明ウィンドウ設定、クリック透過制御
    - 2×3 グリッドで各パネル配置
    - `WorkerW` 配下に再親化（壁紙レイヤー固定）
    - 1 秒周期更新（CPU/RAM/GPU/NET/時計/祝日）
- 主メソッド：
    - `to_fullscreen()`, `keyPressEvent(e)`
    - `_place_calendar(panel)`, `_place_clock(panel)`
    - `_cpu_name()`, `_ram_total()`, `_gpu_name()`, `_net_iface()`
    - `attach_to_wallpaper()`
    - `update_all()`：計測と UI 反映
    - `paintEvent()`：背景エフェクト

---

## 🔁 更新サイクル（1 秒毎）

1. **CPU**：%取得 → パネル値更新 → グラフ push
2. **RAM**：%と使用量/空き → 値/補足/グラフ更新
3. **GPU**：`GPUMonitor.read()` → 値/VRAM/グラフ更新（非対応時フォールバック）
4. **ネット**：IO 差分から速度算出 → 値/補足/グラフ更新
5. **時計/カレンダー**：中央レイアウト再配置＋祝日書式再適用

---

## 🪟 壁紙へのアタッチ仕様

- `get_workerw()`：
    - `Progman` へメッセージ送信 → `WorkerW` を列挙
    - `SHELLDLL_DefView` を持たない `WorkerW` を選定
- `attach_to_wallpaper()`：
    - `SetParent(self, workerw)` → `SetWindowPos(..., HWND_BOTTOM, SWP_NOACTIVATE)`

> これにより、常時壁紙の子として最背面に固定され、他アプリにフォーカスを奪わず表示されます。
> 

---

## 🧪 例外処理・フォールバック

- **PDH 取得失敗**（権限／非対応／カウンタ未登録）
    
    → `GPUMonitor` は空構成、`read()` 例外時 `None` 返却
    
    → GPU パネルは `--% / VRAM --` 表示に自動フォールバック
    
- **`WorkerW` 不在**
    
    → 通常の最背面ウィンドウとして表示（`SetWindowPos(HWND_BOTTOM)`）
    
- **文字描画等の失敗**
    
    → 値は空文字／固定文言で描画継続
    

---

## ⛏️ パフォーマンス設計

- 描画：アンチエイリアス有効（軽量図形のみ）
- グラフ：最大 300 点の `deque`（O(1) push）
- ポーリング：1 秒周期、PDH/psutil の軽量 API のみ
- 透過：`WA_TranslucentBackground`＋最少の再描画領域

---

## 🧱 既知の制約

- GPU 名の取得は未実装（サブタイトルは固定文言）
- ネットワーク IF 名の検出は固定（`Wi-Fi`表記）
- 月跨ぎ・表示月変更時の祝日再計算は**表示中の月**のみ対象
- DPI スケールの差異によってはフォントが意図より大きく／小さく表示される可能性

---

## 🛠️ セットアップ＆実行手順

1. 依存関係のインストール（上記参照）
2. スクリプトを実行
    
    ```bash
    python transparent_clock.py
    
    ```
    
3. **F11** で画面モード切替、**F10** でクリック透過切替、**Esc** で終了

---

## 🔧 拡張ポイント（提案）

- **GPU 名の表示**
    - `wmi` / `pynvml` / `dxdiag` のパース等で取得し、`_gpu_name()` に反映
- **ネット IF 自動検出**
    - `psutil.net_if_stats()` と `net_if_addrs()` で Up の主要 IF を選択
- **更新間隔の設定化**
    - `QTimer` の周期を設定ファイル（`ini`/`json`）で切替
- **テーマ／配色切替**
    - 色定義の集中管理（ライト／ダーク／アクセント）
- **履歴の保持／CSV 書き出し**
    - 指定秒数のリングバッファを CSV へ定期フラッシュ
- **月跨ぎの祝日更新最適化**
    - カレンダーの `currentPageChanged` シグナルで月変更時のみ再計算

---

## 🧷 テクニカルノート（実装の要点）

- **PDH カウンタパス**
    
    `MakeCounterPath()` は **6 要素タプル**
    
    `(machine, object, instance, parentInstance, index, counter)` を順守
    
    例：`(None, "GPU Adapter Memory", inst, None, 0, "Dedicated Usage")`
    
- **クリック透過**
    
    `WA_TransparentForMouseEvents` をトグルし、背面アプリへの入力を許可
    
- **壁紙レイヤー**
    
    `WorkerW` の選定時、`SHELLDLL_DefView` を持たないウィンドウを採用（アイコン描画と干渉しない）
    

---

## ✅ 受け入れ基準

- アプリ起動後、**壁紙の上**に 2×3 パネルが表示されること
- 1 秒周期で各値が更新され、グラフに履歴が追加されること
- **F10** で背面のボタンがクリック可能／不可に切り替わること
- GPU 非対応環境でも異常終了せず、GPU パネルが `-` フォールバックすること
- **Esc** で正常終了すること

---

## 🪪 ライセンス／著作権

- 本仕様書は提供コードに基づく利用者向け技術資料。
    
    第三者コード（PyQt6, psutil, pywin32 等）のライセンス順守は利用者責任。
    

---

## 🗂️ 変更履歴（ドキュメント）

- **2025-08-16**：初版作成（PDH パス仕様の明記、クリック透過／壁紙レイヤー要件整理）