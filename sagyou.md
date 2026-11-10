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
  - `/data/vendor/location/xtra/xtra.sqlite` をバックアップ（`.bak`）した上でリトライ回数カウンタを `0` にリセットし、`xtra-daemon` / `loc_launcher` / `gnss_service` を再起動。
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

## マイルストーン6: 公開前の最終整備 (2026-10-16)
- **公開前の検証**: 追跡ファイル・コミット履歴を全件確認。公開対象に実際の位置座標、ユーザー固有のパス、シリアル・IMEI・MAC・IP 等は含まれないことを確認。
- **生ログの移動**: 実機の生ログ（`Location[fused|network ...]` 等の測位座標を含む）を `logs/` からリポジトリの外（`../rmGPSfix_logs/`）へ移動。`.gitignore` の除外設定は保険として残す。
- **モジュール情報の修正**: `module.prop` の `author` を `Antigravity` から `realryo1` に変更し、`scripts/build_ksu_module.py` で `module/` と ZIP を再生成。
- **ライセンス**: MIT License の `LICENSE` を追加。`module/izat.conf` は ROM 由来のため、原本の権利に関する注記を README に追加。
- **README の整備**: 検証環境（KernelSU のみ検証済み）、ROM イメージを含まないことによる再現手順、ライセンスの注記を日英両方に追記。Magisk / APatch の記述は未検証のため削除。
- **誤字修正**: 本ファイル内の「备份」を「バックアップ」に修正。
- **据え置き**: コミット作者のメールアドレスは変更せず保持。リモートはユーザーが設定予定。

## マイルストーン7: インカメラ写真の緑被り調査（未解決） (2026-10-20〜21)
- **症状**: 標準カメラ（`com.android.camera` / NubiaCamera）のインカメラ（画面下カメラ `ov16a1q`、内部カメラID 3）で撮影した写真だけが、緑（黄緑）がかって保存される。
- **実測（`scripts/measure_color.py`）**:
  - 写真: R/B ≒ 2.5〜2.8、G/B ≒ 3.1〜3.5（青が極端に不足）。美顔 ON/OFF のどちらでも同じ。
  - 動画のフレーム: R/B ≒ 1.08、G/B ≒ 1.03（ほぼ中立）。動画は正常。
  - 写真の青不足の比率は、ログ上の AWB ゲイン（R≒1.5 / G=1.0 / B≒3.3）の比とほぼ一致する。写真の経路で AWB ゲインが反映されていない可能性が高い。
- **写真の経路**: RAW 4コマ（4608x3456）を RAW 領域の AI 補正（`CAiCud` / `libin_display.so` の `In_display_process_raw`、AWB ゲインとレンズシェーディングマップを入力に取る）→ ISP オフライン再処理 → YUV 領域の AI 補正（`yuv_udc` / QNN `udc_512_512_12`）→ JPEG。動画はこれらを通らない。どちらの AI 補正もエラーなく完走している。
- **原因ではないと確認したもの（ストック B20 の `vendor_a` を `fsck.erofs`（erofs-utils 1.9.1、WSL）で展開して SHA-256 比較）**:
  - `vendor/lib64/camera/` のセンサー・チューニング・EEPROM・センサーモジュール、`vendor/etc/camera/` の UDC 系 AI モデル（`udc_512_512_12Binary.bin` 他）は全て一致。
  - QNN/HTP ライブラリ、`libin_display.so`、`libmfnr_network.so`、`libUDCInterface.so` は一致。
  - `camera.qcom.core.so`、`com.qti.chi.override.so`、`libcom.nubia.chinodenubiautils.so`、`com.qti.stats.{aec,af}.so` はサイズ同一で、文字列差分はビルド時の行番号のみ（同一コードの再ビルド）。
  - `camera.ko` の差分は OIS 関連のみ。
  - 端末の標準カメラは `11.0.011-redmagic.2603040916`（ストックは `2604031853`）で、vendor（2026-03-20）と同世代であり整合している。署名がストックと異なるため上書きインストールは不可。
  - アプリの `color_compensation` は `getColorCompensation()` が常に 0 を返す未使用項目。
  - `persist` 側の UDC 向けキャリブレーションデータは存在しない（`dualcam_cali.bin` のみ）。
