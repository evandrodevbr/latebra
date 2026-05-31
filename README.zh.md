# latebra

**具备多层规避管道的匿名网页抓取反机器人 MCP 服务器。**

latebra 将 TLS 指纹伪装、浏览器隐身、人类行为模拟、代理轮换和验证码求解整合至单一 MCP 服务器中。每一层均具备自动回退机制：若 HTTP 请求因被检测而失败，管道将升级至浏览器隐身层；若浏览器被拦截，则尝试通过无头爬虫进行内容提取——始终确保最大程度的匿名性。

---

## 管道

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

管道采用优雅降级策略：

1. **请求（Request）** -- 首先尝试使用 `curl_cffi` 和 TLS 指纹伪装发起请求
2. **浏览器（Browser）** -- 若被检测到，则启动带有隐身配置的 Playwright
3. **提取（Extraction）** -- 使用 Crawl4AI 或正则表达式作为回退方案提取内容
4. **缓存（Cache）** -- 结果存储于 SQLite 中，并支持可配置的生存时间（TTL）

辅助模块（代理、隐身、验证码）在所有层级中协同运作。

---

## 架构

```
src/latebra/
|
+-- server.py                # MCP 服务器 -- 工具: scrape, extract, health
|
+-- pipeline.py              # SmartScrapePipeline -- 回退编排器
|
+-- layers/
|   +-- request.py           # curl_cffi + TLS 指纹伪装 + 代理
|   +-- browser.py           # Playwright + 隐身初始化
|   +-- extraction.py        # Crawl4AI + 正则表达式回退 + SQLite TTL 缓存
|
+-- proxy/
|   +-- manager.py           # 代理轮换、健康检查、自动封禁
|
+-- stealth/
|   +-- fingerprint.py       # Canvas、WebGL、WebRTC 指纹伪装
|   +-- behavior.py          # 贝塞尔曲线、人类延迟、自然滚动
|
+-- captcha/
    +-- solver.py            # 2Captcha + Capsolver
```

### 执行流程

```
                  +-------------------+
                  |  MCP 客户端       |
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
                  |  回退链           |
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
                  |   SQLite 缓存     |
                  |   (TTL + 去重)    |
                  +-------------------+
```

---

## 安装

使用 pip 和 uv 安装方式需要 Python 3.12+。

### npm（推荐）

npm 包封装了 Python 服务器并自动安装所有依赖：

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

# 最小化安装（仅 MCP）
pip install -e .

# 包含浏览器支持
pip install -e ".[browser]"

# 包含提取支持
pip install -e ".[extraction]"

# 包含验证码支持
pip install -e ".[captcha]"

# 完整安装（所有模块）
pip install -e ".[all]"
```

---

## 使用方法

### 作为 MCP 服务器

```bash
latebra run
```

或直接通过 Python 运行：

```bash
python -m latebra run
```

在您的 MCP 客户端中配置（Claude Desktop、Cursor、Hermes Agent）：

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

可用工具：

- `scrape` -- 智能抓取，支持从 HTTP 到浏览器的回退
- `extract` -- 直接的结构化内容提取
- `health` -- 状态检查和匿名级别报告

### 作为 Python 库

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
        force_browser=False,     # 首先尝试 HTTP 请求
        extract_structured=True, # 使用 Crawl4AI 进行提取
    )

    print(f"状态: {result.status}")
    print(f"内容: {result.content[:500]}")
    print(f"使用的层级: {result.layer}")

asyncio.run(main())
```

---

## 已实现技术

- **TLS 指纹伪装** -- 通过 `curl_cffi` 实现 JA3/JA4 指纹冒充
- **Canvas 指纹伪装** -- Canvas 2D 渲染器中的噪声随机化
- **WebGL 指纹伪装** -- WebGL 供应商/渲染器信息伪装
- **WebRTC 泄露防护** -- 防止真实 IP 地址泄露
- **JavaScript 挑战** -- 绕过 Cloudflare、DataDome 和 Akamai 检测
- **行为模拟** -- 贝塞尔曲线鼠标移动、自然滚动、人类行为延迟
- **代理轮换** -- 自动轮换，包含健康检查和慢速代理封禁
- **CDP/DevTools 检测** -- 移除可检测的 Chrome DevTools Protocol 标志
- **速率限制绕过** -- 跨多个代理分发请求
- **蜜罐检测** -- 识别并排除陷阱链接
- **验证码求解** -- 支持 2Captcha 和 Capsolver，并可在服务之间回退
- **智能缓存** -- SQLite 缓存，支持可配置的 TTL 和去重

