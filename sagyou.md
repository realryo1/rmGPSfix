# Redmagic11Pro カスタムロムでGPSが効かない問題を修正ログ

# 概要
`./EvolutionX-NX809J-A17-20261010-MinimalGApps` 環境でのGPSが効かない問題を修正する。

`./1_stock20images` はRedmagic11ProのStockimage。差分検証に使用。

# ルール
・日本語で返答
・このマークダウン（sagyou.md）にマイルストーンを適宜追記
・imageの展開ファイル・ログなどの一時ファイルもすべてこのディレクトリ内に保持する

#　作業ログ

## マイルストーン1: 実機状態の初期調査・ログ取得 (2026-10-16 11:28〜11:49)
- **取得・保存したファイル**:
  - `dumpsys_location.txt`: `dumpsys location` の出力
  - `logcat_all.txt` / `logcat_gnss.txt` / `logcat_restart.txt` / `logcat_gpstest.txt` / `logcat_gpstest2.txt`: GNSS関連ログ
  - `dmesg_avc.txt`: カーネルのSELinux拒否（`avc: denied`）ログ
  - `device_etc/`: 実機の `/vendor/etc/gps.conf`, `izat.conf`, `lowi.conf`, `sap.conf`, `gpsInterval.xml`, `/system/etc/gps_debug.conf`, `/vendor/etc/init/*.rc`, `/vendor/build.prop`, `/vendor/etc/selinux/vendor_sepolicy.cil`, `vendor_file_contexts`, `/odm/etc/init/*.rc`, `/data/vendor/location/xtra/xtra.sqlite`, `nvparam.sqlite` 等を保存

- **実機のGNSS状態（`dumpsys_location.txt` および `logcat` より判明した事象）**:
  1. **GNSS HALとモデム間のQMI接続自体は確立されている**:
     - `GNSS Hardware Model Name: qcom;MPSS.DE.9.0-01805.10-KAANAPALI_GEN_PACK-2.124266.59;` が認識されており、`android.hardware.gnss-aidl-service-qti` が稼働中。
     - ただし `Number of location reports: 0`, `Number of TTFF reports: 0`, `Number of CN0 reports: 0` であり、NMEA出力も空（`$GPGGA,,,,,,0,,,,,,,,*66`）で測位に至っていない。
  2. **`xtra-daemon` の二重起動とSELinux拒否によるXTRA/NTP通信不全**:
     - `/vendor/etc/init/xtra-daemon.rc` により `init` から正規ドメイン `u:r:vendor_location_xtra_daemon:s0` で `xtra-daemon` が起動している。
     - 一方、`/vendor/etc/izat.conf` にて `PROCESS_NAME=lowi-server` は `PROCESS_STATE=DISABLED` に変更されているものの、`PROCESS_NAME=xtra-daemon` が `PROCESS_STATE=ENABLED` のまま残っており、かつ `/vendor/etc/selinux/vendor_sepolicy.cil` で `(allow vendor_location vendor_location_xtra_daemon_exec (file (execute_no_trans)))` が追加されているため、`loc_launcher` (`u:r:vendor_location:s0`) が **2つ目の `xtra-daemon` を `u:r:vendor_location:s0` ドメインで二重起動** している。
     - 後から起動した `u:r:vendor_location:s0` の `xtra-daemon` が `ILocAidlXtraService` と `/dev/socket/location/xtra/socket_xtra` を上書きして乗っ取るが、`netd` 側で `scontext=u:r:netd:s0 tcontext=u:r:vendor_location:s0 tclass=tcp_socket permissive=0` の `{ read write }` SELinux拒否が発生し、`android_setsocknetwork failure: Message too long` で通信に失敗。
     - その結果、`/data/vendor/location/xtra/xtra.sqlite` にて `xtra_request_retry_num = 6`（リトライ上限到達）となり、`check Xtra req retry limit for https://path1.xtracloud.net/xtra3Mint.bin. Retry dropped.` でXTRAデータのダウンロードが停止している。
  3. **Network Location Provider (NLP) が無効状態**:
     - `dumpsys_location.txt` にて `network provider` (`com.google.android.gms`) が `enabled=false, allowed=false`、`Location Controller Extra Package: com.google.android.gms [disabled]` となっており、GNSS HALからの `GNSS HAL Requesting location updates from network provider` に対してアシスト位置情報（Coarse Location）が注入されていない。
  4. **Izatプロバイダ / QTI Locationスタックのエラー**:
     - `dlopen failed: library "libizatprovider.so" not found` / `IzatProvider load failed`
     - `IzatSvc_WWanLocationProvider: Exiting with error handleMsg line 124 "4"` / `IzatSvc_WiFiLocationProvider: Exiting with error handleMsg line 129 "4"`

