# プロセカ遅延・判定ばらつき修正 作業ログ

対象: RedMagic 11 Pro (NX809J) / EvolutionX A17 20261010 MinimalGApps
目的: 公式プロセカ（無改変）で Great を減らし、安定して Perfect を取れる OS にする。テスト楽曲は「ray」。
元の依頼文: `prsk/docs/plan.md`（非公開）

ファイルの置き場所（2026-11-12 に整理）:
- この文書と実験用の設定ファイル（`docs/audio/`）、計測・解析スクリプト（`scripts/audio/`）、修正（`module/` の KernelSU モジュール `gps_incamera_audio_fix`）は rmGPSfix リポジトリにある。
- 計測データ（録音・ログ・スクリーンショット）、公式アプリのバックアップ、APK、端末設定のスナップショットは `prsk/`（独立した非公開の git、rmGPSfix からは除外）にある。文中の `prsk/logs/`、`prsk/backup/`、`prsk/snapshot/` はそこを指す。
- 文中の `rhythm_latency_fix` は、音声の修正を単独で入れていた旧モジュール（v0.1）。v3.0 で `gps_incamera_audio_fix` に統合した。

## 現在地点

**2026-11-12 04:50 時点の結論: 音ゲーは 3.5 mm の有線イヤホンで遊ぶのが最善。** プロセカのタップ → SE は、有線で 30.8 ms、スピーカーで 66 ms（iPad mini のスピーカーは 43 ms）。ray EXPERT（BGM なし）を有線で遊んだ結果は PERFECT 971 / GREAT 7（これまでで最良）。ユーザーの感想は「今までで一番 iPad に近いかも」。

遅延の内訳（スピーカー 66 ms の場合、実測からの推定）:
| 区間 | 量 | 根拠 |
|---|---|---|
| タッチ → アプリ | 10 ms 台前半以下 | 有線の Tap-to-Tone が合計 20 ms |
| ゲーム内（フレーム待ち + CRIWARE） | 約 12 ms | プロセカ 66 ms − OboeTester 54 ms |
| OS の音声経路（報告値） | 8〜13 ms | AudioFlinger / AAudio の報告値 |
| **スピーカーの出力経路（OS の報告に出ない）** | **約 35 ms** | スピーカー 55 ms − 有線 20 ms（同じアプリ・同じ解析） |

- スピーカー経路の 35 ms は、ADSP のスピーカー用の処理〜Awinic アンプのどこかにある。スピーカー保護を外しても変わらなかった。設定ファイルからは原因を特定できず、ソフトの設定では縮められない見込み。
- OS 側でできる対策（タッチ 363 Hz、Extra loudness オフ、`raw_out` の追加）は適用済み。スピーカーで遊ぶ場合は 66 ms が下限。

### 端末の現在の状態
- rmcontrol: 「Touch sampling while gaming = 720 Hz」（実測 363 Hz）、「Extra loudness = オフ」。
- KernelSU モジュール `rhythm_latency_fix` v0.1 を導入済み。`raw_out`（FAST|RAW）を音声 HAL 設定に追加する。有線ヘッドセットでもゲームの音は `raw_out` に乗る（確認済み）。
- `audio.pro` の申告は効果なしで無効化済み（`PRO=0`）。ただし最後の再起動より後に書き換えたので、**次に再起動するまでは申告が有効なまま**（04:12 時点でも有効）。
- スピーカー保護の実験は元に戻した（bind mount を解除、一時ファイルを削除、保護のログが再び出ることを確認）。
- OboeTester 2.8.19 を導入済み（ユーザーが Play ストアから）。
- 音声の修正は `gps_incamera_audio_fix` v3.0（`module/`）に統合した（2026-11-12）。端末にはまだ旧モジュール `gps_incamera_fix` v2.0 と `rhythm_latency_fix` v0.1 が入っている。入れ替えるときは両方を外してから v3.0 を入れる（同じ音声設定ファイルを二重に差し替えないため）。

### 次にやること（優先順）
1. 有線での判定調整（音ズレ補正）の確認。BGM ありの MASTER を数回遊び、FAST / LATE の偏りを見る。BGM なしの EXPERT 1 回では LATE 2 / FAST 5 で、今の値のままでもおおむね合っていそう。スピーカーと有線では必要な調整値が約 35 ms 違う。
2. リトライごとのオフセットずれが今も起きるかの確認（未検証）。
3. ROM 作者・メーカーへの報告（ユーザーが希望すれば文面を作る）: Extra loudness がスピーカーで全アプリの FAST を無効にする件、`sku_canoe` の設定に `raw_out` が無い件（純正も同じ）、スピーカー経路に OS の報告に出ない約 35 ms がある件（スピーカー 55 ms / 有線 20 ms / 受話口 23 ms（往復）/ 報告値 10 ms）。

### 今後チャレンジする項目（スピーカーをステレオのまま速くする。2026-11-12 にユーザーと合意して保留）
原因は ADSP がスピーカー用にだけ組む処理グラフ（約 33 ms）と確定している。アンプのプロファイルとスピーカー保護は無関係。詳細は「スピーカー経路の迂回策の調査」の節。
1. **ACDB の解析（読み取りのみ）**: `MTP_canoe_wsa884x_acdb_cal.acdb` のチャンク構造を読み、スピーカー（DEVICERX = SPEAKER）のデバイス後処理グラフに入っているモジュール ID を、AudioReach の公開ヘッダのモジュール ID と照合する。受話口・ヘッドセットのグラフとの差分が本命。対応表 `.qwsp` は暗号化されていて使えない。
2. **原因モジュールの無効化の実験**: 特定できたら、較正データでそのモジュールを無効（MODULE_ENABLE = 0 など）にした `.acdb` を bind mount で試す。失敗すると音が出なくなるが、外せば戻る。リミッター類を外す場合は小音量で行い、常用するかは別に判断する。
3. **受話口経路の 2 チャンネル化**（最終手段）: handset デバイスを 2 チャンネル・アンプ 2 個（Music）にして、メディアをそこへ回す。ルーティング（`setPreferredDevicesForStrategy` 相当）と受話口用グラフの 2 チャンネル化が必要。
- 前提: 受話口だけのモノラル再生は音ゲーとしては不可（ユーザーの判断）。
- 補助: 実行中のグラフのモジュール一覧は ALSA コントロール（`PCMxxx getTaggedInfo` など）から読める可能性があるが、端末に `tinymix` が無い。

### 当面の運用
- 音ゲーは 3.5 mm の有線イヤホンで遊ぶ（プロセカのタップ → SE 30.8 ms）。スピーカーでは 66 ms が下限。

### 計測のやり方（再現用）
- プレイ中の端末状態: `scripts/audio/capture_baseline.sh [秒] [ラベル]`
- タッチ報告レート: `CFGS="rate,game ..." scripts/audio/touch_rate_sweep.sh [秒]` と `scripts/audio/analyze_getevent.py`
- OS の下限: OboeTester の TAP TO TONE LATENCY（緑の枠を叩く）を `scripts/audio/record_mic.sh 75 <ラベル>` で録音し、`analyze_tap_tone.py <wav> [--min 1.5]`。端末とイヤホンはマイクのすぐ横に置く。往復遅延は ROUND TRIP LATENCY の AVERAGE。
- 有線イヤホンで測るときは、イヤホンと端末の両方をマイクのすぐ横に置く（叩く音と SE の両方を拾うため）。
- タップ → SE の実測: PC 内蔵マイクを ffmpeg（dshow、`マイク配列 (Realtek(R) Audio)`、48 kHz モノラル）で録音し、`scripts/audio/analyze_tap_audio.py <wav>`。プレイ条件は ray EXPERT、BGM 音量 0、SE オン、爪で打鍵、端末をマイクの近くに置く。

### やらないと決めたこと
- 公式 APK の改変・再パッケージ、保護の解除。調査は外側からの計測と、保護されていない部分の読み取りに限る。
- スピーカー保護（`speaker_protection_enabled`）の常用の無効化。スピーカーを壊すおそれがある。音量 3 での一時的な検証はユーザーの依頼で実施済みで、遅延に効果は無かった。
- 音声 HAL バイナリの書き換え（出力周期 144 → 96 フレーム）。効くか不明の 2〜4 ms に対して手間が大きい。ユーザーが希望すれば再検討。

## 実機の現状（2026-11-11 に adb で確認）

| 項目 | 値 |
|---|---|
| プロセカ | `com.sega.pjsekai` 7.1.0 (versionCode 300131)、base + split 4 本 |
| サイズ | APK 一式 704 MB / 内部データ 10 MB / `/sdcard/Android/data` 8.1 GB |
| root | KernelSU（`su` 利用可） |
| SoC / kernel | SM8850 (canoe) / 6.12.38-android16 |
| タッチ IC | `synaptics_tcm_touch`（`/dev/input/event7`） |
| 画面モード | 60 / 90 / 120 / 144 Hz |
| 音声 prop | `aaudio.mmap_policy=2`、`aaudio.hw_burst_min_usec=2000` |
| 管理アプリ | `com.nubia.rmcontrol` あり |

