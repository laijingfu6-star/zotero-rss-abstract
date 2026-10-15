# Zotero 自动补全摘要 RSS

此项目从 Science RSS 获取文章，以 DOI 查询 Crossref 和 OpenAlex 可公开读取的摘要，在新 RSS 的 `description` 字段中放置可用的摘要。**有些文章无公开摘要，不保证 100% 补齐；遇到被限制的接口时也可能只能保留原始简介。**

## 一次性部署（无需电脑常开）

1. 登录 GitHub，创建一个 **Public** 仓库，建议名为 `zotero-rss-abstract`，默认分支 `main`。
2. 将这个压缩包中的所有文件和 `.github/workflows/update.yml` 按原有目录结构上传到仓库。GitHub 网页上传时请确认隐藏文件夹 `.github` 也被保留（直接 Git 上传更稳妥）。
3. 仓库 **Settings → Pages → Build and deployment → Source → GitHub Actions**。
4. 打开 **Actions → Update and publish RSS → Run workflow**，等待 build/deploy 成功。
5. 浏览器打开 `https://你的GitHub用户名.github.io/zotero-rss-abstract/science.xml`；应出现 RSS XML。
6. Zotero：文件 → 新建文献库 → 新建订阅 → 从 URL，粘贴以上 **自己的** RSS URL。

GitHub Actions 约每 6 小时更新一次，但定时任务可能有延迟。首次执行和修改代码需要先运行成功才能在 Pages 上查看新订阅。

## 增加其他期刊

编辑 `feeds.json`，每一个 RSS 源添加 `{ "name": "Journal", "url": "真实的期刊RSS链接", "file": "journal.xml", "max_items": 40 }`。`file` 要使用不同的英文文件名。请先在浏览器确认 RSS 源可访问。

## 重要限制

- 输出 RSS 只补充可从 Crossref / OpenAlex 获得的摘要。不绕过付费墙、不抓取全文。
- 遇到没有 DOI 的条目（新闻、评论等）时，保留 RSS 原始内容。
- 旧 Science 条目可能在 Zotero 中重复出现。订阅新的增强版后可以取消原订阅。
- GitHub 仓库及生成 RSS 均为公开可访问，不要放入私密数据。
- 如果 OpenAlex 要求 API key，请在仓库 Settings → Secrets and variables → Actions 中创建 `OPENALEX_API_KEY`；没有该值也能尝试 Crossref。
- **故障检查**：Actions 日志里的 `complete abstract candidates` 表示本次获取到的可用摘要数。如果为 0，请检查 Crossref/OpenAlex 可访问性及源文章 DOI。
