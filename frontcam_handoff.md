# インカメラ写真の緑被り: 調査の引き継ぎメモ (2026-11-10 時点・未解決)

RedMagic 11 Pro (NX809J) + EvolutionX A17 (2026-10-10 ビルド) で、標準カメラ (`com.android.camera` / NubiaCamera) の
インカメラ (画面下カメラ `ov16a1q`、HAL カメラ ID 3、論理カメラ `cam1`) の **写真だけ** が緑がかる問題の調査記録。
ここまでで原因箇所はかなり絞れているが、修正は未完成。次に作業する人 (または別の AI) がここから再開できるように書く。

- 経緯の詳細は [`sagyou.md`](./sagyou.md) のマイルストーン 7〜10。
- 調査ツールは [`scripts/camdebug/`](./scripts/camdebug/)。
- 取得したログ・写真・ダンプは `logs/` (gitignore 済み)。**個人情報を含むのでコミットしない**。

---

## 1. 結論の要約 (確定していること)

1. **写真の経路で、ホワイトバランス (WB) がどこでも掛かっていない。** これが緑の直接原因。
   - AWB ゲインは R≒1.5 / G=1.0 / B≒3.1。これが掛からないと R は 0.65 倍、B は 0.32 倍のままになり、
     そのあと色補正行列 (CCM) が掛かるので青がほぼ 0 になる。白い対象で写真は RGB ≒ [90, 115, 20]、プレビューは [190, 190, 185]。
2. プレビューと動画は別経路で、IPE の WB モジュール (`IPEWB`, WB15) が有効なので正常。
3. 写真の経路では IPE の WB は **設計上** 無効 (`IPEWB en=0`)。これは正常なアウトカメラの写真でも同じ。
   写真では WB は IPE より上流の **OFE** が掛ける。アウトカメラでは OFE 出力が無彩色になっている (実測)。
   インカメラでは OFE 出力の時点で既に緑寄り (実測)。
4. インカメラの写真は、アウトカメラと違って **Quad CFA フル解像度の非 ZSL 撮影 (NZSL)** という別の経路を通る。
   - アプリが、通常枠 (最大 2304x1728) ではなく、`qcfa_dimension` の 4608x3456 (16MP) を要求するため。
   - センサーはプレビュー用の mode 1 (2304x1728) から、撮影の瞬間だけ mode 0 (4608x3456, `QUADCFA (SWR)`) に切り替わる。
5. この経路はストックのコードが想定していない形跡がある (後述 3 章)。EvolutionX はクラッシュする箇所だけをバイナリパッチで塞いでいる。

## 2. 写真のパイプライン (実測で確認)

```
インカメラ (cam1) の写真 1 枚:
  RealTimeFeatureNZSLSnapshotRDI0   センサー mode 0 (4608x3456) の RAW を 5 枚取得 (1 枚目は暗い、2〜5 枚目を使用)
    -> SWMFMergeRawCudProcess0      com.zte.node.aicud : RAW の AI 補正 (libin_display.so + libmfnr_network.so)。出力 14bit RAW
    -> ZSLSnapshotYUVHAL0           OFE[4] -> IPE[3] : RAW を YUV に現像。ここで緑になる
    -> InternalZSLExtendYuv2Jpeg0   capturepostprocess (yuv_udc の AI 補正) -> IPE[20],[21],[11] -> JPEG

アウトカメラ (cam0) の写真 1 枚 (正常):
  RealtimeDefault0 の ZSL フレーム (プレビューと同じセンサーモード)
    -> SWMFMergeRaw0                com.zte.node.aipreprocess : RAW の AI 補正
    -> ZSLSnapshotYUVHAL0 -> InternalZSLExtendYuv2Jpeg0
```

### 白い対象 (レンズにティッシュ) での実測値