20261010 の CHANGELOG にはタッチサンプリングレートの記載が見当たらない。「入ったと言われている」修正は実測で確かめる（P2）。

## 依頼内容の矛盾・不明点

1. **「同ロジック・ソースをもとにしたデバッグアプリ」は作らない方針にしたい。**
   プロセカのソースは手元になく、作るには公式 APK の逆コンパイル・改ざん検知の回避・再パッケージが要る。これは規約違反で、こちらでは手伝えない。技術的にも遠回りになる。最終的に直したいのは無改変の公式アプリなので、計測も無改変の公式アプリに対して行う必要がある。
   代わりに次の 2 本立てにする。
   - **A. 公式アプリの外側からの計測**（改変なし）: `getevent`、perfetto、`dumpsys media.audio_flinger`、SurfaceFlinger のフレーム統計、マイク録音。
   - **B. 自作の遅延計測ベンチ**: プロセカと同じ Unity バージョン・同じ音声出力経路を使う最小アプリ。タッチ時刻・フレーム時刻・音声コールバック時刻をログに出す。譜面と音源は自前のもの（「ray」の音源や譜面は使わない）。
   公式アプリでの「ray」プレイ結果は、最終的な効果確認に使う。
2. **症状は 3 つの別問題。** 原因も直せる範囲も違うので分けて扱う。
   - 判定のばらつき → タッチ入力の報告レートとジッタ、フレーム単位の入力取り込み
   - SE の遅れ → 音声出力遅延（fast track に乗っているか、バッファ長、エフェクト経由）
   - リトライごとのオフセットずれ → ゲーム側の音声時計と曲位置の同期。**OS 側では直せない可能性がある。** ストリーム再生成のたびに出力遅延が変わる、アンダーランが起きる、といった OS 起因なら直せる。P2 で切り分ける。
3. **バックアップ範囲。** 方針 1 なら 8.1 GB のアセットは不要（再ダウンロードできる）。APK 一式 704 MB と内部データ 10 MB だけ取る。アカウントは念のため公式の引き継ぎ設定もしておく。
4. **「Great が減る」の測り方が未定義。** 数値目標を置く（下の「成功基準」）。
5. **OS 変更の範囲。** これまでと同じ KernelSU モジュール（prop・sysfs・設定ファイル差し替え）を想定。カーネルや ROM の再ビルドは、モジュールで届かないと分かった時点で相談する。

## 確認待ち

- [x] 上の 1（デバッグアプリを自作ベンチ + 外側計測に置き換える）で進めてよいか → 了承（2026-11-11）
- [x] 音の出力先 → 本体スピーカー
- [x] 「ray」の難易度と現在の結果 → MASTER (Lv.26)。ベースライン 1 回目は下記
- [ ] ゲーム内設定: 判定調整の値、ノーツ速度、タップ音の有無、軽量化設定、MV 設定
- [ ] rmcontrol / ゲームスペースの現在の設定（タッチ感度、サンプリングレート、性能モード）
- [ ] iPad mini 側も同じ方法で測るか（マイク録音によるタップ音→SE の遅延比較は可能）

## 成功基準（案）

- タッチ報告レート: 設定値どおり出ていて、間隔のジッタが p99 で 1 報告周期以内
- タップ→SE の遅延（マイク実測）: 中央値と p99 を修正前後で比較し、ばらつき（p99 − p50）を縮める
- リトライ 10 回での遅延の変動: 1 フレーム (8.3 ms) 未満
- 「ray」同一難易度 5 回プレイの Great 数の平均が、修正前より明確に減る

## マイルストーン

### P0 準備
- [x] `prsk/` を独立 git として初期化（親リポジトリの `.gitignore` には `prsk/` 登録済み）。コミットは未実施
- [x] `prsk/.gitignore` に APK・ログ・録音を登録
- [x] APK 一式（5 本、実機とサイズ一致）を `prsk/backup/apk/`、内部データを `prsk/backup/data/pjsekai_data.tgz` に退避
- [x] 現状スナップショットを `prsk/snapshot/` に保存: `getprop`、audio_flinger（アイドル時）、audio_policy、タッチ sysfs、rmcontrol パッケージ情報
- [ ] rmcontrol の実際の設定値（UI 上の設定）は未取得

### P1 公式アプリの構成調査（改変なし）
- [x] Unity バージョン、音声ミドルウェア、同梱ネイティブライブラリ名を APK から読む（結果は下の「P1 で分かったこと」）
- [ ] プレイ中の `dumpsys media.audio_flinger` で出力経路を確認（FAST か、サンプルレート、バッファ長、エフェクト）
- [ ] プレイ中のリフレッシュレートと実フレームレートを確認

### P2 ベースライン計測（公式アプリ、無改変）
- [ ] `getevent -lt` でタッチ報告レートとジッタ（静止時・プレイ中・複数指）
- [ ] perfetto: 入力 → アプリ → 描画、スケジューラ、CPU 周波数、音声スレッド
- [ ] マイク録音でタップ音→SE の遅延分布
- [ ] リトライ 10 回での遅延変動、アンダーラン回数
- [ ] 発熱時とそうでない時の差
- [ ] 「ray」5 回プレイの結果を記録（ユーザー）

### P3 自作ベンチ
- [ ] P1 で分かった Unity バージョン・音声経路に合わせた最小アプリ
- [ ] タッチイベント時刻 / フレーム時刻 / 音声コールバック時刻のログ出力
- [ ] ベンチで公式アプリと同じ傾向が再現するか確認

### P4 原因の切り分けと OS 側の調整（1 変数ずつ）
- [x] タッチ: 報告レート 0〜4 と `play_game` を実測。rmcontrol の設定が gameperfd 経由で効くことを確認。IRQ の割り当ては未調査（不要と判断）
- [x] 音声: FAST が外れる原因は loudness のグローバルエフェクト。オフで解消
- [ ] スケジューラ: top-app の uclamp / cpuset、ガバナ、サーマル制限
- [ ] 表示: リフレッシュレートの固定、フレームペーシング

### P5 モジュール化と実プレイ検証
- [x] 効いた変更の常時適用 → ROM の設定で実現（モジュール不要。`module/` は予備の下書き）
- [x] 「ray」で修正前後を比較（各 1 回。GREAT 26 → 8）
- [ ] 普段使いへの副作用確認（電池、発熱、通話、音楽再生）

### P6 記録
- [ ] 手順と結果をこのファイルにまとめる

## P1 で分かったこと（APK のファイル一覧と文字列のみ。改変・逆コンパイルなし）

- Unity **2022.3.62f2**、IL2CPP（`libil2cpp.so`）。
- 音声は **CRIWARE**（`libcri_ware_unity.so`）。ライブラリは **AAudio** の API を参照している（`setPerformanceMode`、`setSharingMode`、`setFramesPerDataCallback` など）。実際にどのモードで開いているかはプレイ中の `dumpsys` で確認する。
- 端末側は `aaudio.mmap_policy=2`（MMAP 可）。ゲームが低遅延モードを要求していなければ、MMAP にも FAST にも乗らない。ここが SE 遅延の第一候補。
- タッチ: `/proc/touchscreen/` に ZTE 独自ノードがある。`tp_report_rate` の現在値は `1`（意味は未確認）。ほかに `play_game`、`single_game`、`sensibility`、`follow_hand_level`、`stability_level`、`game_partition`。rmcontrol がここを書いているかを P2 で確かめる。
- Sekai-World（GitHub）は判定・音声のコードを含まない。譜面形式（SUS）の資料として、ベンチの譜面密度を決める参考にする。

## P2 ベースライン 1 回目（2026-11-11 23:09、`prsk/logs/20261111_230915_ray_speaker/`）

条件: 本体スピーカー、判定強化なし、120 Hz、発熱なし（Thermal Status 0、skin 30 ℃）。
結果: ray MASTER — PERFECT 1062 / GREAT 26 / GOOD 1 / BAD 0 / MISS 3、LATE 20 / FAST 7、最大コンボ 565。

### 音声（`dumpsys media.audio_flinger`）
- ゲームのトラックは 2 本（ID 144 / 145）。どちらも **低遅延（FAST）トラックではなく通常ミキサー経由**。MMAP ストリームも 0 本。
- AudioFlinger が報告するトラック遅延は **150.70 ms と 130.58 ms**。内訳はアプリ側バッファ 3848 / 2886 フレーム（80 / 60 ms）＋通常ミキサーの書き込み遅延 約 70.7 ms。
- 同じ出力（`AudioOut_D`、スピーカー）には FAST ミキサーがあり、周期 4 ms・遅延 21 ms で動いている。ゲームがそこを使っていないだけ。
- トラック 145 のアンダーラン累計 47034。ただし計測中は増えておらず、過去の累計。
- 出力にはグローバルの Loudness Enhancer エフェクトが 1 つ載っている（無効状態）。
- LATE 20 / FAST 7 と遅い側に偏っているのは、出力遅延が大きいことと矛盾しない（因果は未確認）。