## マイルストーン2: Stockイメージ (`1_stock20images`) と EvolutionX (`super.img`) の差分検証 (2026-10-16 11:50〜12:00)
- **作成した解析スクリプト・展開データ**:
  - `inspect_super.py`, `inspect_evox_super.py`, `erofs_tool.py`, `diff_super.py`, `compare_details.py`
  - `stock_extracted/`: Stock `super.img` 内の全パーティション（`vendor_a`, `odm_a`, `vendor_dlkm_a`, `system_dlkm_a`, `system_ext_a`, `product_a`, `system_a`）のファイル一覧、GPS関連ファイル一覧、およびEvolutionX `super.img` との全ファイル差分リスト（`diff_*.txt`）を保存。
- **判明した差分**:
  1. **`vendor_a` の差分 (`diff_vendor_a.txt`)**:
     - Stock（B20ベース）とEvolutionX（B18ベース）でGNSS関連バイナリ・ライブラリ（`android.hardware.gnss-aidl-service-qti`, `libgnss.so`, `libizat_core.so`, `liblocationservice.so`, `gps.conf`, `sap.conf` 等）は同一サイズ。`/bin/lowi-server` のみサイズ差あり。
     - `/etc/izat.conf`: Stockでは `lowi-server` が `PROCESS_STATE=ENABLED` だが、EvoXでは `PROCESS_STATE=DISABLED` に変更されている（`xtra-daemon` は `ENABLED` のまま）。
     - `/etc/selinux/vendor_sepolicy.cil`: EvoX側で `vendor_location` に対する `execute_no_trans` や `(typepermissive vendor_location)` 等が追記されている。
  2. **`system_ext_a` の差分 (`diff_system_ext_a.txt`)**:
     - Stockの `/system_ext` に存在する Qualcomm Location スタック一式が EvolutionX では削除されている：
       - `/priv-app/com.qualcomm.location/com.qualcomm.location.apk`
       - `/framework/com.qti.location.sdk.jar`
       - `/framework/vendor.qti.hardware.data.qmi-V1.0-java.jar`
       - `/framework/vendor.qti.hardware.data.qmiaidlservice-V1-java.jar`
       - `/lib64/libqmi_cci_system.so`, `libqmi_encdec_system.so`, `vendor.qti.hardware.data.qmi@1.0.so`, `vendor.qti.hardware.data.qmiaidlservice-V1-ndk.so`
       - `/etc/permissions/com.qti.location.sdk.xml`, `com.qualcomm.location.xml`, `com.qualcomm.qti.izattools.xml`, `privapp-permissions-com.qualcomm.location.xml`

## マイルストーン3: ネットワーク位置情報有効化と `xtra-daemon` 二重起動修正（ステップ1・2）の検証 (2026-10-16 12:04〜12:15)
- **「Google 位置情報の精度」（Network Location Provider）の有効化確認 (`dumpsys_location_after_nlp.txt`)**:
  - ユーザーによる「Google 位置情報の精度」有効化により、`network provider` および `fused provider` が `enabled=true, allowed=true, connected=true` となり、GNSS HAL（`GnssService`）へ初期位置（Coarse Location）が正常に配信されることを確認。
  - これにより GPSTest 上で衛星リスト（アルマナック・可視衛星計算結果）とマップ上の位置が表示されるようになった。