---

## 推荐服务

### 代理服务

精选的与 latebra 良好协作的高性价比代理服务商：

**Webshare** -- 住宅代理，赠送 10 个免费代理，数据中心套餐每月 $2.99 起。
- 链接: https://www.webshare.io
- 价格: 住宅代理 $4.50/GB 起，数据中心套餐每月 $2.99 起
- 最佳场景: 需要免费入门套餐的开发者和小型团队

**IPRoyal** -- 按量付费住宅代理，无月度承诺，提供静态住宅代理。
- 链接: https://iproyal.com
- 价格: 住宅代理 $1.75/GB 起，静态住宅代理 $2.40/代理/月起
- 最佳场景: 无需长期合同的灵活使用场景

**Bright Data** -- 最大的代理网络，拥有 7200 万以上 IP，企业级代理管理器和最佳地理覆盖范围。
- 链接: https://brightdata.com
- 价格: 住宅代理约 $5.04/GB 起
- 最佳场景: 需要最大覆盖范围和可靠性的企业级工作负载

**Smartproxy** -- 5500 万以上 IP 池，设计精良的管理面板和浏览器扩展，简化配置流程。
- 链接: https://smartproxy.com
- 价格: 住宅代理 $3/GB 起
- 最佳场景: 注重易用性和面板管理的团队

**Proxy-Cheap** -- 经济实惠的住宅和静态住宅代理，适用于中小型项目。
- 链接: https://proxy-cheap.com
- 价格: 住宅代理约 $3/GB 起
- 最佳场景: 预算有限且流量需求适中的项目

### 验证码求解服务

精选的与 latebra 良好协作的高性价比验证码求解服务：

**2Captcha** -- 最广泛的验证码类型覆盖，在 reCAPTCHA、hCaptcha 和图片验证码方面具有经过验证的可靠性。
- 链接: https://2captcha.com
- 价格: reCAPTCHA v2 $0.50/1000 起，reCAPTCHA v3 $1-$3/1000
- 最佳场景: 需要最广泛功能支持的通用求解场景

**Capsolver** -- 基于人工智能的自动求解，支持 Cloudflare Turnstile、hCaptcha 和 FunCaptcha。
- 链接: https://www.capsolver.com
- 价格: reCAPTCHA v2 约 $1/1000
- 最佳场景: 包括 Cloudflare Turnstile 在内的现代验证码类型

**Anti-Captcha** -- 定价稳定，API 文档完善，并提供用于辅助求解的浏览器扩展。
- 链接: https://anti-captcha.com
- 价格: reCAPTCHA v2 $0.50-$2/1000
- 最佳场景: 注重完善 API 文档和可预测定价的团队

**CapMonster** -- reCAPTCHA v2 具有竞争力的价格，求解速度快，并提供 Chrome 扩展。
- 链接: https://capmonster.cloud
- 价格: reCAPTCHA v2 具有竞争力的费率
- 最佳场景: 需要快速响应的高并发操作

**DeathByCaptcha** -- 自 2010 年以来成熟稳定的服务，基于 OCR 的图片验证码求解，长期可靠性有保障。
- 链接: https://www.deathbycaptcha.com
- 价格: reCAPTCHA v2 $1.49/1000
- 最佳场景: 需要成熟且久经考验的服务商的项目

注意：以上为第三方推荐服务。latebra 不对任何特定服务商予以背书。请根据您的预算、流量和地区需求进行选择。所有列出的服务均为可选项——latebra 无需配置代理或验证码求解服务即可正常工作。

---

## 环境变量

- `CAPSOLVER_API_KEY` -- 用于验证码求解的 Capsolver API 密钥
- `TWOCAPTCHA_API_KEY` -- 用于验证码求解的 2Captcha API 密钥
- `PROXY_LIST` -- 逗号分隔的代理列表（格式: `protocol://user:pass@host:port`）

---

## 致谢

**作者: Evandro Fonseca Junior**

---

## 许可证

基于 MIT 许可证分发。详情请参阅 [LICENSE](LICENSE) 文件。

---

## 参考文献

COOK, Garrett, et al. *There's a Hole in the Bucket: Large-Scale Analysis of CAPTCHA Abuse*. 2020.

VASTEL, Antoine. *Modern Fingerprinting Techniques: A Survey*. 2017.

LAPERDRIX, Pierre, et al. *Beauty and the Beast: Diverting Modern Web Browsers from Building Honest Fingerprints*. 2016.

ACAR, Gunes, et al. *The Web Never Forgets: Persistent Tracking Mechanisms in the Wild*. 2014.