### タッチ（`getevent -lt`、162 秒・タッチ開始 735 回）
- 報告間隔の中央値 **5.57 ms（約 180 Hz）**。92.6% が 4.5〜6 ms に収まる。
- 9 ms 以上の間隔が 7% ある。指が静止している間は報告が出ない可能性があり、これをジッタとは断定できない。静止時とスワイプ時を分けて測り直す。
- プレイ中ずっと `play_game=0`、`tp_report_rate=1`、`single_game=1`、`sensibility=2`、`follow_hand_level=2`、`stability_level=2`。ドライバのゲームモードは入っていない。

### 表示・CPU
- 画面は 120 Hz 固定で動作。ゲームは `top-app` cgroup。ガバナは walt。
- ゲームの実描画フレームレートは未取得（この ROM では timestats が空を返した）。スクリプトを `--latency` 方式に変更済み。リザルト画面は 60 fps 描画だった。ライブ中は次回のプレイ計測で確認する。

## P4 タッチ: 報告レートの切り替えテスト（2026-11-11 23:17、`prsk/logs/20261111_231501_touch_sweep/`）

`/proc/touchscreen/tp_report_rate` に値を書き、指 1 本で円を描きながら各 10 秒測った。終了後は元の値（1 / 0）に戻した。

| 書いた値 | ドライバのログ | 実測の中央値 | 実測レート | p1〜p99 |
|---|---|---|---|---|
| 0 | success in 120Hz | 8.01 ms | 125 Hz | 7.83〜8.21 ms |
| 1（現状） | success in 180Hz | 5.57 ms | 179 Hz | 5.34〜5.77 ms |
| 2 | success in 300Hz | 3.33 ms | 300 Hz | 3.13〜3.52 ms |
| 3 | success in 360Hz | 4.18 ms | **239 Hz** | 3.97〜4.41 ms |
| 4 | success in 720Hz | 2.75 ms | **363 Hz** | 2.55〜2.95 ms（再測定 23:20、20 秒、`prsk/logs/20261111_232035_touch_sweep/`） |

- 連続して触れている間の間隔は揃っている（p1〜p99 の幅 0.4 ms 前後）。ベースラインで見えた 9 ms 以上の間隔は、ジッタではなく指の静止や離接によるものとみてよい。
- 値 3 は「360Hz」と出るのに実測 239 Hz。値 2（300 Hz）のほうが速い。
- 値 4 は 1 回目はイベント 0 件（指を離していたとみられる）。再測定でタッチは正常に反応し、実測 363 Hz。「720Hz」表示の半分だが、5 段階で最速。
- 表示と実測のずれ: 値 3 は 360→239 Hz、値 4 は 720→363 Hz。指 1 本での測定なので、複数指での変化は未確認。
- `play_game=1` の効果は未測定。
- ROM の既定値は 1（180 Hz）。rmcontrol はプロセカ起動中もこれを変えていない。

## P4 タッチ: `tp_report_rate=4` でのプレイ（2026-11-11 23:22、`prsk/logs/20261111_232256_ray_speaker_rate4/`）

| | PERFECT | GREAT | GOOD | MISS | LATE / FAST | コンボ |
|---|---|---|---|---|---|---|
| 現状（値 1、179 Hz） | 1062 | 26 | 1 | 3 | 20 / 7 | 565 |
| 値 4（362 Hz） | 1075 | 17 | 0 | 0 | 12 / 5 | 1092（フルコンボ） |

- プレイ中の実測 362 Hz（間隔の中央値 2.76 ms）。ユーザーの体感も「かなりマシ」。
- 各 1 回ずつの比較なので、差が設定によるものかは回数を重ねて確認する。
- ライブ中の描画は **120 fps で安定**（フレーム間隔 8.30 ms、p95 も 8.30 ms）。60 fps なのはメニューとリザルトだけ。
- 残る体感: 「譜面が少し早く流れてくる」。LATE 側への偏りも残っている。音が遅れて出ていることと整合する。

## P4 音声: 低遅延要求が OS に拒否されている（2026-11-11 23:25、`prsk/logs/media_metrics_2325.txt`）

`dumpsys media.metrics` のトラック生成記録:

- 呼び出し元は **OpenSL ES**（`callerName=opensles`）。AAudio ではなかった。
- ゲームの要求は `originalFlags=AUDIO_OUTPUT_FLAG_FAST|AUDIO_OUTPUT_FLAG_RAW`。
- 実際に付いたのは `flags=AUDIO_OUTPUT_FLAG_NONE`。**ゲームは低遅延を要求し、OS 側が外している。**
- その結果 `frameCount=3848 / 2886` の大きなバッファで通常ミキサーに回り、遅延が 130〜150 ms になっている。
- 拒否理由は生成時（22:27）の logcat に出るが、すでに流れて残っていない。ゲーム再起動時の logcat で取る。
- 候補: 出力ミックス（セッション 0）に常駐している Loudness Enhancer。持ち主は `loudness` というシステムプロセス（pid 2105）。エフェクトが載った出力では FAST/RAW が外されることがある。未検証。

## P4 音声: 原因は ROM の `loudness` サービス（2026-11-11 23:31、`prsk/logs/af_noloudness.txt`）

- `loudness`（`/system_ext/bin/loudness`、`persist.sys.loudness.enabled=1` で起動）は、スピーカー出力のミックス全体に Loudness Enhancer を掛ける ROM 独自の音量かさ上げサービス。
- `su -c "stop loudness"` で止めると、`AudioOut_D` のエフェクトチェーンが 1 → 0 になった。
- その状態でゲームを起動し直すと、トラックが FAST で作られた。

| | フラグ | バッファ (frames) | 報告遅延 |
|---|---|---|---|
| loudness 動作中 | NONE（要求は FAST\|RAW） | 3848 / 2886 | 150.7 / 130.6 ms |
| loudness 停止 | **FAST** | 1536 / 384 | **53 / 29 ms** |

- 拒否理由のログは出なかった（該当メッセージは verbose で、この ROM では出力されない）。因果は停止前後の比較で確認した。
- 一時停止なので再起動で元に戻る。恒久化は `persist.sys.loudness.enabled=0`（スピーカー音量のかさ上げは無くなる）。ゲーム中だけ止める方式も検討する。
- 音が約 100 ms 早く出るようになるので、ゲーム内の判定調整値は合わせ直しが必要になる可能性がある。

## 対策を両方当てたプレイ（2026-11-11 23:32、`prsk/logs/20261111_233214_ray_speaker_rate4_noloudness/`）

ray MASTER、判定強化なし、本体スピーカー、ゲーム内の判定調整は 3 回とも 0.0。各 1 回ずつ。

| 条件 | PERFECT | GREAT | GOOD | MISS | LATE / FAST |
|---|---|---|---|---|---|
| 元の状態（179 Hz、音声 130〜150 ms） | 1062 | 26 | 1 | 3 | 20 / 7 |
| タッチのみ（362 Hz） | 1075 | 17 | 0 | 0 | 12 / 5 |
| タッチ + loudness 停止（362 Hz、音声 29〜53 ms） | 1082 | 8 | 0 | 2 | 2 / 6 |

- プレイ中もトラックは FAST のまま（29 / 53 ms）、エフェクト 0、120 fps 安定、タッチ 362 Hz。
- LATE への偏りが消えて FAST 寄りになった。音が早く出るようになった分の変化と整合する。
- ユーザーの体感: 「全然違う」「AP 圏内になった感じ」。
- 未着手: リトライごとのオフセットずれの検証、iPad mini との比較、マイク実測。

## ROM 既存の仕組みの調査（2026-11-11 23:43）

`com.nubia.rmcontrol`（RedMagicControl）と `io.chaldeaprjkt.gamespace`（GameSpace）の APK 文字列、init rc、`/vendor/bin/gameperfd` を読んだ結果。

- **GameSpace** はゲーム一覧とモードを持つ。`gamespace_game_list` に `com.sega.pjsekai=2`（Performance）で登録済み。対象ゲームが前面に来ると `persist.sys.power_mode_perf=1` を立てる。プロセカ前面時に 1 になることを確認した。
- **gameperfd**（`/vendor/bin/gameperfd`、常駐）がその prop を見て、CPU ブーストとタッチ設定を適用する。タッチは `persist.sys.rm.gametouch.rate` の値で `/proc/touchscreen/tp_report_rate` と `play_game` を書き、ゲームを離れると戻す。
- **rmcontrol** はその設定画面。Touch タブに「Touch sampling while gaming」（Off (180 Hz) / 300 Hz / 360 Hz / 720 Hz）がある。説明文: 通常は 180 Hz、Performance モードのゲームが前面の間だけ指定レートとパネルのゲームモードに切り替える。純正 ROM の「960 Hz」はこの 720 Hz 設定に当たる。
- **`persist.sys.rm.gametouch.rate` は `0` だった。** つまり「Off (180 Hz)」のまま。「タッチサンプリングレートの修正が入ったのに変化を感じない」の理由はこれ。機能は入っていたが、設定が有効化されていなかった。
- **loudness** も rmcontrol の「Extra loudness (makeup gain)」（クイック設定タイルあり）で切れる。`persist.sys.loudness.enabled` を 0 にするスイッチ。
- 自作の `module/` は不要になる見込み。ROM の設定で足りなかった場合の予備として残す。試運転用に端末で動かしていた監視スクリプトは停止・削除済み。
- ROM 側の不具合として報告する価値がある点: Extra loudness を有効にすると、スピーカー出力で全アプリの FAST|RAW 要求が外れ、音声遅延が約 100 ms 増える。