| 段 | インカメラ (異常) | アウトカメラ (正常) |
|---|---|---|
| センサー RAW (10bit)、黒レベル | **約 518** (最小値 508〜513、暗フレームの平均 521〜529) | 約 64 |
| センサー RAW の Bayer 各色 | 598 / 705 / 654 (B / G / R) | 105 / 169 / 115 |
| AI 出力 RAW (14bit) | 9550 / 11254 / 10440。**入力 × 16 とほぼ同じ** (下駄 518×16=8288 が残る) | (入力−64)×16×1.44+1024。色比は入力のまま |
| OFE[4] 出力 (PD10, 8bit 相当) | Y=82 U=**115** V=**123** (緑寄り) | Y=87 U=125 V=128 (無彩色) |
| IPE[3] 出力 (NV12) | RGB ≒ [95, 129, −3] | Y=95 U=123 V=130 |
| 参考: プレビューの OFE[1] 出力 | Y=140 U=127 V=127 (無彩色) | Y=71 U=126 V=127 |

- AI ノードには `black_level: 64.000000` が渡っている (ログ `CAiCud-native-client: Process: 234`)。
  アウトカメラは 64.0〜65.2 と毎回変わる (動的な値)。インカメラは常にちょうど 64.0。
- AI 設定ファイル `/vendor/etc/camera/mfnr_network_denoise_config_underdisplay.xml` の `camera_id="1"` も `black_level_camera="64"`。
  これを 518 に書き換えて被せても、ログの値は 64 のままで効果なし (ノードがメタデータ側の値を使う)。
- インカメラの OFE 出力の色比 (R/G ≒ 0.82、B/G ≒ 0.67) は、「黒レベル 518 を引いた、WB 未適用のセンサー色比 (0.73 / 0.43) にガンマを掛けた値」とほぼ一致する。
  つまり **OFE は黒レベルは正しく扱い、WB だけ掛けていない** と読むのが一番つじつまが合う。ただし OFE 出力は階調補正済みで線形ではないので、これは推定。

## 3. EvolutionX が vendor に当てているバイナリパッチ (ストック B20 との比較で判明)

BuildId が同じなのに中身が違うファイル = 再ビルドではなくバイナリパッチ。

| ファイル | 内容 |
|---|---|
| `/vendor/lib64/com.qti.feature2.rawhdr.so` | 1 命令だけ違う。`ChiFeature2RawHDR::OnPopulateConfigurationSettings` 内 (vaddr 0x26324) の `ldr w12, [x28]` を `mov w12, #0` に変更。元の命令は `m_pInstanceProps` の先頭 (instanceId) を `ppDeviceInfo[]` の添字に使う。インカメラの写真では **instanceId = 256 (NZSL + swremosaic のインスタンス)** になるため、元の命令に戻すと null 参照でクラッシュする (実機で確認)。添字を 1 にしてもクラッシュせず、色も変わらない |
| `/vendor/lib64/hw/com.qti.chi.override.so` | 152 バイト差。(a) ズーム倍率らしき float 10 個を 50.0 に統一、(b) `.data.rel.ro` のカメラ番号対応表 111 か所 (ストックの 1,2,3 → 2,0,1 など)、(c) `ExtensionModule::GetDevicesSettings` で `kaanapali_gsi.xml` を参照する箇所を `kaanapali.xml` に変更、(d) `IsStreamCombinationSupported` の `ldr x11,[x0,#0x458]` → `#0x460` |

**重要な示唆:** ストックのコードは instanceId 256 のまま `ppDeviceInfo[256]` を読むとクラッシュする。
つまり ZTE のストック ROM では、インカメラの写真がこの「NZSL + RawHDR(CUD)」の組み合わせを通っていない可能性が高い。
ストックでは別のグラフ (ZSL のビニング撮影 + アップスケール、または SWRemosaic 経由) になっていると推測される。未検証。

## 4. 否定済みの仮説 (やり直さなくてよい)

- センサーのチューニング、AI モデル、QNN ライブラリ、`camera.ko` の差 → ストックと同一、または無関係。
- アプリの `color_compensation`、美顔、撮影モード、写真の比率 (16:9 でも 4608x2592 の同じ経路)。
- `rawhdr.so` のパッチの添字 (0 と 1 で結果は同じ)。
- IPE の WB15 を強制的に有効化 (`libcamxhwlipedriver.so` vaddr 0x34ab5c の `ldr w9,[x9]` → `mov w9,#1`) → **真っ黒** になる。
  WB15 に渡る入力構造体のゲインが 0 のまま。有効フラグの元は `pInputData+0xe84` で、これは「リアルタイム IPE かどうか」のフラグ。