- **第三者アプリでの切り分けは不可**: インカメラ（ID 3）はシステムカメラ扱いで、`SYSTEM_CAMERA` ロールを持たないアプリ（Open Camera 等）には公開されない。`persist.vendor.camera.privapp.list` への追加でも公開されなかった（変更は元に戻し済み）。
- **その他のログ上の気になる点（原因かは未確定）**: アプリが HAL に存在しない vendor タグ（`af_lock`, `lcd_light`, `is_auto_hdr`, `super_night_frame_done`, `HDRVideoMode`）を参照している。gralloc が不正な dataspace（134217986 = `0x08000102`）の警告を大量に出している（Android 17 のフレームワークと Android 16 世代の vendor の組合せ）。
- **結論と次の一手**: vendor 側のファイル差し替え型の修正（GPS 修正と同じ方式）では直らない見込み。次は CamX のデバッグログを有効にした状態で写真を1枚撮影し、ISP オフライン再処理で AWB ゲインが失われる箇所を特定する。
- **注意**: 撮影した写真・動画・logcat は個人情報を含むため `logs/` に置き、`.gitignore` で除外している（画像・動画・APK の拡張子も除外）。

## マイルストーン8: 白い対象での切り分けと rawhdr 差分の検証（未解決） (2026-10-21)
- **白い対象（ティッシュを被せたインカメラ）での測定**:
  - プレビュー（スクリーンショット）の中央部は R200 / G200 / B194 でほぼ中立。
  - 保存された写真の中央部は R98 / G136 / B2。青がほぼ消えており（青チャンネルが潰れている）、単に AWB ゲイン（B≒3.3）が未適用なだけでは説明できない。
  - フェースビューティー（`PRETTYCAMERA`）モードでも同じ RAW / YUV の AI 補正が走り、経路は変わらない。インカメは「プロ」モードに存在しない。
- **CamX デバッグログ（`camxoverridesettings.txt` を一時的に bind mount して `chiLogInfoMask` などを `0xFFFFFFFF` に）**:
  - オフライン再処理は IPE のみで、`IPEWB` は有効。入力フレームの AWB は R≒1.43 / G=1.0 / B≒3.31 と出ている。
  - 「ここで落ちている」と断定できる行は見つからなかった。`AWBR` の 1.0 ゲイン出力や `Failed to get AWBFrameControlTag` は、プレビュー起動時にも出る通常動作。
- **`com.qti.feature2.rawhdr.so` の4バイト差は B18/B20 のビルド差**:
  - 端末（B18）は `mov w12, #0`、ストック（B20）は `ldr w12, [x28]`（オフセット 0x26324）。
  - ストックの命令に戻して bind mount すると、前面カメラのシャッターで `vendor.qti.camera.provider-service_64` が `ChiFeature2RawHDR::OnPopulateConfigurationSettings` 内で SIGSEGV（null 参照）。`com.qti.chi.override.so`（こちらも152バイト差）と対で変わる変更であり、片方だけ戻すと整合しない。
  - この検証で「白く撮れた」ように見えた画像は、実際には 182x243 のサムネイルと背面カメラの暗い画像だった（前面の本画像は保存されていない）。
  - テスト用の mount は解除し、provider も再起動して元に戻し済み。
- **`dsp_a` の比較**: 端末とストック B20 でサイズ同一、4KB ブロックが 15 個（全体の約0.08%）異なるのみ。先頭付近のメタデータとみられ、ファームウェア版差の根拠にはならない。
- **調査用の注意点（再現時）**: `adb shell su -c 'a && b'` は `su` が最初のコマンドにしか効かない。`adb shell "su -c 'a; b'"` のように全体を引用する。`chcon` などの操作が拒否されるときは、この引用ミスを疑う。provider の再起動は `stop`/`start` が効かないため、`kill $(pidof vendor.qti.camera.provider-service_64)` で行う（init が再起動する）。
- **次の切り分け**: 写真の経路のうち、YUV 側の AI 補正（`yuv_udc` / `udc_512_512_12Binary.bin`）を一時的に無効化して撮影し、青の潰れが消えるかを確認する。

## マイルストーン9: YUV 側 AI 補正の無効化テスト（未解決） (2026-10-21)
- **テスト内容**: `/vendor/etc/camera/udc_512_512_12Binary.bin`（`yuv_udc` の QNN コンテキストキャッシュ）を空ファイルで一時的に bind mount し、provider を再起動して前面カメラで1枚撮影。
- **結果**: ログは `Create From Binary failure` となり、保存された写真は真っ黒（R=G=B=0）。クラッシュはしない。このステージは失敗時に元画像へ素通しされず、出力そのものを作るため、「飛ばして色を確認する」切り分けはできない。
- テスト用の mount は解除し、provider を再起動して元に戻し済み（キャッシュは元のサイズ 124,338,176 バイトに復帰）。
- **現時点の見立て**: vendor 側のファイル差し替え型の修正では直らない見込み。残る可能性は、(1) RAW 側の AI 補正（`libin_display.so`）が青を潰している、(2) Android 17 のフレームワークと B18 vendor の組み合わせによる不整合（ROM 側の問題）。次の手は、ROM 側への報告、または CamX のバッファダンプによる各ステージ出力の確認。

