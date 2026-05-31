# latebra

**多層回避パイプラインによる匿名WebスクレイピングのためのアンチボットMCPサーバー。**

latebraは、TLSフィンガープリンティング、ブラウザステルス、人間行動シミュレーション、プロキシローテーション、およびCAPTCHA解決を単一のMCPサーバーに統合します。各レイヤーは自動フォールバック機構を備えています：HTTPリクエストが検出により失敗した場合、パイプラインはブラウザステルスにエスカレーションします。ブラウザがブロックされた場合、ヘッドレスクローラーによる抽出を試みます。常に最大限の匿名性を維持します。

---

## パイプライン

```
+----------+    +-----------+    +--------------+
| REQUEST  |--->|  BROWSER  |--->| EXTRACTION   |
| curl_cffi|    | Playwright|    | Crawl4AI     |
| TLS imp. |    | + stealth |    | + regex      |
+----+-----+    +-----+-----+    +------+-------+
     |                |                 |
     v                v                 v
+----------+    +-----------+    +--------------+
|  PROXY   |    |STEALTH    |    |   CACHE      |
| Manager  |    |Fingerprint|    |  SQLite TTL  |
| Rotation |    | + Behavior|    |  Dedup       |
| Health   |    | Canvas    |    |              |
| Check    |    | WebGL     |    |              |
+----------+    +-----------+    +--------------+
                     |
                     v
               +----------+
               |  CAPTCHA  |
               |  Solver   |
               | 2Captcha  |
               | Capsolver |
               +----------+
```

パイプラインはグレースフルデグラデーション戦略に従います：

1. **Request** -- `curl_cffi`とTLS偽装による初回試行
2. **Browser** -- 検出された場合、ステルスプロファイルでPlaywrightを起動
3. **Extraction** -- Crawl4AIまたは正規表現フォールバックによるコンテンツ抽出
4. **Cache** -- 設定可能なTTLでSQLiteに結果を保存

補助モジュール（プロキシ、ステルス、CAPTCHA）は全レイヤーにわたって動作します。

---

## アーキテクチャ

```
src/latebra/
|
+-- server.py                # MCPサーバー -- ツール: scrape, extract, health
|
+-- pipeline.py              # SmartScrapePipeline -- フォールバックオーケストレーター
|
+-- layers/
|   +-- request.py           # curl_cffi + TLS偽装 + プロキシ
|   +-- browser.py           # Playwright + ステルス初期化
|   +-- extraction.py        # Crawl4AI + 正規表現フォールバック + SQLite TTLキャッシュ
|
+-- proxy/
|   +-- manager.py           # プロキシローテーション、ヘルスチェック、自動禁止
|
+-- stealth/
|   +-- fingerprint.py       # Canvas, WebGL, WebRTC スプーフィング
|   +-- behavior.py          # ベジェ曲線、人間的遅延、自然なスクロール
|
+-- captcha/
    +-- solver.py            # 2Captcha + Capsolver
```

### 実行フロー

```
                  +-------------------+
                  |  MCP Client       |
                  |  (Claude, Cursor) |
                  +--------+----------+
                           |
                           v
                  +-------------------+
                  |  server.py        |
                  |  scrape / extract |
                  +--------+----------+
                           |
                           v
                  +-------------------+
                  |  pipeline.py      |
                  |  fallback chain   |
                  +---+---+---+-------+
                      |   |   |
              +-------+   |   +-------+
              v           v           v
        +----------+ +--------+ +----------+
        | request  | |browser | |extraction|
        | curl_cffi| |Playwr. | |Crawl4AI  |
        | TLS imp. | |stealth | |+ regex   |
        +----------+ +--------+ +----------+
              |           |           |
              +-----------+-----------+
                          |
                          v
                  +-------------------+
                  |   SQLite Cache    |
                  |   (TTL + dedup)   |
                  +-------------------+
```

---

## インストール

pipおよびuvによるインストールにはPython 3.12以上が必要です。

### npm（推奨）

npmパッケージはPythonサーバーをラップし、すべての依存関係を自動インストールします：