## ROM 設定での最終確認（2026-11-11 23:48、`prsk/logs/20261111_234903_touch_sweep/`）

rmcontrol で「Touch sampling while gaming = 720 Hz」「Extra loudness = オフ」に変更し、プロセカを起動し直した状態。

- `persist.sys.rm.gametouch.rate=4`、`persist.sys.loudness.enabled=0`、`init.svc.loudness=stopped`。
- プロセカ前面で gameperfd が「touch gear 4 + game mode」を適用。`tp_report_rate=4`、`play_game=1`。
- 音声トラックは FAST（1536 / 384 フレーム）、スピーカー出力のエフェクト 0。
- ゲームモード併用時の実測: 間隔の中央値 2.75 ms、**363 Hz**（p1〜p99 = 2.56〜2.98 ms）。ゲームモードなしの値 4 と同じ。**OS に届く報告レートの上限は 363 Hz で、`play_game` はレートを変えない。**「720Hz」「960Hz」は OS への報告レートではない。
- `play_game=1` が判定の安定に効くか（感度やフィルタの違い）は未検証。

## さらなる低遅延化の候補（2026-11-11 23:55 調査、未適用）

現状の音声遅延（AudioFlinger 報告値）: SE 側トラック 29 ms = アプリ側バッファ 384 フレーム (8 ms) + FAST ミキサー経路 21 ms。BGM 側 53 ms = 1536 フレーム (32 ms) + 21 ms。報告値は HAL の申告で、実際の音の遅れは未実測。

### 候補 A: `raw_out` 出力の追加（本命）
- ゲームの要求は `FAST|RAW`。現在は FAST だけ通り、通常の低遅延出力 `low_latency_out` に乗っている。
- Qualcomm の基本設定 `/vendor/etc/audio/audio_module_config_primary.xml` には `raw_out`（flags `FAST RAW`、スピーカーへのルートあり）がある。
- 実際に読み込まれている `/vendor/etc/audio/sku_canoe/audio_module_config_primary.xml` には `raw_out` が無い。audio policy のダンプにも出てこない。
- HAL 側には対応コードがある（`libaudiocorehal.qti.so` に `UllPlayback`、`ULL_PLAYBACK`。resourcemanager に `PAL_STREAM_ULTRA_LOW_LATENCY`）。
- `module/audio_module_config_primary.xml` に `raw_out` を足した版を用意した（mixPort 1 個と、speaker / wired_headset / wired_headphones / usb_device_out / usb_headset の 5 ルートに追記）。`module/post-fs-data.sh` で bind mount する。
- 効果は未知。ULL 経路は DSP の後処理を通らないので短くなる見込みだが、数値は試さないと分からない。スピーカー保護などとの相性で音が出ない・歪む可能性もある。
- 純正 ROM の設定に `raw_out` があるかは未確認。

### 候補 B: 有線 / USB-C 出力
- スピーカー経路はアンプ保護などの DSP 処理が入る。有線や USB DAC は短いことが多い。設定変更なしで試せる。

### 候補 C: `af.fast_track_multiplier=1`
- FAST トラックのバッファを 384 → 192 フレームに（−4 ms）。音切れのリスクあり。OpenSL 経由のトラックに効くかは未確認。

### 伸びしろが無いと判断したもの
- タッチ: OS に届く報告は 363 Hz が上限。
- 描画: ライブ中 120 fps 安定。ROM のフレーム補間（GPP）はオフ（`persist.sys.rm.gpp=0`）。

### 前提として必要なもの
- 実際の音の遅れを測る手段（マイク録音）。これが無いと、候補 A〜C の効果を報告値でしか比べられない。

## マイク実測 1 回目（2026-11-12 00:13、`prsk/logs/mic/tap_20261112_001340_baseline.wav`）

PC 内蔵マイク（Realtek マイク配列）で 40 秒録音。条件: 本体スピーカー、loudness オフ、タッチ 363 Hz、FAST トラック。解析は `scripts/audio/analyze_tap_audio.py`（叩く音 = 低域の立ち上がり、SE = 8 kHz 以上が 10 ms 以上続く区間）。

- 叩く音 20 回のうち、SE を対応付けできたのは 9 回。残り 11 回は 250 ms 以内に SE が無かった（SE が鳴らない場所を叩いた可能性）。
- タップ → SE: 76.5 / 80.5 / 82.5 / 88.5 / 89.0 / 91.5 / 93.5 ms など。**中央値 88.5 ms**。1 回だけ 189 ms（外れ値か別の音の誤対応）。
- 録音の前半には、叩く音を伴わない SE が約 2 秒おきに 7 回あった（弱いタップで叩く音が拾えなかったとみられる）。
- サンプルが少なく、操作内容も不明確なので参考値。条件を揃えて取り直す。
- AudioFlinger の報告値（SE 側 29 ms）より 50〜60 ms 長い。差はタッチ → ゲームのフレーム処理 → CRIWARE 内部のミキシングで生じているとみられ、OS の音声経路だけでは説明できない。

## マイク実測 2 回目・基準値（2026-11-12 00:18、`prsk/logs/mic/tap_20261112_001819_ray_nobgm.wav`）

ray EXPERT、BGM 音量 0、SE オン、中盤以降は爪で打鍵。PERFECT 969 / GREAT 9、フルコンボ、LATE 4 / FAST 5。
条件: 本体スピーカー、loudness オフ、タッチ 363 Hz + ゲームモード、FAST トラック。

解析スクリプトを作り直した（叩く音 = 2-8 kHz の鋭い立ち上がり、SE = 8 kHz 以上の持続的な立ち上がり、直前 60 ms が静かなタップのみ採用）。

- 条件を満たすタップ 305 回、SE を対応付けできたもの 108 回。
- **タップ → SE: 中央値 79.2 ms**、p25〜p75 = 72.6〜83.5 ms、p10〜p90 = 59.7〜88.9 ms。70〜90 ms に 74 回（69%）。
- 四分位幅 11 ms は、120 fps のフレーム周期 8.3 ms と音声エンジンの処理周期によるばらつきとして説明がつく範囲。
- 内訳の見立て（未検証）: OS の音声経路 約 29 ms（報告値）、タッチ〜フレーム取り込み 約 10 ms、残り約 40 ms がゲーム内（CRIWARE のミキシングとバッファ）。
- loudness オンの状態では測っていない。報告値どおりなら約 100 ms 長かったはず。

## `raw_out` の一時適用と実測（2026-11-12 00:23、`prsk/logs/mic/tap_20261112_002408_ray_nobgm_rawout.wav`）

適用方法: `module/audio_module_config_primary.xml` を `/data/local/tmp/rlf_audio.xml` に置き、init の mount 名前空間で `/vendor/etc/audio/sku_canoe/audio_module_config_primary.xml` に bind mount。`vendor.audio-hal-aidl` と `audioserver` を再起動。再起動で消える。

- audio policy に `raw_out`（0x0104、FAST|RAW）が現れ、出力スレッド `AudioOut_15` が開いた。HAL フレーム数 144（3 ms）、FAST ミキサー周期 3 ms、遅延 7 ms（`low_latency_out` は 192 / 4 ms / 21 ms）。エフェクト 0。
- 起動中のプロセカのトラックは自動で作り直され、`FAST|RAW` で `raw_out` に乗った。フレーム数 288 / 1536、報告遅延 13 / 39 ms（適用前 29 / 53 ms）。
- ユーザーの聴感: 音量は小さくなり、少し柔らかい音になった。途切れなし。

| | タップ → SE 中央値 | p25〜p75 | p10〜p90 | n |
|---|---|---|---|---|
| `low_latency_out`（FAST） | 79.2 ms | 72.6〜83.5 | 59.7〜88.9 | 108 |
| `raw_out`（FAST\|RAW） | **66.0 ms** | 61.0〜70.6 | 50.0〜76.1 | 120 |

- 実測で 13 ms 短縮。報告値の差（14〜16 ms）とほぼ一致。
- プレイ結果（ray EXPERT、BGM なし、爪）: 適用前 PERFECT 969 / GREAT 9 / LATE 4 / FAST 5、適用後 PERFECT 967 / GREAT 9 / MISS 2 / LATE 0 / FAST 9。
- 適用後は FAST に偏った。BGM なしのプレイなので原因は切り分けられていない（ユーザーの見立て: 音楽が無いせい）。BGM ありで確認する。
- 未確認: この経路でスピーカー保護が効いているか。音量が下がった理由（かさ上げ処理を通らないためとみられる）。

