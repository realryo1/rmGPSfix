# RedMagic 11 Pro (NX809J) EvolutionX 修正

[English (README_en.md)](./README_en.md)

EvolutionX（2026-10-10）で、GPS が測位しない問題と、インカメラ写真の緑被りを直す KernelSU モジュールです。配布は [`gps_incamera_fix_v2.0.zip`](./gps_incamera_fix_v2.0.zip) の1つです。

| 項目 | 内容 |
|---|---|
| 端末 | RedMagic 11 Pro（`NX809J`） |
| ROM | EvolutionX A17 / 2026-10-10 / MinimalGApps |
| root | KernelSU（確認済み）。Magisk / APatch は未確認 |

## 入れ方

1. 以前の `rm11pro_gps_fix` と、試験用の `rm11pro_frontcam_wb` が入っていれば外す。id が `gps_incamera_fix` に変わるので、自動では置き換わりません。
2. KernelSU で [`gps_incamera_fix_v2.0.zip`](./gps_incamera_fix_v2.0.zip) を入れ、再起動する。
3. **設定 → 位置情報 → 位置情報サービス → Google 位置情報の精度** を ON にする。
4. 屋外で測位を確認する。インカメラの写真は、白いものが緑に潰れず、青が残る。

`scripts/build_ksu_module.py` が `module/` からこの ZIP を作ります。

## GPS

カスタム ROM の `/vendor/etc/izat.conf` は `xtra-daemon` が `ENABLED` のままです。`loc_launcher` が、init の正規起動に加えて SELinux ドメイン `vendor_location` でもう1つ起動します。後から起動した方がソケットを取りますが、`netd` がそのドメインを拒否するため XTRA のダウンロードが失敗し、`/data/vendor/location/xtra/xtra.sqlite` のリトライが上限 6 で止まります。Google 位置情報の精度がオフだと、初期位置の補助も入りません。

モジュールは、`xtra-daemon` を `DISABLED` にした `izat.conf` を bind mount して二重起動を止め、初回だけ上限に達した `xtra.sqlite` を退避して作り直し、`netd` が `vendor_location` のソケットを扱えるルールを足します。

## インカメラの緑被り

写真だけが緑です。動画とプレビューは正常です。アプリが 4608×3456 を要求すると、インカメラは Quad CFA の非 ZSL に入り、その経路では現像段（OFE）がホワイトバランスを掛けません。AWB は青を約 3 倍する値なので、掛からないと青が潰れます。アウトカメラの写真は別経路で、OFE がホワイトバランスを掛けています。写真用 IPE の WB は設計上オフで、ここを無理に有効にすると真っ黒になります。

修正は `com.qti.feature2.gs.sm8850.so` の `GetNZSLSnapshotFlag` で、戻り値の下位 32bit を 0 にします。ファイルオフセット 0xd4e26 の `17` を `1f` に変えるだけです。非 ZSL に入らず、ホワイトバランスの掛かる 2304×1728 で撮ってから 4608×3456 に拡大します。表示上の画素数は 16MP のまま、中身は 4MP からの拡大です。起動のたびに端末上の so を複製してその 1 バイトだけ変え、bind mount します。サイズ 1545632 かつ命令 `eb 03 17 2a` の 2026-10-10 ビルドだけに当て、違うビルドは素通りします。

確認時、ぬいぐるみの青い目は RGB 約 [36, 78, 120]、白い生地は約 [182, 183, 174] でした。壊れていた白い対象は約 [90, 115, 20] です。

## モジュールでは直していないこと

- 左下サムネイルは Google フォトではなく Glimpse（`org.lineageos.glimpse`）を直接開きます。画像の既定アプリを変えても切り替わりません。
- 「撮影中、デバイスをしっかり握ってください」が出ている間は、画面下インカメの処理中で JPEG がまだありません。消えてから左下を開くと写真が見えます。アウトカメラはこの表示が出ないので、すぐ開いても真っ黒になりません。

計測と、試して捨てた仮説は [`sagyou.md`](./sagyou.md) と [`frontcam_handoff.md`](./frontcam_handoff.md) にあります。

## 中身

- `module/` … モジュール本体
- `scripts/` … `super.img` の差分とカメラ計測。ROM イメージはリポジトリに含まれない

## ライセンス

スクリプトと文書は [MIT License](./LICENSE) です。`module/izat.conf` は EvolutionX / Qualcomm 由来の設定を改変したものです。
