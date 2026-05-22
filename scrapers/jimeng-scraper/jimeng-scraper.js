// 即梦提示词爬取脚本 v2.0
// 用法: node jimeng-scraper.js --port 9230 --output batch1.json --max 500
// 需要先启动 Chrome: chrome --remote-debugging-port=<port>
// Ctrl+C 安全退出，已采集数据不会丢失

const fs = require('fs');
const path = require('path');

// ============================================================
// 配置区
// ============================================================

function getArg(name, defaultVal) {
  const idx = process.argv.indexOf(`--${name}`);
  return idx !== -1 && process.argv[idx + 1] ? process.argv[idx + 1] : defaultVal;
}

const PORT = getArg('port', '9223');
const OUTPUT_FILE = getArg('output', 'jimeng-prompts.json');
const MAX_ITEMS = parseInt(getArg('max', '100'));
const DELAY_MIN = 800;
const DELAY_MAX = 1500;
const BATCH_SIZE = 50;
const BATCH_PAUSE = 5000;

// 健康监控参数
const HOME_URL = 'https://jimeng.jianying.com/ai-tool/home';
const STUCK_THRESHOLD = 5;
const ERROR_REFRESH_THRESHOLD = 3;
const MAX_REFRESHES = 20;          // 最大刷新次数，防止无限循环
const HEALTH_CHECK_INTERVAL = 30000;
const GOTO_TIMEOUT = 20000;
const GOTO_RETRIES = 3;            // goto 失败重试次数
const MAX_SCROLL_COUNT = 50;       // 最大滚动次数（从 20 提高到 50）

// 图片选择器 —— 多个备选，按优先级尝试
const IMAGE_SELECTORS = [
  '.cover-UJwtaY',                              // 当前类名（可能变）
  'img[class*="cover-"]',                       // 模糊匹配 cover- 开头的类
  '[class*="work-card"] img',                   // 工作卡片内的图片
  '[class*="gallery"] img',                     // 画廊图片
  '[class*="waterfall"] img',                   // 瀑布流图片
  '[class*="card"] img[src*="image"]',          // 含 image 的 src
];

// 弹窗/详情区域选择器（只用即梦实际存在的类名，避免误匹配）
const DETAIL_SELECTORS = [
  '[class*="work-detail"]',
  '[class*="detail-area"]',
  '[class*="detail-panel"]',
  '[class*="work-info"]',
];

// ============================================================
// 工具函数
// ============================================================

function randomDelay(min = DELAY_MIN, max = DELAY_MAX) {
  return new Promise(r => setTimeout(r, min + Math.random() * (max - min)));
}

function formatDuration(ms) {
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  return m > 0 ? `${m}m${s % 60}s` : `${s}s`;
}

// 安全的 JSON 追加写入 —— 直接追加，不读取整个文件
function appendToJson(filePath, entry, isFirst) {
  try {
    if (isFirst) {
      fs.writeFileSync(filePath, '[\n' + JSON.stringify(entry, null, 2), 'utf-8');
    } else {
      // 直接在文件末尾追加，不读取整个文件
      const comma = ',\n';
      const entryStr = JSON.stringify(entry, null, 2) + '\n';
      fs.appendFileSync(filePath, comma + entryStr, 'utf-8');
    }
    return true;
  } catch (err) {
    console.error('写入文件失败:', err.message);
    return false;
  }
}

// 关闭 JSON 文件（补上 ] ）
function finalizeJson(filePath) {
  try {
    const content = fs.readFileSync(filePath, 'utf-8');
    if (!content.trim().endsWith(']')) {
      fs.appendFileSync(filePath, '\n]', 'utf-8');
    }
  } catch {}
}

// ============================================================
// 页面操作封装
// ============================================================

class PageHelper {
  constructor(page) {
    this.page = page;
    this.totalRefreshes = 0;
    this.startTime = Date.now();
  }

  // 安全的 goto，带重试
  // 用 domcontentloaded 而不是 networkidle —— 即梦页面一直有网络活动，networkidle 会超时
  async safeGoto(url, options = {}) {
    for (let attempt = 1; attempt <= GOTO_RETRIES; attempt++) {
      try {
        await this.page.goto(url, {
          waitUntil: 'domcontentloaded',
          timeout: GOTO_TIMEOUT,
          ...options,
        });
        // 等待页面基本加载完成
        await randomDelay(2000, 3000);
        return true;
      } catch (err) {
        console.error(`  goto 失败 (第 ${attempt} 次): ${err.message}`);
        if (attempt < GOTO_RETRIES) {
          await randomDelay(2000, 4000);
        }
      }
    }
    console.error(`  goto 失败，已重试 ${GOTO_RETRIES} 次`);
    return false;
  }