## これ以上の短縮の検討（2026-11-12 00:35）

- **`af.fast_track_multiplier=1` は効果なし。** audioserver を再起動して確認したが、SE 側トラックは 288 フレームのまま。このバッファ長はアプリ（OpenSL / CRIWARE）側の要求で決まっている。prop は 2 に戻した（audioserver は 1 を読んだまま動いているが、挙動は変わらない。再起動で消える）。
- 現在の OS 側の音声経路（報告値）: SE 側 13 ms = アプリ要求のバッファ 6 ms + `raw_out` 7 ms（周期 3 ms）。
- 実測 66 ms のうち、OS の音声経路は 13 ms、タッチ〜フレーム取り込みが推定 10 ms 前後、残り約 40 ms はゲーム内部（推定）。
- OS 側に残る候補はどれも数 ms 規模:
  - HAL の ULL 周期（3 ms）を縮める。PAL / HAL の設定かコード変更が必要で、音切れのリスクが高い。未調査。
  - 有線 / USB-C 出力。スピーカー経路との差は未測定。
- ゲーム内部の約 40 ms が本当にゲーム側かを確かめるには、同じ経路（OpenSL、FAST|RAW）で即座に音を鳴らす自作ベンチでの実測が要る。この PC には Android SDK が入っていないので、ビルド環境の導入から必要。

## iPad mini (A17 Pro) との比較（2026-11-12 00:32、`prsk/logs/mic/tap_20261112_003217_ray_nobgm_ipadmini.wav`）

同じ PC 内蔵マイク、同じ解析スクリプト。ray、BGM 音量 0、SE オン、本体スピーカー。iPad は MASTER（スマホ側は EXPERT）。iPad のプレイ結果: PERFECT 1075 / GREAT 13 / MISS 4、LATE 7 / FAST 6。

| 端末・条件 | タップ → SE 中央値 | p25〜p75 | p10〜p90 | n |
|---|---|---|---|---|
| RedMagic 元の状態（loudness オン、FAST 不可） | 未実測（報告値から推定 約 180 ms） | — | — | — |
| RedMagic `low_latency_out`（FAST） | 79.2 ms | 72.6〜83.5 | 59.7〜88.9 | 108 |
| RedMagic `raw_out`（FAST\|RAW） | 66.0 ms | 61.0〜70.6 | 50.0〜76.1 | 120 |
| iPad mini | **43.2 ms** | 37.4〜48.5 | 31.8〜53.2 | 76 |

- iPad のほうが 23 ms 短い。ばらつき（四分位幅 11 ms）は同程度。
- 注意: 難易度が違う（iPad は MASTER）。録音の背景ノイズも iPad の回のほうが大きい。検出は相対しきい値なので比較はできるが、数 ms の誤差はあり得る。
- 23 ms の差のうち OS 側に残っているのは `raw_out` の 7 ms 程度。残りは、同じゲームエンジンでも Android 版の音声ミドルウェアが大きめのバッファで動いている分とみられる（未検証）。
- 端末が申告している機能: `android.hardware.audio.low_latency` あり、`android.hardware.audio.pro` なし。アプリ側がこの申告を見てバッファを決めている場合、`audio.pro` を足すと変わる可能性がある（プロセカがそうしているかは不明。試すには再起動が必要）。

## モジュール `rhythm_latency_fix` v0.1 のインストールと `audio.pro` 申告の実験（2026-11-12 00:38）

- `module/` を zip にして `ksud module install` で導入、再起動。`post-fs-data.sh` が 2 ファイルを bind mount（ログ `/data/local/tmp/rhythm_latency_fix.log` で両方 `bind ok`）。
  - `/vendor/etc/audio/sku_canoe/audio_module_config_primary.xml` ← `raw_out` 追加版
  - `/vendor/etc/permissions/android.hardware.audio.low_latency.xml` ← `android.hardware.audio.pro` 追加版
- 再起動後: `raw_out` 登録済み、`pm list features` に `audio.pro` あり、loudness 停止、ゲーム起動中は `tp_report_rate=4` / `play_game=1`。

実測（`prsk/logs/mic/tap_20261112_004114_ray_nobgm_module_raw_pro.wav`、ray EXPERT、BGM なし、爪）:

| 条件 | タップ → SE 中央値 | p25〜p75 | n |
|---|---|---|---|
| `raw_out` のみ（一時適用） | 66.0 ms | 61.0〜70.6 | 120 |
| `raw_out` + `audio.pro` 申告（モジュール） | 65.2 ms | 63.0〜69.0 | 78 |

- **`audio.pro` の申告は SE の遅延を変えなかった**（差 0.8 ms は誤差の範囲）。SE 側トラックは 288 フレームのまま。
- BGM 側トラックは 1536 → 1152 フレーム（報告遅延 39 → 31 ms）になった。1152 = 144 × 8 で、`raw_out` の周期に合わせて起動時に決まったとみられる（一時適用のときは、旧設定で起動済みのプロセスが 192 × 8 のまま作り直していた）。`audio.pro` の影響かどうかは切り分けていない。
- プレイ結果: PERFECT 969 / GREAT 7 / MISS 2、LATE 0 / FAST 7。BGM なしだと FAST に偏る傾向が 2 回続いた。
- 判断: `audio.pro` は実態を伴わない申告で、他のアプリが無理なバッファ設定を選ぶ恐れがある。効果が確認できないので無効化した（`post-fs-data.sh` の `PRO=0`。端末側のモジュールも更新済み、次回の再起動から有効）。
- 配布用 zip: `rhythm_latency_fix_v0.1.zip`（`PRO=0` 版）。

## 外部資料との照合（2026-11-12、ユーザーが別途依頼したリサーチ結果 + CRI マニュアル）

出典:
- プロセカ開発者インタビュー（CRI 公式、2021）: https://game.criware.jp/interview/pjsekai/ — 初期 Android は約 0.16 秒、低遅延モードで約 0.07 秒（実測ではない）、1 周年ごろ SonicSYNC に全面移行。
- CRI ADX Unity プラグインのマニュアル（Android の SonicSYNC 特記事項）: https://game.criware.jp/manual/unity_plugin/latest/contents/cri4u_tgtspc_android_sonicsync_notes.html
- 同（Android 低遅延再生）: https://game.criware.jp/manual/unity_plugin/latest/contents/cri4u_tgtspc_android_atom_law_latency_play.html

CRI 公式の実測表（タップ → 発音、各 20 回の平均、サーバー周波数 60）:

| 端末 | 出力の「サンプルサイズ」 | SonicSYNC | 低遅延再生 | どちらもなし |
|---|---|---|---|---|
| Pixel 3 (Android 11) | 96 | 45.7 ms | 66.4 ms | 90.3 ms |
| Xperia XZ2 (Android 10) | 192 | 52.5 ms | 64.5 ms | 114.9 ms |
| Galaxy S20 5G (Android 10) | 192 | 65.3 ms | 79.0 ms | 128.2 ms |

こちらの実測との対応:
- `low_latency_out`（周期 192 フレーム）79.2 ms、`raw_out`（周期 144 フレーム）65.2〜66.0 ms。公式表の範囲に収まる。
- マニュアルの定義では、この遅延は「タッチ入力の遅延 + 再生リクエストの遅延（サーバー周波数依存）+ 出力バッファの更新遅延 + スピーカーまでの出力遅延」の合計。サーバー周波数 60 なら、再生リクエストだけで最大 16.7 ms（平均 約 8 ms）待つ。これは OS から触れない。
- マニュアルには、SonicSYNC が端末の出力バッファに同期して動くこと、端末ごとにバッファの大きさが違い小さいほど遅延が小さいことが書かれている。使用 API（AAudio / OpenSL ES）や、端末によって SonicSYNC が無効になる条件は書かれていない。
- プロセカがこの端末で SonicSYNC と低遅延再生のどちらで動いているかは、外側からは確定できていない。トラックが 2 本（288 フレームと 1152 フレーム）ある点は低遅延再生の構成に見えるが、断定はできない。

リサーチ結果にあった疑問「FAST より raw out のほうが速いのはなぜか、FAST はどの経路か」への答え:
- 「FAST」は `low_latency_out`（PRIMARY|FAST）。Android の FastMixer を通る通常の低遅延出力で、周期 4 ms、HAL 申告遅延 21 ms。
- 「raw out」は `raw_out`（FAST|RAW）。こちらも FastMixer を通るが、DSP の後処理を通らない別の出力で、周期 3 ms、HAL 申告遅延 7 ms。
- どちらも CRI が推奨する「Fast Mixer」の条件は満たしている。差はアプリ側ではなく、端末の出力経路の差。

出力周期をさらに縮められるか:
- `raw_out` の周期（144 フレーム）は HAL のコード（`libaudiocorehal.qti.so` の `UllPlayback::getFrameCount`）で決まっていて、設定ファイルや prop では見つからなかった。変えるには HAL バイナリの改変が必要。実施しない。