## マイルストーン10: 各段ダンプによる原因箇所の特定と引き継ぎ（未解決） (2026-11-10)
- **手法**: `camxoverridesettings.txt` を一時的に bind mount して CamX の画像ダンプ (`autoImageDump`) と verbose ログを有効化し、写真 1 枚の各段の出力を実測。撮影はキーイベントで自動化 (`scripts/camdebug/`)。
- **判明したこと**:
  - 写真の経路は `RealTimeFeatureNZSLSnapshotRDI0`（センサー mode 0、4608x3456、Quad CFA 扱いの非 ZSL 撮影）→ `SWMFMergeRawCudProcess0`（RAW の AI 補正）→ `ZSLSnapshotYUVHAL0`（OFE → IPE）→ `InternalZSLExtendYuv2Jpeg0`。
  - 緑になるのは OFE → IPE の現像段。白い対象で OFE 出力が U=115 / V=123（プレビューとアウトカメラは U≒126 / V≒128）。
  - 直接原因は「写真の経路で WB がどこでも掛かっていない」こと。IPE の WB モジュールは写真では設計上無効（アウトカメラも同じ）で、WB は OFE が掛ける。インカメラの写真では OFE が WB を掛けていない。
  - 写真用センサーモードの RAW の黒レベルは約 518（プレビューは 64）。AI ノードには 64 が渡っている。
  - EvolutionX は `com.qti.feature2.rawhdr.so` と `com.qti.chi.override.so` にバイナリパッチを当てている（BuildId が同じで中身が違う）。`rawhdr.so` のパッチが塞いでいるクラッシュは、instanceId 256（NZSL + swremosaic）を配列添字に使うことで起きる。ストックのコードはインカメラがこの経路を通る想定になっていない可能性が高い。
- **試して効果が無かったもの**: `rawhdr.so` の添字を 1 に変更、IPE の WB15 の強制有効化（真っ黒になる）、AI 設定 XML の黒レベル変更、`exposeFullSizeForQCFA=FALSE`、`AECGainThresholdForQCFA=1`、写真の比率を 16:9 に変更。
- **端末の状態**: 実験用の bind mount・一時ファイル・ダンプはすべて除去済み。`/vendor` への書き込みは無し。
- **引き継ぎ**: 事実・数値・アドレス・次の一手は [`frontcam_handoff.md`](./frontcam_handoff.md) にまとめた。

## マイルストーン11: NZSL フラグを 0 にした写真の色（ぬいぐるみの目で確認） (2026-11-10)
- **パッチ**: `com.qti.feature2.gs.sm8850.so` の `ChiFeature2GraphSelector::GetNZSLSnapshotFlag`（vaddr `0xd4e24`）の `mov w11, w23` を `mov w11, wzr` に変更。戻り値の下位 32bit（nzsl flags）だけを 0 にする。呼び出し元 `SelectFeatureGraphforRequestFromTable` はここを `[sp+0x8c]` に保存してグラフ選択フラグへ混ぜる。bind mount のみで、`/vendor` には書いていない。
- **ぬいぐるみの目** (`IMG_20261110_230643.jpg`、4608x3456):
  - 青い目の画素平均 RGB ≒ [36, 78, 120]。青が最大で、緑被りの潰れ方ではない。
  - 白い生地の画素平均 RGB ≒ [182, 183, 174]。壊れていた白い対象（RGB ≒ [90, 115, 20]）とは違う。
- **経路**: `RealTimeFeatureNZSLSnapshotRDI0` には入らない。AI (`CAiCud`) の入力は 2304x1728、`black_level` は 64。`ZSLSnapshotYUVHAL0` は入力 2304x1728 を出力 4608x3456 に拡大する（`postScaleRatio=0.5`）。写真用 IPE の `IPEWB` は従来どおり `en 0`。色が直ったのは、WB の掛かるビンニング側へ寄ったため。保存ファイルの画素数は 16MP のままで、中身は 4MP からの拡大。
- **ログ用の `camxoverridesettings.txt` は検証後に外す。** 色のパッチは再起動するまで bind mount のまま。
- **手動確認**: ユーザーがぬいぐるみの目で色の修正を確認した。

