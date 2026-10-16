# RedMagic 11 Pro (NX809J) EvolutionX GPS Fix

RedMagic 11 Pro (`NX809J` / Snapdragon 8 Elite Gen 2 `SM8850` `canoe`) のカスタムROM（EvolutionX 等）において、GPS / GNSS 測位が機能しない問題を修正する KernelSU / Magisk モジュールおよび解析スクリプト一式です。

---

## 原因の概要

Stock ROM（RedMagic OS B20）とカスタムROM（EvolutionX）のパーティション差分および実機ログ（`logcat`, `dumpsys location`, `dmesg`）の解析により、以下の2点が原因で GPS 測位不全が発生していることを特定しました。

### 1. `xtra-daemon` の二重起動と SELinux 拒否による XTRA / NTP 通信ロックアウト
- `/vendor/etc/init/xtra-daemon.rc` によって、`init` から正規の SELinux ドメイン（`u:r:vendor_location_xtra_daemon:s0`）で `xtra-daemon` が起動しています。
- しかしカスタムROMの `/vendor/etc/izat.conf` では、`PROCESS_NAME=lowi-server` のみが `PROCESS_STATE=DISABLED` に変更され、`PROCESS_NAME=xtra-daemon` が `PROCESS_STATE=ENABLED` のまま残されていました。
- さらに `/vendor/etc/selinux/vendor_sepolicy.cil` にて `(allow vendor_location vendor_location_xtra_daemon_exec (file (execute_no_trans)))` が追加されていたため、`loc_launcher`（`u:r:vendor_location:s0`）が **非正規ドメイン `u:r:vendor_location:s0` のまま2つ目の `xtra-daemon` を二重起動** していました。
- 後から起動した非正規ドメインの `xtra-daemon` が AIDL サービス（`ILocAidlXtraService`）およびソケット（`/dev/socket/location/xtra/socket_xtra`）を上書きして乗っ取りますが、`netd` (`fwmarkd`) 側に `vendor_location` の `tcp_socket` に対する `{ read write getopt setopt }` 権限が存在しないため、`avc: denied`（`permissive=0`）で通信が100%拒否され、`android_setsocknetwork failure: Message too long` が発生します。
- その結果、`/data/vendor/location/xtra/xtra.sqlite` のリトライ回数カウンタ（`xtra_request_retry_num`）が上限（6回）に到達し、XTRA 予測軌道データのダウンロードが完全にロックアウトされていました。

### 2. Google 位置情報の精度（Network Location Provider）の無効化
- 初期状態で GMS のネットワーク位置情報プロバイダ（`network provider`）が無効になっている場合、GNSS HAL が要求する初期位置（Coarse Location）のアシスト注入が行われず、コールドスタート時の衛星捕捉が大幅に遅延・失敗します。

---

## 修正内容（`rm11pro_gps_fix_v1.0.zip`）

本リポジトリのモジュール（`module/` および `rm11pro_gps_fix_v1.0.zip`）は以下の処理をシステムレスで適用します：

1. **`/vendor/etc/izat.conf` の修正と bind mount (`post-fs-data.sh`, `service.sh`)**:
   - `PROCESS_NAME=xtra-daemon` の `PROCESS_STATE` を `DISABLED` に変更した `izat.conf` を起動時（`post-fs-data` ステージ）に `/vendor/etc/izat.conf` へ bind mount します。
   - これにより `loc_launcher` による二重起動を防ぎ、`init` から起動される正規ドメイン（`u:r:vendor_location_xtra_daemon:s0`）の `xtra-daemon` 単独で正常に XTRA / NTP 通信が行われるようになります。
2. **`xtra.sqlite` リトライ上限ロックの初回自動リセット (`post-fs-data.sh`)**:
   - モジュール初回導入時の起動にて、すでにリトライ上限に達している `/data/vendor/location/xtra/xtra.sqlite` を `.bak` に退避・再生成させ、ロックアウト状態を自動解除します。
3. **SELinux ポリシールールの補完 (`sepolicy.rule`)**:
   - `allow netd vendor_location { tcp_socket udp_socket } { read write getopt setopt }` を追加し、`vendor_location` ドメインからのソケット通信が発生した場合でも `netd` で拒否されないように保護します。

---

## 導入手順

1. **モジュールのインストール**
   - KernelSU（または Magisk / APatch）マネージャーから [`rm11pro_gps_fix_v1.0.zip`](./rm11pro_gps_fix_v1.0.zip) をインストールし、端末を再起動します。
2. **「Google 位置情報の精度」の有効化**
   - 端末の **「設定」 ＞ 「位置情報」 ＞ 「位置情報サービス」 ＞ 「Google 位置情報の精度」** を開いて **ON（有効）** にします。
3. **動作確認**
   - 窓際または屋外にて GPSTest 等のアプリを開き、衛星リスト・信号強度（CN0）および位置固定（Fix）が行われることを確認してください。

---

## ディレクトリ構成

- `module/`: KernelSU モジュールのソースファイル一式
  - `module.prop`: モジュールメタデータ
  - `izat.conf`: `xtra-daemon` の二重起動を無効化した設定ファイル
  - `post-fs-data.sh` / `service.sh` / `uninstall.sh`: マウント・初期化スクリプト
  - `sepolicy.rule`: 追加 SELinux ルール
- `scripts/`: ROMイメージ（EROFS / Sparse LP `super.img`）解析およびモジュールビルド用 Python スクリプト群
  - `build_ksu_module.py`: `module/` から配布用 ZIP（`rm11pro_gps_fix_v1.0.zip`）を生成するスクリプト
  - `erofs_tool.py`: EROFS イメージ・LP メタデータ解析ツール
  - `diff_super.py` / `compare_details.py`: Stock ROM とカスタムROMの全パーティション差分抽出スクリプト
  - `inspect_super.py` / `inspect_evox_super.py`: Raw / Sparse `super.img` のパーティション構造確認スクリプト
- `sagyou.md`: 調査・検証・実装のマイルストーン作業記録