## 純正 ROM との比較（2026-11-12、`archive/stock_extracted/diff_vendor_a.txt` と純正 `super.img`）

以前 GPS 調査で作った vendor のファイル一覧比較（サイズと種別の比較）を再利用した。

- **`sku_canoe/audio_module_config_primary.xml` は純正と同じサイズ（29446 バイト）で、差分一覧に載っていない。純正にも `raw_out` は無い。** 純正イメージ内のファイルも 29446 バイトと確認。
- **`libaudiocorehal.qti.so` も純正と同じサイズ（1648856 バイト）。** HAL は純正のまま。純正の HAL を重ねても周期は変わらない。
- EvoX 側で変わっている音声関連ファイル: `sku_canoe/resourcemanager_canoe_mtp_wsa884x.xml`（100655 → 100433 バイト）、`audio_effects_config.xml`、`audio_policy_volumes.xml`、`acdbdata/.../MTP_canoe_wsa884x_acdb_cal.acdb`、`init/audiohalservice_qti.rc`、追加で `libv4a_aidl.so`。
- `resourcemanager` の差分の中身は未確認（純正イメージ内で圧縮されており、手元の `scripts/erofs_tool.py` では読めない）。
- 比較はサイズ一致によるもので、バイト単位の一致までは確認していない。

作業中のミス: この調査のコマンドに誤って `raw_out` 設定の bind mount を外す操作を混ぜてしまった。音声 HAL は設定を読み込み済みだったので動作への影響は無く、すぐ同じファイルを mount し直した（`raw_out` は登録されたまま）。再起動後はモジュールが通常どおり mount する。

## SonicSYNC が効いているかの調査（2026-11-12）

対象は APK 内の CRIWARE ライブラリ `libcri_ware_unity.so`（CRI Atom Ver.2.27.320、2025-05-22 ビルド）。文字列とシンボル名だけを読んだ（`prsk/logs/cri/strings.txt`）。逆アセンブルや改変はしていない。

ライブラリから分かったこと:
- 「SonicSYNC」という文字列は無い。内部名は **Low-Latency Mode** とみられる。該当メッセージ: 「NSR Playback is not available in Low-Latency Mode. ASR playback is used instead.」「Atom latency estimator is not supported for Low-Latency Mode.」。マニュアルの SonicSYNC の制限事項（低遅延再生ボイスプール不可、遅延推測不可）と一致する。
- 「この端末では Low-Latency Mode を使えない」といった、端末条件で無効化する趣旨のメッセージは見当たらない。有効・無効はアプリ側の設定で決まるとみられる。
- 出力は OpenSL ES（`SL_IID_ANDROIDSIMPLEBUFFERQUEUE` ほか）。AAudio のコードも入っているが、マニュアル上はベータ扱いで既定は無効。実機でも `callerName=opensles`。
- OS から `PROPERTY_OUTPUT_FRAMES_PER_BUFFER` と `PROPERTY_OUTPUT_SAMPLE_RATE` を読んでいる。前者は Android の仕様上プライマリ出力（`low_latency_out`）の値で、この端末では 192。`raw_out` の 144 ではない。

実機の挙動から分かったこと:
- ゲームが作る音声トラックは常に 2 本。起動直後に 1 本目（`raw_out` 環境で 1152 フレーム = 144 × 8）、約 0.7 秒後に 2 本目（288 フレーム = 144 × 2）。
- SonicSYNC が無効で「低遅延再生」を使う構成なら、通常再生用の大きなバッファのトラックに加えて、低遅延ボイス用のプレーヤーが複数本（最大 6）作られるはず。2 本しか無く、うち 1 本が出力周期の 2 倍という最小構成なのは、**SonicSYNC（Low-Latency Mode）が有効**という見方と整合する。
- 1 本目（1152 フレーム）の正体は未確認。CRI より先に初期化される別の音声出力（Unity 標準オーディオなど）の可能性がある。
- ゲーム起動中のスレッド名とログでの裏取りは未実施（調査時点でゲームが起動していなかった）。

結論（確度は中程度）: **SonicSYNC は有効とみられる。** この場合、こちらの 65 ms は CRI 公式表の SonicSYNC 列（Pixel 3 45.7 / Xperia XZ2 52.5 / Galaxy S20 65.3 ms）と比べる値になり、Galaxy S20 相当。

残る未知数: OS とハードウェアだけの下限（タッチ → 最小構成のアプリ → スピーカー）。これが分かれば、65 ms のうちゲーム側の取り分が確定する。Google の OboeTester の Tap-to-Tone を同じマイク録音で測れば求まる。

## OboeTester による OS・ハードウェアの下限（2026-11-12 04:12〜04:25）

OboeTester 2.8.19（Play ストア版）。条件: 本体スピーカー、`raw_out` 導入済み、タッチ 363 Hz、メディア音量 10/15。Tap-to-Tone の音は Blip（1 kHz の正弦波）なので、解析スクリプトに SE の検出帯域を指定するオプション（`--se 800 1300`）を追加した。録音スクリプト `scripts/audio/record_mic.sh`、UI 一覧スクリプト `scripts/audio/ui_dump.py` を追加。

| 経路 | PC マイク: 中央値（p25〜p75、n） | OboeTester 自身（端末マイク） | 録音 |
|---|---|---|---|
| AAudio MMAP 排他（周期 96 フレーム = 2 ms、バッファ 192、報告遅延 8.5 ms） | **52.5 ms**（51.0〜54.8、27） | 平均 54（49〜61、20 回） | `prsk/logs/mic/tap_20261112_041242_oboe_aaudio_mmap_ex.wav` |
| OpenSL ES（`raw_out`、FAST\|RAW、288 フレーム = ゲームの SE トラックと同じ） | **54.2 ms**（53.1〜56.5、26） | 平均 55（53〜61、19 回） | `prsk/logs/mic/tap_20261112_041444_oboe_opensl_rawout.wav` |

- 2 つの計測方法で値が一致した。PC マイクでの計測方法は信頼できる。
- AAudio MMAP と OpenSL（`raw_out`）の差は約 2 ms。**API を変えても縮まらない。**
- **ゲームの取り分**: プロセカ 66 ms − 最小構成のアプリ 54 ms = **約 12 ms**。120 fps のフレーム待ち（平均 4 ms）と CRIWARE のミキシングで説明がつく大きさで、ゲーム側は十分に詰められている。前に推定した「ゲーム内部 約 40 ms」は誤りだった。
- ただし検出の仕方の違い（Blip は 1 kHz 帯の立ち上がり、ゲームの SE は 8 kHz 以上）で数 ms の誤差はあり得る。

### 往復遅延（Round Trip Latency、スピーカー → 端末マイク、AAudio MMAP 排他、5 回平均）
- 入力プリセット VoiceRec: **55.35 ms**（MAD 0.31）。OS の報告値（入力 + 出力）は 9.78 ms。
- 入力プリセット Performance: 55.81 ms（報告値 10.28 ms）。入力側の前処理は関係ない。
- SCAN（出力バッファ 2 → 31 周期）: 往復 2691 → 5390 フレーム（56 → 112 ms）。バッファを増やした分だけ素直に伸びる。
- **OS の報告に出ない遅延が約 45 ms ある。** 往復（入力 + 出力）55 ms と Tap-to-Tone（タッチ + 出力）54 ms がほぼ同じなので、タッチと入力は同程度。MMAP 入力は通常数 ms なので、**隠れた遅延の大半はスピーカー出力側**（ADSP の処理〜アンプ）で、タッチは 10 ms 前後とみられる（未検証。切り分けにはスピーカーを通らない出力での計測が要る）。

### スピーカー経路の構成（読み取りのみ）
- サウンドカード `canoe-mtp-wsa884x-snd-card`。設定は `sku_canoe/resourcemanager_canoe_mtp_wsa884x.xml`。
- スピーカーは `MI2S-LPAIF-RX-PRIMARY`（I2S）経由で Awinic `aw882xx_smartpa` 2 個（I2C 24-0034 / 24-0035）。
- `PAL_DEVICE_OUT_SPEAKER` で `speaker_protection_enabled=1`、`cps_mode=0`、`ras_enabled=0`。
- **スピーカー保護は無効化しない。** 過大入力からスピーカーを守る処理なので、外すとスピーカーを壊すおそれがある。
- iPad mini（43 ms）との差 11 ms は、ほぼこのスピーカー出力経路の差とみられる。

### その他
- OS の申告 `PROPERTY_OUTPUT_FRAMES_PER_BUFFER` は現在 **144**（OboeTester のメイン画面の表示）。前の記録（192）は `raw_out` 導入前の値。
- `audio.pro` の申告はまだ有効（`pm list features` に出る）。前回の記録どおり、次の再起動で消える。

## スピーカー保護を外した往復遅延（2026-11-12 04:22〜04:26、ユーザーの依頼で一時適用）