```bash
npm install -g latebra
```

### uv

```bash
git clone https://github.com/evandrodevbr/latebra.git
cd latebra
uv sync
```

### pip

```bash
git clone https://github.com/evandrodevbr/latebra.git
cd latebra

# 最小構成（MCPのみ）
pip install -e .

# ブラウザサポート付き
pip install -e ".[browser]"

# 抽出サポート付き
pip install -e ".[extraction]"

# CAPTCHAサポート付き
pip install -e ".[captcha]"

# 完全版（全モジュール）
pip install -e ".[all]"
```

---

## 使用方法

### MCPサーバーとして

```bash
latebra run
```

またはPythonから直接：

```bash
python -m latebra run
```

MCPクライアント（Claude Desktop、Cursor、Hermes Agent）での設定：

```json
{
  "mcpServers": {
    "latebra": {
      "command": "python",
      "args": ["-m", "latebra", "run"],
      "env": {
        "PROXY_LIST": "socks5://user:pass@proxy1:1080,socks5://user:pass@proxy2:1080",
        "CAPSOLVER_API_KEY": "your_key_here"
      }
    }
  }
}
```

利用可能なツール：

- `scrape` -- HTTPからブラウザへのフォールバックを備えたインテリジェントスクレイピング
- `extract` -- 直接的な構造化コンテンツ抽出
- `health` -- ステータスチェックおよび匿名性レベルレポート

### Pythonライブラリとして

```python
import asyncio
from latebra.pipeline import SmartScrapePipeline

async def main():
    pipeline = SmartScrapePipeline(
        proxy_list=["socks5://user:pass@proxy1:1080"],
        capsolver_key="your_key",
    )

    result = await pipeline.scrape(
        url="https://example.com",
        force_browser=False,     # 最初にHTTPを試行
        extract_structured=True, # Crawl4AIで抽出
    )

    print(f"Status: {result.status}")
    print(f"Content: {result.content[:500]}")
    print(f"Layer used: {result.layer}")

asyncio.run(main())
```

---

## 実装された技術

- **TLSフィンガープリンティング** -- `curl_cffi`によるJA3/JA4フィンガープリント偽装
- **Canvasフィンガープリンティング** -- Canvas 2Dレンダラーでのノイズランダム化
- **WebGLフィンガープリンティング** -- WebGLベンダー/レンダラーのスプーフィング
- **WebRTCリーク防止** -- 実際のIPアドレス漏洩防止
- **JavaScriptチャレンジ** -- Cloudflare、DataDome、Akamaiのバイパス
- **行動シミュレーション** -- ベジェ曲線マウス移動、自然なスクロール、人間的な遅延
- **プロキシローテーション** -- ヘルスチェックと低速プロキシ禁止による自動ローテーション
- **CDP/DevTools検出** -- 検出可能なChrome DevTools Protocolフラグの除去
- **レート制限バイパス** -- 複数プロキシへのリクエスト分散
- **ハニーポット検出** -- トラップリンクの識別と除外
- **CAPTCHA解決** -- 2CaptchaおよびCapsolver対応、サービス間フォールバック
- **インテリジェントキャッシュ** -- 設定可能なTTLと重複排除を備えたSQLiteキャッシュ

---

## 推奨サービス

### プロキシサービス

latebraと相性の良い、コスト効率の高いプロキシプロバイダーの精選リスト：

**Webshare** -- 10個の無料プロキシ付きレジデンシャルプロキシ、データセンタープランは$2.99/月から。
- リンク: https://www.webshare.io
- 価格: レジデンシャル $4.50/GBから、データセンタープラン $2.99/月から
- 最適: 無料枠から始めたい開発者や小規模チーム

**IPRoyal** -- 従量課金制のレジデンシャルプロキシ、月額契約不要、静的レジデンシャルも利用可能。
- リンク: https://iproyal.com
- 価格: レジデンシャル $1.75/GBから、静的レジデンシャル $2.40/プロキシ/月から
- 最適: 長期契約なしの柔軟な利用