## マイルストーン12: 撮影直後の左下プレビューが真っ黒 (2026-11-10)
- **症状**: インカメラで撮ってすぐ左下サムネイルを開くと、日付だけで画面が真っ黒。アウトカメラはすぐ開いても真っ黒にならない。完成した JPEG 自体は真っ黒ではない。
- **実測**（色パッチ適用中、`IMG_20261110_231739.jpg`）: シャッターからファイル出現まで約 2.9 秒。内訳は RAW AI（`CAiCud`）がモデル初期化込みで約 0.4 秒、YUV の画面下補正 `yuv_udc` が初期化 566ms + 推論 598ms。処理の途中（約 1 秒時点）でアプリが `notifyProcessingUri` を出し、中身の無いメディア項目を先に作る。そこを開くと日付だけ見える。
- **サムネイル用タグ**: `com.zte.node.capturepostprocess.so` などが `ThumbnailSnapshot` を読めず `Get vendor tag Thumbnail snapshot failed`。失敗しても処理は続行する。先に小さなプレビューを渡す経路が、このグラフでは動いていない。

## マイルストーン13: 色修正の KernelSU モジュール (2026-11-10)
- **super.img の APK**: カメラは `/product/priv-app/NubiaCamera/NubiaCamera.apk`。product は super.img の中なので、同じ署名かつより大きい versionCode の APK を入れて super.img だけ焼き直せば、起動時のパッケージ走査で置き換わる。署名が違うと置き換わらない。versionCode が同じだと更新扱いにならないことがある。
- **モジュール**: 緑被りの回避（`GetNZSLSnapshotFlag` の `mov w11, w23` → `mov w11, wzr`、ファイルオフセット 0xd4e26 の `17` → `1f`）。起動時に端末上の so を複製してその 1 バイトだけ変え、bind mount する。サイズ 1545632 かつ命令 `eb 03 17 2a` のときだけ当てる。適用後の命令は `eb 03 1f 2a`。単独モジュール `rm11pro_frontcam_wb` で実機確認したあと、マイルストーン16 で GPS モジュール v2.0 に移した。
- **APK のくるくる表示はモジュールに入れていない。** 左下サムネイルのビットマップはアプリのプロセス内だけで、別署名の APK を被せるとシステムアプリとして載らない。

## マイルストーン14: サムネイルの開き先は既定アプリではない (2026-11-10)
- 画像の VIEW に既定アプリは無く、選ぶ画面になる。システムギャラリーのロールは `org.lineageos.glimpse`。
- 左下タップ `ThumbnailOnClickListener.goToGalley` は `CameraUtil.viewUri` / `viewUriInPhotos` を呼び、どちらも `setPackage("org.lineageos.glimpse")` で Glimpse の `ViewActivity` を直接開く。実測でも 23:51 以降のタップはすべて Glimpse。
- `checkIfUseGooglePhotosAsGallery` は framework の `config_systemGallery` が `com.google.android.apps.photos` を含むときだけ真。サムネイルの経路はこれを見ずにパッケージを固定している。既定アプリを消しても Google フォトにはならない。

## マイルストーン15: 「しっかり握ってください」が消えてから開くと見える (2026-11-10)
- 文言は `show_night_capture_text`（「撮影中、デバイスをしっかり握ってください」）。画面下インカメの撮影で `NormalMemberFragment.onUnderScreenStart` が出して、`onUnderScreenStop` で消す。
- この表示が残っている間は JPEG がまだ無い。消えてから左下を開くと、中身の無い処理中項目ではなく完成した写真になる。アウトカメラはこの画面下撮影に入らないので、すぐ開いても真っ黒にならない。

## マイルストーン16: GPS と緑被りを v2.0 の1パッケージに (2026-11-11)
- モジュール id は `gps_incamera_fix`、`version=v2.0` / `versionCode=2`。配布 ZIP は `gps_incamera_fix_v2.0.zip`。旧 id `rm11pro_gps_fix` とは別モジュールになる。
- `module/apply.sh` が緑被りの 1 バイトパッチを担当し、`post-fs-data.sh` と `service.sh` から呼ぶ。マウント確認は `gps_incamera_fix`。違うビルドの so は素通り。
- 試験導入した `rm11pro_frontcam_wb` は外す。同じパッチが v2.0 に入っている。
- Glimpse を直接開く件と、「しっかり握ってください」が消えるまで待つ件は、モジュールでは直していない。