方法: `docs/audio/experiments/resourcemanager_canoe_mtp_wsa884x_nospkprot.xml`（純正ファイルから `speaker_protection_enabled` を 1 → 0 にした 1 行だけの差分）を `/data/local/tmp/` に置き、init の mount 名前空間で `/vendor/etc/audio/sku_canoe/resourcemanager_canoe_mtp_wsa884x.xml` に bind mount。`vendor.audio-hal-aidl` と `audioserver` を再起動。スピーカーを守るため、メディア音量を 3/15 に下げてから行った。

| 状態（音量 3、AAudio MMAP 排他、5 回平均） | 往復遅延 | OS の報告値 |
|---|---|---|
| 保護あり | 55.98 ms（MAD 0.52） | 10.31 ms |
| **保護なし** | **56.15 ms**（MAD 0.18） | 10.48 ms |
| 元に戻した後 | 55.74 ms（MAD 0.63） | 10.23 ms |

- 保護なしの間は、PAL のログに `SpeakerProtectionwsa884x` が一度も出なかった（保護ありでは再生のたびに出る）。保護は確かに外れていた。
- **遅延は変わらなかった。スピーカー保護は隠れた約 45 ms の原因ではない。**
- 元に戻した: umount、HAL と audioserver を再起動、`/data/local/tmp/rlf_rm_nosp.xml` を削除。`raw_out` は残っており、保護のログも復活した。音量はユーザーが手元で下げたので、そのままにしている（10 に戻す途中の値の乱れもユーザーの操作だったとみられる）。
- 補足: `cmd media_session volume --set` は音量を変えられなかった。音量キー（`input keyevent KEYCODE_VOLUME_DOWN/UP`）で変えた。結果は `dumpsys audio` の `2 (speaker)` で確認する。
- 残る候補（いずれも未確認）: ADSP の再生グラフ内のほかの処理（ACDB で決まる音質処理など）、Awinic アンプ内部の処理、I2S の転送。どれも設定ファイルからは見えない。スピーカーを通らない出力（有線）で測れば、出力側か入力側かは切り分けられる。

## 有線イヤホン（3.5 mm）での Tap-to-Tone（2026-11-12 04:30〜04:45）

条件: 3.5 mm の有線ヘッドセット（マイク付き、`AUDIO_DEVICE_OUT_WIRED_HEADSET`、04:28:52 に接続して以後抜けていない）。OboeTester は AAudio MMAP 排他（`AudioMmapOut` スレッドの出力先が WIRED_HEADSET）。イヤホンを PC マイクの近くに置いて録音。OboeTester 自身の計測は、イヤホンの音が端末のマイクに届かないので使えない（1174 ms などの誤検出）。

1 回目（`tap_20261112_043017_oboe_aaudio_mmap_wired.wav`）は端末とイヤホンがマイクから遠く、Blip がほとんど録れずに使えなかった。2 回目（`tap_20261112_043405_oboe_aaudio_mmap_wired2.wav`）で、端末とイヤホンをマイクの横に置いて取り直した。

解析の作り直し: 前の `analyze_tap_audio.py --se 800 1300` はタップから 15 ms 以降しか探さず、基準水準もタップ後 6〜15 ms から取るので、短い遅延を検出できない。また叩く音自体にも 1 kHz 成分がある。そこで `scripts/audio/analyze_tap_tone.py` を新しく作った。5 ms 窓の 1 kHz 直交検波で、Blip の安定水準の 50% を超え、かつ 600 / 1400 Hz の 3 倍を超えた点を立ち上がりとする。前の Blip と重なったタップと、Blip が小さく録れたタップは除外する。

| 出力（同じ解析 `analyze_tap_tone.py --min 1.5`） | タップ → Blip 中央値 | p25〜p75 | n |
|---|---|---|---|
| スピーカー、AAudio MMAP | 55.2 ms | 53.5〜56.9 | 26 |
| スピーカー、OpenSL（`raw_out`） | 57.5 ms | 56.0〜59.5 | 25 |
| **有線イヤホン、AAudio MMAP** | **20.0 ms** | 18.5〜22.8 | 12 |

（`--min 0.3` でも有線は中央値 21.2 ms、n=28。スピーカーの値は前の解析方法、OboeTester 自身の計測とも 2〜3 ms 以内で合う。）

- **有線イヤホンはスピーカーより約 35 ms 短い。** 隠れた約 45 ms の大半は、スピーカーの出力経路（ADSP のスピーカー用の処理〜WSA884x 経路〜Awinic アンプ）にあると確定した。スピーカー保護を外しても変わらなかったので、原因は保護以外の部分にある。
- タッチ → アプリ → 有線出力の合計が約 20 ms なので、タッチの遅れは 10 ms 台前半以下。
- 有線では、Blip が小さく録れたタップの立ち上がりが遅めに出る（判定が遅れるため）。音量か距離を十分にとって測る。
- プロセカに当てはめた見込み: 66 − 35 ≈ **約 30 ms**（iPad mini のスピーカー 43 ms より短い）。ただしプロセカの音が有線で `raw_out` に乗るかは未確認（モジュールは wired_headset / wired_headphones にも `raw_out` のルートを足している）。

## プロセカを有線イヤホンで実測（2026-11-12 04:40、`prsk/logs/mic/tap_20261112_044040_ray_nobgm_wired.wav`）

ray EXPERT、BGM 0、SE オン、爪で打鍵。3.5 mm 有線イヤホンを PC マイクの横に置いた。開始前の確認: ゲームのトラック 2 本（1152 / 288 フレーム）はどちらも FAST|RAW で、出力先は有線ヘッドセット（`AudioOut_15` = `raw_out`、WIRED_HEADSET）。

| 端末・出力 | タップ → SE 中央値 | p25〜p75 | p10〜p90 | n |
|---|---|---|---|---|
| RedMagic スピーカー（`raw_out`） | 66.0 ms | 61.0〜70.6 | 50.0〜76.1 | 120 |
| **RedMagic 有線イヤホン（`raw_out`）** | **30.8 ms** | 25.6〜33.9 | 20.0〜39.0 | 90 |
| iPad mini スピーカー | 43.2 ms | 37.4〜48.5 | 31.8〜53.2 | 76 |

- 見込み（約 30 ms）どおり、スピーカーより 35 ms 短い。iPad mini より 12 ms 短い。
- 注意: `analyze_tap_audio.py` はタップから 15 ms 以降しか探さないので、15 ms 未満の値は数えていない（最小値 15.0 ms）。中央値への影響は小さいとみられる。
- プレイ結果: **PERFECT 971 / GREAT 7**、フルコンボ、LATE 2 / FAST 5（`prsk/logs/mic/result_ray_nobgm_wired.png`）。同条件（EXPERT、BGM なし）のこれまで: `low_latency_out` 969 / 9、`raw_out` スピーカー 967 / 9。
- ユーザーの感想: 「今までで一番 iPad に近いかも」。

## スピーカー経路の迂回策の調査（2026-11-12 04:50〜05:05）

### 出力の種類ごとの往復遅延（OboeTester Round Trip、AVERAGE、入力は AAudio MMAP 排他で固定）
入力側は同じなので、差はそのまま出力側の差。`scripts/audio/oboe_ui.py` で画面を操作して測った（intent での自動テスト `--es test latency` は「please wait」で止まって使えなかった。`scripts/audio/oboe_rt.sh` は動かないまま残している）。

| 出力の設定 | 経路 | 往復遅延 | OS の報告値 |
|---|---|---|---|
| AAudio MMAP 排他、スピーカー | MMAP | 56.0 ms | 5.8 ms |
| AAudio 非 MMAP（Legacy）、スピーカー | `raw_out`（FAST\|RAW） | 61.1 ms | 11.1 ms |
| 性能モード NONE、スピーカー | 通常（FLAG_NONE、5766 フレーム） | 296.9 ms | 217.0 ms |
| 用途 VoiceComm | 受話口に回される、FAST なし | 164.7 ms | 111.3 ms |
| **AAudio MMAP、出力先を受話口に指定（用途 Media）** | MMAP | **22.8 ms** | 5.3 ms |

- **受話口はスピーカーより 33 ms 短い**（有線イヤホンとの差 35 ms とほぼ同じ）。重い処理はスピーカーの経路にだけ入っている。
- OboeTester で選べる出力先: 自動 / 受話口（2）/ スピーカー（3）/ telephony / FM。
- `cmd audio` には、メディアの出力先を指定するコマンドは無い。