**Bright Data** -- 7200万以上のIPを持つ最大のプロキシネットワーク、エンタープライズグレードのプロキシマネージャー、最高の地理的カバレッジ。
- リンク: https://brightdata.com
- 価格: レジデンシャル 約$5.04/GBから
- 最適: 最大限のカバレッジと信頼性を必要とするエンタープライズワークロード

**Smartproxy** -- 5500万以上のIPプール、洗練されたダッシュボードとセットアップ簡略化のためのブラウザ拡張機能。
- リンク: https://smartproxy.com
- 価格: レジデンシャル $3/GBから
- 最適: 使いやすさとダッシュボード管理を重視するチーム

**Proxy-Cheap** -- 中小規模プロジェクトに適した手頃なレジデンシャルおよび静的レジデンシャルプロキシ。
- リンク: https://proxy-cheap.com
- 価格: レジデンシャル 約$3/GBから
- 最適: 中程度のボリューム要件を持つ予算重視のプロジェクト

### CAPTCHA解決サービス

latebraと相性の良い、コスト効率の高いCAPTCHA解決サービスの精選リスト：

**2Captcha** -- reCAPTCHA、hCaptcha、画像CAPTCHAにわたり実績のある信頼性を備えた、最も幅広いCAPTCHAタイプカバレッジ。
- リンク: https://2captcha.com
- 価格: reCAPTCHA v2 $0.50/1000から、reCAPTCHA v3 $1-$3/1000
- 最適: 最も幅広い機能サポートを備えた汎用解決

**Capsolver** -- Cloudflare Turnstile、hCaptcha、FunCaptcha対応のAI駆動自動解決。
- リンク: https://www.capsolver.com
- 価格: reCAPTCHA v2 約$1/1000
- 最適: Cloudflare Turnstileを含む最新のCAPTCHAタイプ

**Anti-Captcha** -- 一貫した価格設定、優れたAPIドキュメント、支援解決用ブラウザ拡張機能。
- リンク: https://anti-captcha.com
- 価格: reCAPTCHA v2 $0.50-$2/1000
- 最適: 十分に文書化されたAPIと予測可能な価格を重視するチーム

**CapMonster** -- reCAPTCHA v2の競争力のある価格、高速解決速度、Chrome拡張機能付き。
- リンク: https://capmonster.cloud
- 価格: reCAPTCHA v2の競争力のある料金
- 最適: 高速な処理を必要とする大規模運用

**DeathByCaptcha** -- 2010年から続く実績あるサービス、OCRベースの画像CAPTCHA解決と長年の信頼性。
- リンク: https://www.deathbycaptcha.com
- 価格: reCAPTCHA v2 $1.49/1000
- 最適: 成熟した信頼できるプロバイダーを必要とするプロジェクト

注意: これらのサービスはサードパーティの推奨です。latebraは特定のプロバイダーを推奨するものではありません。予算、ボリューム、地域要件に基づいて選択してください。記載されているすべてのサービスはオプションです -- latebraはプロキシやCAPTCHAソルバーが設定されていなくても動作します。

---

## 環境変数

- `CAPSOLVER_API_KEY` -- CAPTCHA解決用のCapsolver APIキー
- `TWOCAPTCHA_API_KEY` -- CAPTCHA解決用の2Captcha APIキー
- `PROXY_LIST` -- カンマ区切りのプロキシリスト（形式: `protocol://user:pass@host:port`）

---

## クレジット

**作者: Evandro Fonseca Junior**

---

## ライセンス

MITライセンスの下で配布されています。詳細は[LICENSE](LICENSE)ファイルを参照してください。

---

## 参考文献

COOK, Garrett, et al. *There's a Hole in the Bucket: Large-Scale Analysis of CAPTCHA Abuse*. 2020.

VASTEL, Antoine. *Modern Fingerprinting Techniques: A Survey*. 2017.

LAPERDRIX, Pierre, et al. *Beauty and the Beast: Diverting Modern Web Browsers from Building Honest Fingerprints*. 2016.

ACAR, Gunes, et al. *The Web Never Forgets: Persistent Tracking Mechanisms in the Wild*. 2014.