  // 检测是否在详情页（URL 检测 + DOM 检测）
  isOnDetailPage() {
    const url = this.page.url();
    if (url.includes('/work-detail/') || url.includes('/detail')) {
      return true;
    }
    return false;
  }

  // 检测弹窗是否打开（DOM 检测）
  async isModalOpen() {
    try {
      return await this.page.evaluate((selectors) => {
        for (const sel of selectors) {
          const el = document.querySelector(sel);
          if (el && el.offsetParent !== null) return true;
          // 也检查 visibility 和 opacity
          if (el) {
            const style = window.getComputedStyle(el);
            if (style.display !== 'none' && style.visibility !== 'hidden') return true;
          }
        }
        return false;
      }, DETAIL_SELECTORS);
    } catch {
      return false;
    }
  }

  // 关闭弹窗（智能检测，按需执行）
  async closeModal() {
    try {
      // 先检测弹窗是否真的开着
      const isOpen = await this.isModalOpen();
      if (!isOpen) return; // 没开就跳过，省 3-4 秒

      // 方式1: Escape 键
      await this.page.keyboard.press('Escape');
      await randomDelay(500, 800);

      // 检查是否已关闭
      const stillOpen = await this.isModalOpen();
      if (!stillOpen) return;

      // 方式2: 点击弹窗外区域
      await this.page.evaluate(() => {
        document.elementFromPoint(10, 10)?.click();
      });
      await randomDelay(300, 500);

      // 方式3: 移除弹窗 DOM（最后手段）
      await this.page.evaluate((selectors) => {
        for (const sel of selectors) {
          const els = document.querySelectorAll(sel);
          els.forEach(el => {
            try { el.remove(); } catch {}
          });
        }
      }, DETAIL_SELECTORS);
      await randomDelay(300, 500);
    } catch {}
  }

  // 确保在首页
  async ensureOnHomePage() {
    if (this.isOnDetailPage()) {
      console.log('⚠️  检测到在详情页，返回首页...');
      const ok = await this.safeGoto(HOME_URL);
      if (ok) {
        // 等待图片加载
        try { await this.page.waitForSelector(IMAGE_SELECTORS.join(', '), { timeout: 10000 }); } catch {}
      }
      return true;
    }
    return false;
  }

  // 刷新页面恢复
  async refreshPage(reason) {
    if (this.totalRefreshes >= MAX_REFRESHES) {
      console.error(`❌ 已刷新 ${MAX_REFRESHES} 次，仍然失败，退出`);
      return false;
    }
    this.totalRefreshes++;
    console.log(`🔄 刷新页面 (${reason}), 第 ${this.totalRefreshes}/${MAX_REFRESHES} 次`);
    const ok = await this.safeGoto(HOME_URL);
    if (!ok) {
      console.error('  刷新失败，网络可能有问题');
      return false;
    }
    // 等待图片加载
    try { await this.page.waitForSelector(IMAGE_SELECTORS.join(', '), { timeout: 10000 }); } catch {}
    await randomDelay(1000, 2000);
    return true;
  }

  // 检测页面错误
  async checkPageError() {
    try {
      return await this.page.evaluate(() => {
        const body = document.body?.textContent || '';
        return body.includes('页面不存在') ||
               body.includes('加载失败') ||
               body.includes('网络错误') ||
               body.includes('出错了') ||
               body.includes('无法访问') ||
               body.includes('服务不可用');
      });
    } catch {
      return true; // evaluate 失败也算错误
    }
  }

  // 查找图片元素（多选择器）
  async findImages() {
    for (const selector of IMAGE_SELECTORS) {
      try {
        const images = await this.page.$$(selector);
        if (images.length > 0) {
          return { images, selector };
        }
      } catch {}
    }
    return { images: [], selector: null };
  }

  // 获取安全的图片 src（处理懒加载）
  async getImgSrc(imgEl) {
    try {
      const src = await imgEl.evaluate(el => {
        return el.src || el.dataset.src || el.dataset.lazySrc || el.getAttribute('data-original');
      });
      return src || null;
    } catch {
      return null;
    }
  }
}

// ============================================================
// 数据提取
// ============================================================