### スピーカーと受話口の違い（`mixer_paths_canoe_mtp_wsa884x.xml`）
- `speaker`: `aw_dev_0_switch` / `aw_dev_1_switch` = Enable、`aw_dev_0_prof` / `aw_dev_1_prof` = **Music**、`aw_dev_0_monitor` / `aw_dev_1_monitor` = Enable。
- `handset`: `aw_dev_0_switch` = Enable、`aw_dev_1_switch` = Disable、`aw_dev_0_prof` = **Receiver**。
- 受話口は、スピーカー用の Awinic アンプ 2 個のうち 1 個（dev_0）を Receiver プロファイルで鳴らしているだけ。伝送路（`MI2S-LPAIF-RX-PRIMARY`）とアンプのチップは共通。
- したがって 33 ms の差は、(a) ADSP の処理グラフ（ACDB でスピーカー用と受話口用に別の処理が組まれる）か、(b) アンプのプロファイル（Music / Receiver、`/vendor/firmware/aw882xx_acf.bin`）のどちらか。
- アンプのドライバ: `aw882xx_smartpa` v2.0.1。sysfs の `algo_state` は「read algo run state failed」、`algo_ver` は空、`dsp_re` は 0。ADSP 側で Awinic の処理アルゴリズムが動いているかは不明。
- 端末に `tinymix` は無い。

### アンプのプロファイルを Receiver にしたスピーカー（2026-11-12 05:00、ユーザーの了承を得て一時適用）
- `docs/audio/experiments/mixer_paths_canoe_mtp_wsa884x_spk_receiver.xml`（`speaker` パスの `aw_dev_0_prof` / `aw_dev_1_prof` を Music → Receiver にした 2 行だけの差分）を bind mount し、HAL と audioserver を再起動。音量 3。
- カーネルログで、測定中は 2 個のアンプとも `set prof[Receiver]` で動いていたことを確認（停止時に初期値の Music に戻すログも出るので、時刻で区別する）。
- **往復遅延 55.5 ms で変わらず**（confidence 0.777、音が小さくなったため）。**33 ms の原因はアンプのプロファイルではなく、ADSP の処理グラフ (a)**。
- 元に戻した（umount、HAL 再起動、一時ファイル削除、`raw_out` が残っていることを確認）。

### ACDB（ADSP の処理グラフと較正データ）
- `/vendor/etc/acdbdata/canoe_mtp_wsa884x/MTP_canoe_wsa884x_acdb_cal.acdb`（3.2 MB）と `MTP_canoe_wsa884x_workspaceFileXml.qwsp`（1.2 MB）。
- `.qwsp`（モジュール名などの対応表）はエントロピー 8.0 で暗号化されていて読めない。`.acdb` は `ACDB` / `HEAD` / `CLIVers_1` で始まるチャンク形式のバイナリで、モジュールは数値 ID のみ。
- 純正 ROM と同じファイル（前の比較で、音声設定と HAL は純正と同一）なので、純正の RedMagic OS でもスピーカーは同じ遅延のはず（未実測）。

### 迂回策の候補（スピーカーでステレオを保つ前提）
1. `.acdb` を解析し、スピーカー用のデバイス後処理（devicepp）のモジュール ID を、AudioReach の公開ヘッダのモジュール ID と照合して特定する（読み取りのみ）。
2. 遅延の原因になっているモジュールが特定できたら、較正データでそのモジュールを無効にした `.acdb` を bind mount で試す（失敗すると音が出なくなる可能性があるが、bind mount を外せば戻る）。リミッターなどを外す場合は大音量で注意が要る。
3. 受話口（handset）デバイスを 2 チャンネル・アンプ 2 個にして、メディアをそこへ回す。ルーティングの変更（`setPreferredDevicesForStrategy` 相当）と、受話口用グラフの 2 チャンネル化が必要で、難しい。
- ユーザーの判断: 受話口だけのモノラル再生は音ゲーとしてはあり得ない。ステレオが前提。

## 考察: スピーカー経路の遅延について（2026-11-12）

- 小さなスピーカーは、そのまま鳴らすと音が小さく割れやすいので、DSP で音質補正・音圧調整・制限をかけ、アンプ側でも処理する。こうした処理はまとまった量の音をためて行うので、遅延が増える。今回の 35 ms はこの種の処理によるものとみられる（どの処理かは未特定）。
- Qualcomm 系の Android 端末では、スピーカー経路に 30〜50 ms あることは珍しくない。iPad はスピーカーでも短く、この部分の作り込みに差がある。
- ゲーミング端末としては、スピーカー経路に低遅延モード（処理を軽くした経路）が無いこと、Extra loudness が低遅延経路を無効にすること、`raw_out` が設定に無いことが作り込み不足と言える。一方、3.5 mm ジャックを残している点は音ゲー向けには有利（有線 31 ms は iPad のスピーカーより速い）。

## 作業ログ

### 2026-11-11
- plan.md を読み、実機の現状を adb で確認（読み取りのみ、変更なし）。
- 矛盾・不明点を整理し、段階計画を作成。
- 方針 1 の了承を受けて P0 を実施。APK 5 本と内部データを退避、スナップショット取得。
- APK の静的調査で Unity 2022.3.62f2 / CRIWARE + AAudio を確認。
- Sekai-World の 29 リポジトリを確認。クライアントのロジックは無く、データ・ビューア・譜面ツールのみ。
- ベースライン 1 回目を取得（1 回目の記録は判定強化が入っていたため破棄）。音声が FAST 経路に乗っていないこと、タッチ報告が約 180 Hz であること、ドライバのゲームモードが切れていることを確認。
- 計測スクリプト `scripts/audio/capture_baseline.sh`、分析スクリプト `scripts/audio/analyze_getevent.py` を追加。
- タッチ報告レートの切り替えテストを実施。値 2 で 300 Hz を実測。値 4（720 Hz）は未確定。
- 値 4（720 Hz 表示）を再測定。実測 363 Hz、間隔 2.75 ms、タッチは正常。
- `tp_report_rate=4` で ray をプレイ。GREAT 26→17、フルコンボ。ライブ中 120 fps を確認。
- media.metrics から、ゲームの FAST|RAW 要求が OS に外されていることを確認。
- `loudness` 停止でゲームのトラックが FAST になることを確認（遅延 29〜53 ms）。
- 両対策でのプレイ: GREAT 8、LATE 2 / FAST 6。
- rmcontrol / GameSpace / gameperfd を調査。タッチレートと loudness はどちらも ROM の設定で切り替えられると判明。
- rmcontrol の設定で両対策が有効になることを確認。ゲームモード併用でも実測 363 Hz。
- さらなる低遅延化の候補を調査。sku_canoe の HAL 設定に `raw_out` が欠けていることを確認し、追加版を `module/` に用意（未適用）。
- PC 内蔵マイクでタップ → SE を実測。中央値 88.5 ms（n=9、参考値）。解析スクリプト `scripts/audio/analyze_tap_audio.py` を追加。
- BGM なしの ray EXPERT でマイク実測。タップ → SE の基準値は中央値 79.2 ms（n=108）。
- `raw_out` を一時適用。マイク実測でタップ → SE 79.2 → 66.0 ms。
- `af.fast_track_multiplier=1` を試したが、アプリ側バッファは変わらず効果なし。
- iPad mini を同条件でマイク実測。タップ → SE 中央値 43.2 ms（n=76）。RedMagic との差は 23 ms。
- モジュール `rhythm_latency_fix` v0.1 をインストール。`audio.pro` 申告は効果なしで無効化。
- 外部リサーチと CRI マニュアルを照合。実測値は公式表の範囲内。`raw_out` の周期は HAL のコード内で決まっており、設定では変えられない。
- 純正 ROM の音声設定と HAL を比較。どちらも現行と同じで、純正にも `raw_out` は無い。
- CRIWARE ライブラリの文字列と実機のトラック構成から、SonicSYNC は有効とみられると判断（確度は中程度）。
- OboeTester で OS・ハードウェアの下限を実測。Tap-to-Tone 52〜54 ms、ゲームの取り分は約 12 ms。往復遅延 55 ms のうち約 45 ms は OS の報告に出ず、スピーカー出力側にあるとみられる。
- ユーザーの依頼で、音量 3 にしてスピーカー保護を一時的に外し往復遅延を測定。56.0 → 56.2 ms で変化なし。元に戻した。
- 3.5 mm の有線イヤホンで Tap-to-Tone を測定。有線 20 ms / スピーカー 55 ms で、スピーカーの出力経路が約 35 ms を占めると判明。解析スクリプト `scripts/audio/analyze_tap_tone.py` を追加。
- プロセカ（ray EXPERT、BGM なし）を有線イヤホンで実測。タップ → SE 中央値 30.8 ms（スピーカー 66.0 ms）。PERFECT 971 / GREAT 7、LATE 2 / FAST 5。
- スピーカー経路の迂回策を調査。受話口に出すと往復遅延 22.8 ms（スピーカー 56 ms）。差はアンプのプロファイル（Music / Receiver）か ADSP の処理グラフ。
- アンプを Receiver プロファイルにしても遅延は変わらず、原因は ADSP の処理グラフと確定。ACDB の対応表は暗号化されている。
- スピーカーをステレオのまま速くする 3 案を「今後チャレンジする項目」として保留。ここまでをコミット。
- 文書・スクリプト・実験用の設定ファイルを rmGPSfix に移し、音声の修正をモジュール `gps_incamera_audio_fix` v3.0 に統合。`prsk/` には非公開の計測データと APK だけを残す。