- Quad 配列前提のゲインを Bayer データに掛けている説 → 現像後の画像に 4 画素周期の模様が無いので否定。
- `camxoverridesettings.txt` の `exposeFullSizeForQCFA=FALSE`、`AECGainThresholdForQCFA=1` → どちらも効果なし。
- システムプロパティの欠落 (ストックの build.prop と比較) → カメラに関係する差は無い。
- 第三者アプリでの切り分け → インカメラはシステムカメラ扱いで見えない。

## 5. 未解決の問い

1. **OFE はなぜインカメラの写真で WB を掛けないのか。** OFE の実装は `/vendor/lib64/libcamxofehwl.so`。
   `camera.qcom.core.so` に `demuxblklevel142_ofe_qcfa_v2` という Quad CFA 専用の「黒レベル + チャンネルゲイン」チューニングモジュール名がある。
   センサーモードが Quad CFA 扱いのとき、OFE がこの Quad CFA 用モジュールを選び、そこにゲインが入らない (あるいはインカメラ用のチューニングが無い) 可能性。
2. **センサー mode 0 の黒レベルが 518 なのは仕様か異常か。** AI 側は 64 前提。OFE 側は 518 を正しく引いているように見える。
3. **ストック ROM では、インカメラの写真はどのグラフを通るのか。** これが分かれば正解の形が決まる。

## 6. 次の一手 (優先順)

### A. ストック ROM で同じ計測をして「正解」を取る (最も確実)
ストックに一時的に戻せるなら、同じ手順 (7 章) で `REQMAP` のパイプライン名、`[XCFA]` のログ、ダンプの各段の値を取る。
見るべき点: 写真が NZSL (`RealTimeFeatureNZSLSnapshotRDI0`) を通るか、`SWRemosaic` を通るか、AI ノードに渡る black_level、OFE 出力の U/V。

### B. インカメラの写真を NZSL (Quad CFA) に入れない
アウトカメラと同じ「ZSL フレーム → AI → OFE」に流せば、OFE の WB が効く見込み。
- 判定は `/vendor/lib64/com.qti.feature2.gs.sm8850.so` (ストックと同一) の `GetNZSLSnapshotFlag`。
  ログ文字列 `[XCFA] isHighResStrmFound: %d, nzsl flags: 0x%x, isQCFASnapshot: %d, isB2YBinningSnapshot: %d, isMCX: %d` の参照が vaddr 0xd4514 にある。
  関数本体はおおよそ 0xd41a0〜0xd4530。実機では `isHighResStrmFound: 1, nzsl flags: 0x3, isQCFASnapshot: 1, isB2YBinningSnapshot: 0, isMCX: 1`。
  ここで nzsl flags を 0 にする、または `isB2YBinningSnapshot` を 1 にするパッチを作り、`cam_apply.sh` で被せて試す。
  同じ関数群に `AEC Gain` と `AEC Gain Threshold` を比べる分岐 (ログ参照 0xd48b8) があるが、MCX 経路では通っていない。
- 別案: インカメラの静的メタデータから `is_qcfa_sensor` / `qcfa_dimension` を消す (アプリは `org.codeaurora.qcamera3.quadra_cfa.*` を読んで 16MP を選ぶ)。
  生成元は `com.qti.chi.override.so` の `UpdateQCFACaps` 付近。アウトカメラの高解像度モードを壊さないよう、カメラを限定する必要がある。
- この案だと写真は 2304x1728 (4MP) になる可能性がある。センサーは Quad Bayer なので実解像度は 4MP 相当で、画質面の損失は小さいはず。

### C. Quad CFA 経路のまま WB を掛けさせる
- OFE 側: `libcamxofehwl.so` で WB (demux / channel gain) のゲインをどこから取るかを追う。
  アウトカメラとインカメラの写真で OFE の入力メタデータ (AWB ゲインのタグ) がどう違うかを比べる。
  現状の verbose マスクでは OFE の IQ モジュールのログがほとんど出ない (`camxofecst12.cpp` と `camxofercs20.cpp` だけ)。
