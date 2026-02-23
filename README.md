# lanzouyunDownloader
# 蓝奏云单文件链接批量下载器 (Playwright版)

https://img.shields.io/badge/python-3.7+-blue.svg
https://img.shields.io/badge/playwright-1.40+-green
https://img.shields.io/badge/License-MIT-yellow.svg

一个基于 **Playwright** 的自动化脚本，用于批量下载蓝奏云（lanzou）的单文件分享链接。它模拟真实浏览器操作，能有效绕过常见的反爬机制，稳定下载大量文件。

## ✨ 功能特点

- ✅ **批量下载** – 支持从文本文件中读取大量蓝奏云链接，自动逐个下载。
- ✅ **并发控制** – 可设置同时处理的链接数，平衡速度与稳定性。
- ✅ **自动重试** – 下载失败时自动重试（可配置重试次数），避免临时网络问题。
- ✅ **随机延时** – 每个链接处理前随机等待一段时间，模拟人类操作，降低被封风险。
- ✅ **断点续传** – 已成功下载的链接会被记录，下次运行自动跳过，避免重复下载。
- ✅ **失败记录** – 最终失败的链接单独保存，便于后续排查或重试。
- ✅ **文件名冲突处理** – 如果多个链接下载的文件名相同，会自动添加数字后缀（如 `文件_1.pdf`），避免覆盖。
- ✅ **详细日志** – 运行日志同时输出到控制台和文件，方便追踪问题。
- ✅ **密码支持** – 链接需要密码时，可在链接文件中一并提供（格式：`链接,密码`）。

## 🛠 环境要求

- Python 3.7 或更高版本
- 操作系统：Windows / macOS / Linux（均已测试）

## 📦 安装

1. **克隆或下载本项目**

   bash

   ```
   git clone https://github.com/yourname/lanzou-batch-downloader.git
   cd lanzou-batch-downloader
   ```

   

2. **安装 Python 依赖**

   bash

   ```
   pip install playwright tqdm
   ```

   

3. **安装 Playwright 浏览器内核**

   bash

   ```
   playwright install chromium
   ```

   

## 🚀 快速开始

### 1. 准备链接文件

创建一个文本文件（例如 `lanzou_links.txt`），每行一个蓝奏云分享链接。
如果需要密码，在链接后加英文逗号及密码：

text

```
# 无密码示例
https://lazymans.lanzoue.com/i3hMK3hn4qze
# 有密码示例
https://lanzoue.com/xxxxx,1234
```



### 2. 配置脚本（可选）

打开 `lanzou_batch_playwright.py`，在开头的“配置区域”按需调整参数：

python

```
LINKS_FILE = "lanzou_links.txt"      # 链接文件路径
DOWNLOAD_DIR = "./downloads"          # 下载保存目录
CONCURRENCY = 3                        # 并发数（同时打开的页面数）
MAX_RETRIES = 2                         # 每个链接失败重试次数
DELAY_BETWEEN_LINKS = (2, 5)            # 随机延时范围（秒）
HEADLESS = False                        # 是否隐藏浏览器窗口（True为无头模式）
```



### 3. 运行脚本

bash

```
python lanzou_batch_playwright.py
```



### 4. 查看结果

- 成功下载的文件保存在 `./downloads` 文件夹。
- 已成功处理的链接记录在 `processed.txt`（断点续信用）。
- 最终失败的链接记录在 `failed.txt`。
- 运行日志保存在 `downloader.log`。

## ⚙️ 配置参数详解

| 参数                  | 说明                                      | 建议值                            |
| :-------------------- | :---------------------------------------- | :-------------------------------- |
| `LINKS_FILE`          | 链接文件路径                              | 默认 `lanzou_links.txt`           |
| `DOWNLOAD_DIR`        | 下载目录                                  | 默认 `./downloads`                |
| `PROCESSED_FILE`      | 成功记录文件                              | 默认 `processed.txt`              |
| `FAILED_FILE`         | 失败记录文件                              | 默认 `failed.txt`                 |
| `CONCURRENCY`         | 同时处理的链接数（即并发页面数）          | 1~5，过大易触发反爬               |
| `MAX_RETRIES`         | 失败重试次数                              | 2~3                               |
| `DELAY_BETWEEN_LINKS` | 每个链接处理前的随机等待时间（秒）        | `(2, 5)` 或更宽松                 |
| `HEADLESS`            | 是否无头模式（`True` 则浏览器不显示界面） | 调试用 `False`，稳定后可设 `True` |
| `SAVE_HTML`           | 是否保存每个页面的HTML源码（用于调试）    | 大量下载建议 `False`              |
| `LOG_LEVEL`           | 日志级别                                  | `logging.INFO`                    |

## 🔍 工作原理

1. **读取链接** – 从文本文件加载所有待下载链接，并过滤掉已成功处理的记录。
2. **并发控制** – 使用 `asyncio.Semaphore` 限制同时运行的页面数量。
3. **模拟浏览器** – 每个链接启动一个 Playwright 页面，访问蓝奏云分享页。
4. **处理密码（如有）** – 检测页面中是否有密码输入框，自动填写并提交。
5. **定位 iframe** – 蓝奏云下载按钮位于一个 `iframe.ifr2` 内，脚本会等待 iframe 加载并切换到内部。
6. **点击下载** – 在 iframe 中寻找下载链接（支持多种文字和属性），触发下载。
7. **保存文件** – 监听浏览器下载事件，将文件保存到指定目录；若文件名冲突，自动添加序号。
8. **记录状态** – 成功则写入 `processed.txt`，最终失败则写入 `failed.txt`。

## ⚠️ 注意事项

- **蓝奏云域名变化** – 蓝奏云经常更换域名（如 `lanzous` → `lanzoux` → `lanzoue`），若链接无法访问，请检查域名是否正确。
- **下载按钮选择器** – 脚本中预设的下载按钮选择器基于常见页面结构。若蓝奏云改版导致无法定位，可手动调整 `process_single_link` 函数中的 `wait_for_selector` 参数。
- **请求频率** – 并发数不宜过大，建议 1~3；延时设置宽松一些，避免被服务器封 IP。
- **文件大小限制** – 蓝奏云单文件最大 100MB，本脚本适用于此类小文件批量下载。
- **网络环境** – 部分网络可能需要科学上网才能正常访问蓝奏云。

## 📝 日志示例

text

```
2026-02-23 12:30:45 - INFO - 共读取到 120 个链接
2026-02-23 12:30:45 - INFO - 已从记录中跳过 5 个已下载链接
2026-02-23 12:30:45 - INFO - 剩余待处理链接: 115
2026-02-23 12:30:48 - INFO - ✅ 下载成功: 260130《马》.pdf
2026-02-23 12:30:51 - WARNING - ❌ 尝试 1/3 失败: https://lazymans.lanzoue.com/xxx - Timeout
2026-02-23 12:30:56 - INFO - ✅ 下载成功: 260130文.pdf
...
2026-02-23 12:45:10 - INFO - 🎉 批量下载完成！成功: 114, 失败: 1
```



## 🤝 贡献

欢迎提交 Issue 或 Pull Request 来改进脚本。如果你发现蓝奏云页面结构更新导致脚本失效，请及时反馈。

## 📄 许可证

[MIT License](https://license/)

------

**免责声明**：本脚本仅供学习和研究使用，请勿滥用。下载他人分享的文件请遵守相关法律法规及分享者的意愿。