async function extractPromptData(page) {
  return await page.evaluate(() => {
    // 提示词：优先用精准选择器，避免遍历全部 DOM
    let prompt = null;

    // 方式1: 找 span/div 文本为"图片提示词"的元素的下一个兄弟
    const labelEls = document.querySelectorAll('span, div, p, label');
    for (const el of labelEls) {
      if (el.childNodes.length === 1 && el.textContent.trim() === '图片提示词') {
        const next = el.nextElementSibling;
        if (next) {
          prompt = next.textContent.trim();
          break;
        }
      }
    }

    // 方式2: textarea/pre
    if (!prompt) {
      const ta = document.querySelector('textarea[class*="prompt"], pre[class*="prompt"], [class*="prompt-text"]');
      if (ta) prompt = ta.textContent.trim();
    }

    // 方式3: 找包含"图片提示词"的容器，取其文本
    if (!prompt) {
      const containers = document.querySelectorAll('[class*="prompt"], [class*="desc"]');
      for (const c of containers) {
        if (c.textContent.includes('图片提示词')) {
          // 取"图片提示词"后面的文本
          const idx = c.textContent.indexOf('图片提示词');
          if (idx !== -1) {
            prompt = c.textContent.slice(idx + 5).trim();
            if (prompt) break;
          }
        }
      }
    }

    // 模型和比例
    let model = null;
    let ratio = null;

    // 从元数据区域提取（限制遍历范围）
    const metaEls = document.querySelectorAll('[class*="meta"], [class*="param"], [class*="tag"]');
    for (const el of metaEls) {
      const text = el.textContent;
      // 只处理短文本节点，避免匹配整个页面
      if (text.length > 200) continue;
      if (!model) {
        const modelMatch = text.match(/图片\s*([\d.]+\s*(?:Lite|Pro)?)/i);
        if (modelMatch) model = modelMatch[1].trim();
      }
      if (!ratio) {
        const ratioMatch = text.match(/^(\d+:\d+)$/);
        if (ratioMatch) ratio = ratioMatch[1];
      }
    }

    // 备用：从弹窗区域文本提取（不是整个 body）
    if (!model || !ratio) {
      const dialog = document.querySelector('[class*="work-detail"], [class*="detail-area"]');
      if (dialog) {
        const text = dialog.textContent;
        if (!model) {
          const m = text.match(/图片\s*([\d.]+\s*(?:Lite|Pro)?)/i);
          if (m) model = m[1].trim();
        }
        if (!ratio) {
          const r = text.match(/(\d+:\d+)/);
          if (r) ratio = r[1];
        }
      }
    }

    // 作者和日期
    let author = null;
    let date = null;
    const authorEl = document.querySelector('[class*="author"], [class*="user-name"], [class*="nickname"], [class*="creator"]');
    if (authorEl) author = authorEl.textContent.trim();
    const dateEl = document.querySelector('[class*="date"], [class*="time"], [class*="create-time"]');
    if (dateEl) {
      const d = dateEl.textContent.match(/(\d{4}-\d{2}-\d{2})/);
      if (d) date = d[1];
    }

    return { prompt, model, ratio, author, date };
  });
}

// ============================================================
// 主流程
// ============================================================