- IPE 側: WB15 に正しいゲインを渡す。入力構造体は `IPEIQModuleInputData+0xa8` が指す先 (先頭が有効フラグ、+0xc/+0x10/+0x14 がゲイン)。
  これを埋めているコードが未特定。IPE ノードは `GetAWBFrameControl()` で正しいゲイン (1.56 / 1.0 / 3.11) を読めている (ログで確認)。
  ただしアウトカメラの写真では OFE が WB を掛けるので、**インカメラに限定しないと二重に掛かる**。

### D. 最後の手段
壊れていない段から自前で分岐する。たとえば AI 出力 RAW (色比は正しい) を使う、あるいは写真だけプレビュー系の経路の出力を使う。

## 7. 再現と計測の手順

前提: adb 接続、KernelSU の root、端末の画面は点灯してロック解除、標準カメラを起動。画面は 1216x2688。

```bash
# 1 枚撮って色を測る (レンズにティッシュを被せると白い対象になる)
adb shell input tap 1080 2328            # カメラ切り替えボタン (起動直後は背面 ID 1。インカメラは ID 3)
bash scripts/camdebug/cam_shot.sh base   # プレビューと写真の中央 RGB を表示

# vendor のファイルを一時的に差し替える (再起動か --restore で元に戻る)
bash scripts/camdebug/cam_apply.sh <ローカルファイル> /vendor/...
bash scripts/camdebug/cam_apply.sh --restore /vendor/...
```

- **各段の画像ダンプ:** `camxoverridesettings.txt` の末尾に下の 4 行を足したものを被せる。
  出力先は `/data/vendor/camera/p[パイプライン]_req[..]_..._w[..]_h[..]_stride[..]_scanline[..]_日時.形式`。
  ```
  autoImageDump=TRUE
  autoImageDumpMask=0xFFFFFFFF
  autoInputImageDumpMask=0xFFFFFFFF
  offlineImageDumpOnly=TRUE
  ```
  `offlineImageDumpOnly` を外すとセンサーの RDI (`RealTimeFeatureNZSLSnapshotRDI0 ... port[50] ... RawPlain16LSB10bit`) も出る。
  プレビュー中は毎秒 1GB 近く増えるので、1 枚撮ったらすぐ戻して `p[` で始まるファイルを消す。
  取り出したファイルは `python scripts/camdebug/camx_dump_analyze.py <ディレクトリ>` で要約できる。
- **verbose ログ:** 同じファイルに `logVerboseMask=0x40220018`、`logInfoMask=0x40220018`、`logConfigMask=0x40220018` を足す
  (IQMod / ISP / PProc / HWL / BPS の各グループ)。`adb logcat -G 256M` でバッファを広げてから撮る。
  見るべき行: `IQ 57 IPEWB module en`、`DumpTuningModeData`、`GetAWBFrameControl`、`[REQMAP]`、`hdrplus`、`CAiCud-native-client`。
- **ストックとの比較:** `scripts/camdebug/dump_part.py` で `super.img` から `vendor_a` を取り出し、WSL (Ubuntu) の `fsck.erofs --extract` (erofs-utils 1.9 以降) で展開する。
  リポジトリの `scripts/erofs_tool.py` は圧縮ファイルを読めない (空になる) ので、内容の比較には使わない。
- **逆アセンブル:** Python の `capstone` と `pyelftools`。文字列への参照は `adrp` + `add` の組で探す。
  この文書のアドレスは 2026-10-10 ビルドの端末上のファイル (SHA-256 の先頭: `rawhdr.so` = dffe47d4、`libcamxhwlipedriver.so` = dedb11ce) に対するもの。

## 8. 作業上の注意

- `adb shell su -c 'a; b'` は、全体を 1 つの文字列として引用しないと 2 つ目以降が root で動かない (`adb shell "su -c 'a; b'"`)。
- camera provider は `stop` / `start` が効かない。`kill $(pidof vendor.qti.camera.provider-service_64)` で init に再起動させる。
- 差し替えを戻すときは、provider を kill した直後に `umount` する (使用中だと busy で失敗する)。
- 実験が終わったら必ず確認する: `mount | grep camtest` が 0 件、`/data/local/tmp/camtest_*` が無い、`/data/vendor/camera` にダンプが残っていない。
- 壊れた設定で撮ると写真が真っ黒になったり provider が落ちたりするが、bind mount を外せば元に戻る。`/vendor` 自体には一切書き込んでいない。
