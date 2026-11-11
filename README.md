# RedMagic 11 Pro (NX809J) EvolutionX 修正

[English (README_en.md)](./README_en.md)

EvolutionX（2026-10-10）で、GPS が測位しない問題、インカメラ写真の緑被り、音ゲーの音の遅れ（低遅延出力の欠落）を直す KernelSU モジュールです。配布は [`gps_incamera_audio_fix_v3.0.zip`](./gps_incamera_audio_fix_v3.0.zip) の1つです。

| 項目 | 内容 |
|---|---|
| 端末 | RedMagic 11 Pro（`NX809J`） |
| ROM | EvolutionX A17 / 2026-10-10 / MinimalGApps |
| root | KernelSU（確認済み）。Magisk / APatch は未確認 |

## 入れ方

1. 以前の `gps_incamera_fix`（v2.0）、`rhythm_latency_fix`、`rm11pro_gps_fix`、試験用の `rm11pro_frontcam_wb` が入っていれば外す。id が `gps_incamera_audio_fix` に変わるので、自動では置き換わりません。
2. KernelSU で [`gps_incamera_audio_fix_v3.0.zip`](./gps_incamera_audio_fix_v3.0.zip) を入れ、再起動する。
3. **設定 → 位置情報 → 位置情報サービス → Google 位置情報の精度** を ON にする。
4. 屋外で測位を確認する。インカメラの写真は、白いものが緑がからないことを確認する。
5. 音ゲーを遊ぶなら、rmcontrol（RedMagic の設定アプリ）で **Extra loudness をオフ**、**Touch sampling while gaming を 720 Hz** にする（下の「音声」を参照）。

`scripts/build_ksu_module.py` が `module/` からこの ZIP を作ります。

## GPS

カスタム ROM の `/vendor/etc/izat.conf` は `xtra-daemon` が `ENABLED` のままです。`loc_launcher` が、init の正規起動に加えて SELinux ドメイン `vendor_location` でもう1つ起動します。後から起動した方がソケットを取りますが、`netd` がそのドメインを拒否するため XTRA のダウンロードが失敗し、`/data/vendor/location/xtra/xtra.sqlite` のリトライが上限 6 で止まります。Google 位置情報の精度がオフだと、初期位置の補助も入りません。

モジュールは、`xtra-daemon` を `DISABLED` にした `izat.conf` を bind mount して二重起動を止め、初回だけ上限に達した `xtra.sqlite` を退避して作り直し、`netd` が `vendor_location` のソケットを扱えるルールを足します。

## インカメラの緑被り

写真だけが緑です。動画とプレビューは正常です。アプリが 4608×3456 を要求すると、インカメラは Quad CFA の非 ZSL に入り、その経路では現像段（OFE）がホワイトバランスを掛けません。AWB は青を約 3 倍する値なので、掛からないと青が潰れます。アウトカメラの写真は別経路で、OFE がホワイトバランスを掛けています。写真用 IPE の WB は設計上オフで、ここを無理に有効にすると真っ黒になります。

修正は `com.qti.feature2.gs.sm8850.so` の `GetNZSLSnapshotFlag` で、戻り値の下位 32bit を 0 にします。ファイルオフセット 0xd4e26 の `17` を `1f` に変えるだけです。非 ZSL に入らず、ホワイトバランスの掛かる 2304×1728 で撮ってから 4608×3456 に拡大します。表示上の画素数は 16MP のまま、中身は 4MP からの拡大です。起動のたびに端末上の so を複製してその 1 バイトだけ変え、bind mount します。サイズ 1545632 かつ命令 `eb 03 17 2a` の 2026-10-10 ビルドだけに当て、違うビルドは素通りします。

確認時、ぬいぐるみの青い目は RGB 約 [36, 78, 120]、白い生地は約 [182, 183, 174] でした。壊れていた白い対象は約 [90, 115, 20] です。

細かい模様は、Quad CFA のフル読み出しより柔らかくなります。このセンサーは Quad Bayer なので、光学的な解像度はもともと 4MP 相当です。フル読み出しとの差はストック ROM と比較していないため、未計測です。

パッチ箇所はインカメラ専用ではなく、全カメラ共通のグラフ選択です。通常のアウトカメラ写真はこの非 ZSL を通らないので、そのままです。アウトカメラの高解像度モードが同じフラグを使う場合は、そちらも 4MP 側に落ちます。パッチ後の高解像度モードは未確認です。

## 音声（音ゲーの遅延）

この ROM の音声 HAL 設定 `/vendor/etc/audio/sku_canoe/audio_module_config_primary.xml` には、超低遅延の出力 `raw_out`（FAST|RAW）がありません。アプリが FAST|RAW を要求しても、1 段遅い `low_latency_out` に乗ります。純正 ROM の設定にもありません。モジュールは `raw_out` を足した設定を bind mount します。スピーカー、有線ヘッドセット、USB オーディオのルートに足しています。

プロジェクトセカイ（ray）で、画面を叩いてから SE が鳴るまでを PC のマイクで測りました。

| 状態 | タップ → SE（中央値） |
|---|---|
| ROM の初期状態（Extra loudness オン） | 約 180 ms（OS の報告値からの推定） |
| Extra loudness オフ | 79 ms |
| さらに `raw_out` を追加（このモジュール） | 66 ms |
| 同上、3.5 mm 有線イヤホン | 31 ms |
| 参考: iPad mini（A17 Pro）のスピーカー | 43 ms |

設定で直すもの（モジュールでは変えていません）:
- **Extra loudness**（rmcontrol）: オンだと、スピーカー出力にかさ上げ処理が入り、全アプリの低遅延出力が無効になります。オフにしてください。
- **Touch sampling while gaming**（rmcontrol）: 720 Hz にすると、タッチの報告が約 180 Hz から 363 Hz（実測）になります。

本体スピーカーには、OS の報告に出ない約 35 ms の遅れが残ります。音声 DSP がスピーカー用にだけ組む処理で、アンプのプロファイルやスピーカー保護は関係ありませんでした。受話口や有線イヤホンの経路にはありません。音ゲーは 3.5 mm の有線イヤホンで遊ぶのが一番速いです。

計測の手順と結果は [`docs/audio/progress.md`](./docs/audio/progress.md) にあります。

## モジュールでは直していないこと

- 左下サムネイルは Google フォトではなく Glimpse（`org.lineageos.glimpse`）を直接開きます。画像の既定アプリを変えても切り替わりません。
- 「撮影中、デバイスをしっかり握ってください」が出ている間は、画面下インカメの処理中で JPEG がまだありません。消えてから左下を開くと写真が見えます。アウトカメラはこの表示が出ないので、すぐ開いても真っ黒になりません。

計測と、試して捨てた仮説は [`docs/sagyou.md`](./docs/sagyou.md) と [`docs/frontcam_handoff.md`](./docs/frontcam_handoff.md) にあります。

## 中身

- `module/` … モジュール本体
- `scripts/` … `super.img` の差分とカメラ計測。ROM イメージはリポジトリに含まれない
- `scripts/audio/` … 音声とタッチの遅延の計測スクリプト。録音などの計測データは含まれない
- `docs/` … 作業記録。GPS とカメラは `sagyou.md` と `frontcam_handoff.md`、音声は `audio/`

## ライセンス

スクリプトと文書は [MIT License](./LICENSE) です。`module/izat.conf`、`module/audio_module_config_primary.xml`、`docs/audio/experiments/` の設定ファイルは、EvolutionX / Qualcomm 由来の設定を改変したものです。