- **`xtra-daemon` 二重起動防止と `xtra.sqlite` リトライ上限リセットの適用・検証 (`prepare_step1.py`, `apply_step1.sh`, `logcat_step1_v3.txt`, `dumpsys_location_step1_v2.txt`)**:
  - `device_etc/izat_fixed.conf`（`PROCESS_NAME=xtra-daemon` の `PROCESS_STATE` を `DISABLED` に変更）を作成し、実機の `/vendor/etc/izat.conf` へ一時的に bind mount を実施。
  - `/data/vendor/location/xtra/xtra.sqlite` を备份（`.bak`）した上でリトライ回数カウンタを `0` にリセットし、`xtra-daemon` / `loc_launcher` / `gnss_service` を再起動。
  - **結果**:
    1. `ps -efZ` にて、`loc_launcher` による非正規ドメイン（`u:r:vendor_location:s0`）の2つ目の `xtra-daemon` が起動しなくなり、`init` からの正規ドメイン（`u:r:vendor_location_xtra_daemon:s0`）の `xtra-daemon` 1プロセスのみが単独稼働することを確認。
    2. `netd` における `tcp_socket { read write }` の SELinux 拒否（`android_setsocknetwork failure`）が完全に消滅。
    3. 再起動直後に `https://path1.xtracloud.net/xtra3Mgrbej.bin` および `https://path1.xtracloud.net/xtra3Mint.bin` のダウンロードが1回目で成功（`xtra_last_download_status = 0`, `xtra_int_last_download_status = 0`）し、モデムへの軌道データ注入（`LocSvc_xtra2: onInjectXtraData:153] injectXtraData`）が完了したことを確認。
    4. XTRA注入後、`dumpsys location` の `Total number of sv status messages processed` が急増（4,762 → 25,376）し、可視衛星ステータス通知が高速に処理されていることを確認。

## マイルストーン4: KernelSUモジュール（`rm11pro_gps_fix`）の作成・恒久適用 (2026-10-16 12:17〜12:18)
- **作成ファイル (`build_ksu_module.py`)**:
  - `ksu_module_rm11pro_gps_fix/` およびバックアップ用ZIPパッケージ `rm11pro_gps_fix_v1.0.zip` を作成。
  - 内容:
    - `izat.conf`: `PROCESS_NAME=xtra-daemon` を `PROCESS_STATE=DISABLED` に修正し、`loc_launcher` による `xtra-daemon` の二重起動を防止。
    - `post-fs-data.sh` / `service.sh`: 起動時の `post-fs-data` ステージ（`loc_launcher` 起動前）にて `/vendor/etc/izat.conf` へ修正版 `izat.conf` を bind mount。
    - `sepolicy.rule`: 万一 `vendor_location` ドメインからネットワーク通信が行われた場合にも `netd` (`fwmarkd`) で拒否されないよう、`allow netd vendor_location { tcp_socket udp_socket } { read write getopt setopt }` を追加。
- **実機への反映とクリーンアップ**:
  - 実機の `/data/adb/modules/rm11pro_gps_fix` に配置し、`ksud sepolicy apply` と `post-fs-data.sh` の即時適用を確認。
  - 作業に使用した実機 `/data/local/tmp/` 上の一時ファイルをすべて削除してクリーンアップ完了。

## マイルストーン5: ディレクトリ整理とGitHubパブリック公開用ローカルコミット作成 (2026-10-16 13:54〜13:58)
- **ディレクトリの整理**:
  - `module/`: KernelSUモジュールのソース一式（`module.prop`, `izat.conf`, `post-fs-data.sh`, `service.sh`, `uninstall.sh`, `sepolicy.rule`）を配置し、初回導入時に `/data/vendor/location/xtra/xtra.sqlite` のリトライ上限ロックを自動解除する処理を `post-fs-data.sh` に追加した上で `rm11pro_gps_fix_v1.0.zip` を再生成。
  - `scripts/`: 解析・ビルド用Pythonスクリプト群（`build_ksu_module.py`, `erofs_tool.py`, `diff_super.py`, `compare_details.py`, `inspect_super.py`, `inspect_evox_super.py`）を集約し、スクリプト内の絶対パスをすべて相対パスへ変更。
  - `logs/`: 実機から取得した生ログ一式（`dumpsys_location*.txt`, `logcat_*.txt`, `dmesg_avc.txt`, `diag_report.txt`）を移動。
  - `archive/`: 検証用一時スクリプトおよび実機・Stockからの抽出ファイル（`device_etc/`, `stock_extracted/` 等）を移動して保持。
- **GitHubパブリック公開対応とローカルコミット作成**:
  - `.gitignore` を作成し、位置座標等の個人情報を含む `logs/`、抽出データ `archive/`、大容量ROMイメージ（`1_stock20images/`, `EvolutionX-*/`）をGit管理対象から除外。
  - 原因解説と導入手順をまとめた `README.md`（日本語）および `README_en.md`（英語）を作成し、`git init` およびローカルコミットを作成。