async function main() {
  let chromium;
  try {
    chromium = require('playwright').chromium;
  } catch {
    console.log('Installing playwright...');
    require('child_process').execSync('npm install playwright', { stdio: 'inherit' });
    chromium = require('playwright').chromium;
  }

  console.log(`连接 Chrome 端口 ${PORT}...`);
  let browser;
  try {
    browser = await chromium.connectOverCDP(`http://localhost:${PORT}`);
  } catch (err) {
    console.error(`无法连接 Chrome 端口 ${PORT}: ${err.message}`);
    console.error('请确认 Chrome 已启动并带 --remote-debugging-port=' + PORT);
    process.exit(1);
  }

  const context = browser.contexts()[0] || await browser.newContext();
  const page = context.pages()[0] || await context.newPage();
  const helper = new PageHelper(page);

  console.log('打开即梦首页...');
  const ok = await helper.safeGoto(HOME_URL);
  if (!ok) {
    console.error('无法打开即梦首页，检查网络');
    process.exit(1);
  }

  // 等待图片加载（domcontentloaded 后图片可能还没出来）
  try {
    await page.waitForSelector(IMAGE_SELECTORS.join(', '), { timeout: 10000 });
    console.log('页面图片已加载');
  } catch {
    console.log('⚠️  等待图片超时，继续尝试...');
  }
  await randomDelay(1000, 2000);

  // 初始化输出文件
  const outputPath = path.resolve(OUTPUT_FILE);
  const results = [];
  let scrollCount = 0;
  const seen = new Set();      // imgSrc 去重
  const seenUrls = new Set();  // 详情页 URL 去重

  // 健康监控状态
  let consecutiveErrors = 0;
  let stuckCount = 0;
  let lastResultCount = 0;
  let lastHealthCheck = Date.now();
  let currentSelector = null;
  let fileInitialized = false;

  // 优雅退出
  let interrupted = false;
  process.on('SIGINT', () => {
    if (interrupted) {
      console.log('\n强制退出');
      process.exit(1);
    }
    interrupted = true;
    console.log('\n⚠️  收到中断信号，正在安全退出...');
    console.log(`   已采集 ${results.length} 条数据`);
  });

  // 健康检查
  function healthCheck() {
    const now = Date.now();
    if (now - lastHealthCheck < HEALTH_CHECK_INTERVAL) return 'ok';
    lastHealthCheck = now;

    const elapsed = (now - helper.startTime) / 1000 / 60; // 分钟
    const speed = elapsed > 0 ? (results.length / elapsed).toFixed(1) : 0;
    const progress = results.length - lastResultCount;
    lastResultCount = results.length;

    console.log(`📊 健康检查: ${results.length}/${MAX_ITEMS} 条, 速度 ${speed} 条/分, 刷新 ${helper.totalRefreshes} 次, 错误 ${consecutiveErrors}, 选择器: ${currentSelector || '未找到'}`);

    if (progress === 0) {
      stuckCount++;
      if (stuckCount >= STUCK_THRESHOLD) {
        console.log(`⚠️  连续 ${stuckCount} 轮无新数据`);
        return 'stuck';
      }
    } else {
      stuckCount = 0;
    }
    return 'ok';
  }

  // ==================== 主循环 ====================

  while (results.length < MAX_ITEMS && !interrupted) {
    // 健康检查
    const health = healthCheck();
    if (health === 'stuck') {
      const ok = await helper.refreshPage('连续无新数据');
      if (!ok) break;
      consecutiveErrors = 0;
      stuckCount = 0;
      continue;
    }

    // 确保在首页
    const wasOnDetail = await helper.ensureOnHomePage();
    if (wasOnDetail) {
      consecutiveErrors = 0;
      continue;
    }

    // 检测页面错误
    const hasError = await helper.checkPageError();
    if (hasError) {
      consecutiveErrors++;
      console.log(`❌ 页面错误，第 ${consecutiveErrors} 次`);
      if (consecutiveErrors >= ERROR_REFRESH_THRESHOLD) {
        const ok = await helper.refreshPage('页面错误');
        if (!ok) break;
      } else {
        await helper.safeGoto(HOME_URL);
        await randomDelay(2000, 3000);
      }
      continue;
    }

    // 查找图片
    const { images, selector } = await helper.findImages();
    if (!selector) {
      console.log('⚠️  找不到任何图片选择器，可能网站改版了');
      const ok = await helper.refreshPage('选择器失效');
      if (!ok) break;
      continue;
    }
    if (currentSelector !== selector) {
      currentSelector = selector;
      console.log(`📌 使用选择器: ${selector}`);
    }

    console.log(`页面 ${images.length} 张图片, 已采集 ${results.length} 条`);
    let newInThisRound = 0;

    for (let i = 0; i < images.length && results.length < MAX_ITEMS && !interrupted; i++) {
      try {
        // 再次检查是否在首页
        if (helper.isOnDetailPage()) {
          console.log('⚠️  循环中检测到详情页，返回首页');
          await helper.safeGoto(HOME_URL);
          try { await page.waitForSelector(IMAGE_SELECTORS.join(', '), { timeout: 10000 }); } catch {}
          break;
        }

        // 获取图片 src（处理懒加载）
        const imgSrc = await helper.getImgSrc(images[i]);
        if (!imgSrc || seen.has(imgSrc)) continue;
        seen.add(imgSrc);

        // 滚动到图片位置
        await images[i].scrollIntoViewIfNeeded().catch(() => {});
        await randomDelay(500, 1000);

        const box = await images[i].boundingBox().catch(() => null);
        if (!box) continue;

        // 记录点击前的 URL
        const urlBefore = page.url();

        // 点击图片（即梦会跳转到详情页，不是弹窗）
        await images[i].click({ force: true }).catch(() => {});
        await randomDelay(1500, 2500);

        // 等待页面跳转（URL 变化）
        try {
          await page.waitForURL('**/work-detail/**', { timeout: 8000 });
        } catch {
          // 如果没跳转，可能点击失败，跳过
          console.log('  点击后未跳转，跳过');
          continue;
        }

        // 在详情页提取数据
        const data = await extractPromptData(page);
        const detailUrl = page.url();

        if (data.prompt && !seenUrls.has(detailUrl)) {
          seenUrls.add(detailUrl);
          const entry = {
            ...data,
            url: detailUrl,
            scrapedAt: new Date().toISOString(),
          };
          results.push(entry);
          newInThisRound++;
          consecutiveErrors = 0;

          // 追加写入文件
          const writeOk = appendToJson(outputPath, entry, !fileInitialized);
          if (writeOk) fileInitialized = true;

          // 计算速度
          const elapsed = (Date.now() - helper.startTime) / 1000 / 60;
          const speed = elapsed > 0 ? (results.length / elapsed).toFixed(1) : 0;
          console.log(`[${results.length}/${MAX_ITEMS}] ${speed}条/分 Model:${data.model} 长度:${data.prompt.length}`);
        } else if (!data.prompt) {
          console.log('  详情页未提取到提示词，跳过');
        }

        // 返回首页（用 safeGoto，不用 goBack）
        await helper.safeGoto(HOME_URL);

        // 等待首页图片重新加载
        try {
          await page.waitForSelector(IMAGE_SELECTORS.join(', '), { timeout: 10000 });
        } catch {
          console.log('  返回首页后图片加载超时');
        }
        await randomDelay(500, 1000);

        // 每 BATCH_SIZE 个暂停
        if (results.length % BATCH_SIZE === 0 && results.length > 0) {
          console.log(`--- 批次暂停 ${BATCH_PAUSE / 1000}s ---`);
          await randomDelay(BATCH_PAUSE, BATCH_PAUSE + 5000);
        }

      } catch (err) {
        consecutiveErrors++;
        console.error(`错误 [${i}]: ${err.message} (连续: ${consecutiveErrors})`);

        if (consecutiveErrors >= ERROR_REFRESH_THRESHOLD) {
          const ok = await helper.refreshPage('连续错误过多');
          if (!ok) { interrupted = true; break; }
          break;
        }

        // 出错时尝试返回首页
        try { await helper.safeGoto(HOME_URL); } catch {}
        await randomDelay(2000, 3000);
      }
    }

    // 滚动加载更多
    if (newInThisRound === 0 && !interrupted) {
      scrollCount++;
      if (scrollCount > MAX_SCROLL_COUNT) {
        console.log(`滚动 ${MAX_SCROLL_COUNT} 次无新内容，停止`);
        break;
      }
      console.log(`滚动加载更多 (${scrollCount}/${MAX_SCROLL_COUNT})...`);
      await page.evaluate(() => window.scrollBy(0, 800 + Math.random() * 400));
      await randomDelay(1000, 2000);
    } else {
      scrollCount = 0;
    }
  }

  // ==================== 收尾 ====================

  // 关闭 JSON 文件
  finalizeJson(outputPath);

  // 最终统计
  const elapsed = (Date.now() - helper.startTime) / 1000 / 60;
  const speed = elapsed > 0 ? (results.length / elapsed).toFixed(1) : 0;

  console.log('\n==================== 采集完成 ====================');
  console.log(`总采集: ${results.length} 条`);
  console.log(`耗时: ${formatDuration(Date.now() - helper.startTime)}`);
  console.log(`平均速度: ${speed} 条/分钟`);
  console.log(`页面刷新: ${helper.totalRefreshes} 次`);
  console.log(`输出文件: ${outputPath}`);
  if (interrupted) console.log('(用户中断)');

  // 模型分布
  const modelStats = {};
  results.forEach(r => {
    const m = r.model || 'unknown';
    modelStats[m] = (modelStats[m] || 0) + 1;
  });
  console.log('\n模型分布:');
  Object.entries(modelStats).sort((a, b) => b[1] - a[1]).forEach(([m, c]) => {
    console.log(`  图片 ${m}: ${c}`);
  });
  console.log('==================================================');

  await browser.close().catch(() => {});
}

main().catch(err => {
  console.error('致命错误:', err.message);
  process.exit(1);
});
