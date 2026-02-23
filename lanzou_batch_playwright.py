#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
蓝奏云单文件链接批量下载V1.0
支持：并发控制、自动重试、随机延时、进度条、断点续传、失败记录、文件名防冲突
"""

import asyncio
import os
import random
import logging
from typing import List, Tuple

from tqdm import tqdm
from playwright.async_api import async_playwright, BrowserContext

# ==================== 配置区域 ====================
LINKS_FILE = "lanzou_links.txt"          # 输入文件：每行一个链接，带密码用逗号分隔，例如 https://xxx,1234
DOWNLOAD_DIR = os.path.abspath("./downloads")  # 下载保存目录
PROCESSED_FILE = "processed.txt"         # 已成功处理的链接记录（断点续传）
FAILED_FILE = "failed.txt"               # 最终失败的链接记录

# 并发与延时控制
CONCURRENCY = 3                           # 同时处理的链接数（建议1-5）
MAX_RETRIES = 2                            # 每个链接失败重试次数
DELAY_BETWEEN_LINKS = (2, 5)                # 随机延时范围（秒）

# 调试与可视化
HEADLESS = False                           # 是否无头模式（False可观察浏览器操作）
SAVE_HTML = False                           # 是否保存每个页面的HTML（调试用，大量下载建议False）
LOG_LEVEL = logging.INFO                    # 日志级别

# ==================================================

# 初始化文件夹
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
if SAVE_HTML:
    os.makedirs("page_html", exist_ok=True)

# 配置日志
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("downloader.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def get_unique_filepath(directory: str, filename: str) -> str:
    """
    如果 filename 在 directory 中已存在，则自动添加数字序号返回新路径
    例如：文件.pdf -> 文件_1.pdf -> 文件_2.pdf
    """
    base, ext = os.path.splitext(filename)
    counter = 1
    filepath = os.path.join(directory, filename)
    while os.path.exists(filepath):
        new_filename = f"{base}_{counter}{ext}"
        filepath = os.path.join(directory, new_filename)
        counter += 1
    return filepath

def read_links() -> List[Tuple[str, str]]:
    """读取链接文件，返回列表 [(url, password), ...]"""
    links = []
    if not os.path.exists(LINKS_FILE):
        logging.error(f"链接文件 {LINKS_FILE} 不存在！")
        return links
    with open(LINKS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(",")
            url = parts[0].strip()
            pwd = parts[1].strip() if len(parts) > 1 else ""
            links.append((url, pwd))
    logging.info(f"共读取到 {len(links)} 个链接")
    return links

def load_processed() -> set:
    """加载已成功处理的链接（去重）"""
    processed = set()
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE, "r", encoding="utf-8") as f:
            processed = {line.strip() for line in f if line.strip()}
        logging.info(f"已从记录中跳过 {len(processed)} 个已下载链接")
    return processed

def save_processed(url: str):
    """记录成功处理的链接"""
    with open(PROCESSED_FILE, "a", encoding="utf-8") as f:
        f.write(url + "\n")

def save_failed(url: str, password: str):
    """记录最终失败的链接"""
    with open(FAILED_FILE, "a", encoding="utf-8") as f:
        if password:
            f.write(f"{url},{password}\n")
        else:
            f.write(f"{url}\n")

async def process_single_link(link_info: Tuple[str, str], context: BrowserContext, pbar: tqdm) -> bool:
    """
    处理单个链接（含重试逻辑）
    返回 True 表示成功，False 表示最终失败
    """
    url, password = link_info
    for attempt in range(MAX_RETRIES + 1):
        page = None
        try:
            # 随机延时（首次尝试也延时，避免请求过快）
            if attempt == 0:
                delay = random.uniform(*DELAY_BETWEEN_LINKS)
                await asyncio.sleep(delay)
            else:
                # 重试前等待更长时间
                await asyncio.sleep(random.uniform(5, 10))

            logging.debug(f"开始处理: {url} (尝试 {attempt+1}/{MAX_RETRIES+1})")

            # 创建新页面
            page = await context.new_page()
            page.set_default_timeout(60000)

            # 访问链接
            await page.goto(url, wait_until="networkidle")
            await page.wait_for_timeout(3000)

            # 如果有密码，尝试输入（主页面可能没有密码框，忽略异常）
            if password:
                try:
                    pwd_input = await page.wait_for_selector('input[type="password"]', timeout=5000)
                    await pwd_input.fill(password)
                    submit_btn = await page.wait_for_selector(
                        'button:has-text("确 定"), button:has-text("提取文件"), input[type="submit"]',
                        timeout=5000
                    )
                    await submit_btn.click()
                    await page.wait_for_timeout(2000)
                except Exception:
                    logging.debug("主页面无密码框或密码错误，忽略")

            # 等待 iframe 并切换到内部
            iframe_element = await page.wait_for_selector('iframe.ifr2', timeout=30000)
            frame = await iframe_element.content_frame()
            if not frame:
                raise Exception("无法获取 iframe 内容")
            await frame.wait_for_load_state("networkidle")

            # 在 iframe 中寻找下载链接（常用选择器）
            download_link = await frame.wait_for_selector(
                'a:has-text("普通下载"), a:has-text("点击下载"), a.download-btn, a[href*="file"], a[href*="lanrar"]',
                timeout=30000
            )

            # 监听下载并点击
            async with page.expect_download() as download_info:
                await download_link.click()
            download = await download_info.value

            # 生成唯一文件名并保存
            raw_filename = download.suggested_filename
            # 清理文件名中的非法字符
            clean_filename = "".join(c for c in raw_filename if c not in r'\/:*?"<>|')
            filepath = get_unique_filepath(DOWNLOAD_DIR, clean_filename)
            await download.save_as(filepath)
            logging.info(f"✅ 下载成功: {os.path.basename(filepath)}")

            # 记录成功
            save_processed(url)
            pbar.update(1)
            return True

        except Exception as e:
            logging.warning(f"❌ 尝试 {attempt+1}/{MAX_RETRIES+1} 失败: {url} - {str(e)[:100]}")
            if attempt == MAX_RETRIES:  # 最后一次尝试失败
                save_failed(url, password)
                pbar.update(1)
                return False
            # 继续下一次重试
        finally:
            if page:
                await page.close()

    return False  # 不会执行到这里

async def main():
    # 读取链接
    all_links = read_links()
    if not all_links:
        return

    # 加载已处理记录，过滤掉已成功的
    processed = load_processed()
    remaining = [link for link in all_links if link[0] not in processed]
    logging.info(f"剩余待处理链接: {len(remaining)}")

    if not remaining:
        logging.info("所有链接均已下载完成！")
        return

    # 初始化进度条
    pbar = tqdm(total=len(remaining), desc="总体进度", unit="个")

    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(
            headless=HEADLESS,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context(
            accept_downloads=True,
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        # 并发控制：使用 Semaphore
        semaphore = asyncio.Semaphore(CONCURRENCY)

        async def worker(link):
            async with semaphore:
                return await process_single_link(link, context, pbar)

        # 创建所有任务
        tasks = [worker(link) for link in remaining]
        results = await asyncio.gather(*tasks)

        await browser.close()

    # 统计结果
    success = sum(results)
    failed = len(results) - success
    logging.info(f"🎉 批量下载完成！成功: {success}, 失败: {failed}")
    if failed:
        logging.info(f"失败链接已记录到 {FAILED_FILE}")

if __name__ == "__main__":
    asyncio.run(main())