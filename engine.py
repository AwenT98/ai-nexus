import os
import sys
import time
import datetime
import json
import random
import re
import traceback

print("🔄 正在初始化 AI Nexus 引擎 (内容深度增强版)...")

# === 1. 依赖检查 ===
try:
    import requests
    import urllib3
    import xml.etree.ElementTree as ET
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    print("\n❌ 严重错误：缺少 requests 库。")
    sys.exit()

# === 2. 翻译检查 ===
try:
    from deep_translator import GoogleTranslator
    translator = GoogleTranslator(source='auto', target='zh-CN')
    TRANSLATE_AVAILABLE = True
    print("✅ 翻译服务: 在线智能翻译")
except:
    TRANSLATE_AVAILABLE = False
    print("⚠️ 翻译服务: 使用本地词典模式")

# === 3. 全局配置 ===
DATA_FILE = "data.js"
HEADERS = { 
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9"
}

def get_beijing_now():
    utc_now = datetime.datetime.utcnow()
    return utc_now + datetime.timedelta(hours=8)

class DataEngine:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.news = []
        self.ranks = {}
        self.prompts = []
        self.seen_titles = set()

    def fetch(self, url):
        try: return self.session.get(url, timeout=10, verify=False)
        except: return None

    def smart_trans(self, text):
        if not text: return ""
        text = text.strip()
        if len(text) < 5: return text
        if TRANSLATE_AVAILABLE:
            try: return translator.translate(text[:800]) # 增加翻译长度限制到800
            except: pass
        return text

    # === 🌟 核心升级：暴力抓取正文摘要 ===
    def extract_body_text(self, html):
        """当找不到 Meta 标签时，尝试提取网页正文的第一段有意义的文字"""
        # 去除 script, style 等干扰标签
        clean_html = re.sub(r'<(script|style).*?>.*?</\1>', '', html, flags=re.DOTALL)
        clean_html = re.sub(r'', '', clean_html, flags=re.DOTALL)
        # 提取所有 p 标签
        paragraphs = re.findall(r'<p.*?>(.*?)</p>', clean_html, re.DOTALL)
        
        for p in paragraphs:
            # 清除标签内的 HTML 标记
            text = re.sub(r'<.*?>', '', p).strip()
            # 如果这段话长度适中（大于50字），很可能是正文摘要
            if len(text) > 50:
                return text[:300] + "..." # 截取前300字
        return ""

    def get_smart_summary(self, url, default_title):
        """
        全方位抓取摘要：OG标签 -> Meta Description -> 正文首段
        """
        print(f"   🔍 深挖: {default_title[:15]}...", end="", flush=True)
        try:
            r = self.session.get(url, timeout=6, verify=False)
            if r.status_code != 200: 
                print(" [跳过]")
                return default_title
            
            html = r.text
            
            # 1. 优先找 og:description
            og_match = re.search(r'<meta\s+property=["\']og:description["\']\s+content=(["\'])(.*?)\1', html, re.IGNORECASE | re.DOTALL)
            if og_match and len(og_match.group(2).strip()) > 20:
                print(" [OG抓取]")
                return self.smart_trans(og_match.group(2).strip())
            
            # 2. 其次找 name="description"
            meta_match = re.search(r'<meta\s+name=["\']description["\']\s+content=(["\'])(.*?)\1', html, re.IGNORECASE | re.DOTALL)
            if meta_match and len(meta_match.group(2).strip()) > 20:
                print(" [Meta抓取]")
                return self.smart_trans(meta_match.group(2).strip())
            
            # 3. 🔥 最后大招：抓取正文第一段
            body_text = self.extract_body_text(html)
            if body_text:
                print(" [正文抓取]")
                return self.smart_trans(body_text)

            print(" [未找到]")
            return default_title
        except Exception:
            print(f" [出错]")
            return default_title

    def parse_time(self, raw, is_unix=False):
        try:
            if not raw: return get_beijing_now().strftime("%m-%d %H:%M")
            if is_unix:
                dt = datetime.datetime.utcfromtimestamp(int(raw))
            else:
                dt = datetime.datetime.strptime(raw[:19], "%Y-%m-%dT%H:%M:%S")
                if "-08:00" in raw or "-07:00" in raw: dt += datetime.timedelta(hours=16)
            cst = dt + datetime.timedelta(hours=8)
            return cst.strftime("%m-%d %H:%M")
        except: return get_beijing_now().strftime("%m-%d %H:%M")

    # === 1. 情报抓取 ===
    def run_spider(self):
        print("   └─ 正在挖掘软件情报...")
        self.news = []
        self.seen_titles.clear()
        
        # Product Hunt
        r = self.fetch("https://www.producthunt.com/feed/category/artificial-intelligence")
        if r and r.status_code == 200:
            try:
                root = ET.fromstring(r.content)
                ns = {'atom': 'http://www.w3.org/2005/Atom'}
                entries = root.findall('atom:entry', ns) or root.findall('{http://www.w3.org/2005/Atom}entry')
                for entry in entries[:15]:
                    try:
                        title = (entry.find('atom:title', ns) or entry.find('{http://www.w3.org/2005/Atom}title')).text
                        if title in self.seen_titles: continue
                        summary = (entry.find('atom:summary', ns) or entry.find('{http://www.w3.org/2005/Atom}summary')).text
                        link = (entry.find('atom:link', ns) or entry.find('{http://www.w3.org/2005/Atom}link')).attrib['href']
                        pub = (entry.find('atom:published', ns) or entry.find('{http://www.w3.org/2005/Atom}published')).text
                        
                        # 如果自带摘要太短，也尝试深挖一下
                        final_desc = summary
                        if len(summary) < 30:
                            final_desc = self.get_smart_summary(link, title)
                        else:
                            final_desc = self.smart_trans(summary)

                        self.news.append({
                            "id": str(len(self.news)), "src": "Product Hunt", "type": "APP",
                            "title": self.smart_trans(title),
                            "desc": final_desc,
                            "url": link, "time": self.parse_time(pub)
                        })
                        self.seen_titles.add(title)
                        print("📱", end="", flush=True)
                    except: continue
            except: pass

        # Hacker News
        r = self.fetch("https://hacker-news.firebaseio.co/v0/topstories.json")
        if r:
            try:
                ids = r.json()[:60]
                keys = ['Show HN', 'Launch', 'Tool', 'App', 'Open Source', 'GPT', 'LLM']
                count = 0
                for i in ids:
                    if count >= 15: break 
                    item = self.fetch(f"https://hacker-news.firebaseio.co/v0/item/{i}.json").json()
                    if not item: continue
                    t = item.get('title', '')
                    if t in self.seen_titles: continue
                    if any(k in t for k in keys):
                        url = item.get('url', f"https://news.ycombinator.com/item?id={i}")
                        # Hacker News 必须深挖，否则只有标题
                        rich_desc = self.get_smart_summary(url, t)
                        
                        self.news.append({
                            "id": str(len(self.news)), "src": "Hacker News", "type": "DEV",
                            "title": self.smart_trans(t),
                            "desc": rich_desc,
                            "url": url, "time": self.parse_time(item.get('time', 0), True)
                        })
                        self.seen_titles.add(t)
                        count += 1
                        print("💻", end="", flush=True)
            except: pass
        print("")
        if len(self.news) < 40: self.inject_filler(40 - len(self.news))

    # === 🌟 升级：深度点评备用库 ===
    # 当爬虫失败时，这些丰富的内容会顶上去
    def inject_filler(self, count):
        current_time = get_beijing_now().strftime("%m-%d %H:%M")
        # 这里的 desc 现在全是长文本
        filler_db = [
            {
                "type":"APP", "src":"OpenAI", "title":"OpenAI o1 模型预览版上线", 
                "desc":"OpenAI 发布的全新 o1 系列模型（原草莓项目），引入了‘思维链’推理技术。这意味着模型在回答问题前会像人类一样进行深思熟虑，从而在复杂的数学、编程和科学推理任务上表现出卓越的能力，准确率大幅超越 GPT-4o。",
                "url":"https://openai.com"
            },
            {
                "type":"DEV", "src":"Meta", "title":"Llama 3.2 开源多模态模型", 
                "desc":"Meta 再次震撼开源界！Llama 3.2 是首个能够同时处理图像和文本的轻量级开源模型。它包含 11B 和 90B 两个版本，甚至还有能在手机端流畅运行的 1B/3B 版本，为边缘计算和移动端 AI 应用开发打开了新的大门。",
                "url":"https://llama.meta.com"
            },
            {
                "type":"APP", "src":"Anthropic", "title":"Claude 3.5 Sonnet 重大更新", 
                "desc":"Anthropic 发布了 Claude 3.5 Sonnet 的升级版，这次更新引入了革命性的 'Computer Use' 功能，允许 AI 像人一样控制鼠标和键盘操作电脑。此外，其代码生成能力和逻辑推理速度也得到了进一步优化，是目前开发者首选的编程助手。",
                "url":"https://claude.ai"
            },
            {
                "type":"VIDEO", "src":"Runway", "title":"Gen-3 Alpha 视频生成全面开放", 
                "desc":"好莱坞级别的 AI 视频生成工具 Runway Gen-3 Alpha 现已向公众开放。它支持极其精准的运动控制（Motion Brush）和运镜指令，能够生成长达 10 秒的高清、连贯视频，光影效果和物理规律模拟几乎达到了以假乱真的地步。",
                "url":"https://runwayml.com"
            },
            {
                "type":"APP", "src":"Cursor", "title":"Cursor 编辑器推出 Composer", 
                "desc":"VS Code 的最强竞争对手 Cursor 推出了 'Composer' 功能。它允许用户在一个窗口中同时编辑多个文件，通过自然语言指令重构整个项目的代码结构。这不仅是一个代码补全工具，更像是一个能够理解整个工程架构的 AI 结对程序员。",
                "url":"https://cursor.com"
            },
            {
                "type":"IMAGE", "src":"BlackForest", "title":"Flux.1 Pro 图像模型发布", 
                "desc":"由原 Stable Diffusion 核心团队打造的 FLUX.1 横空出世。该模型在文字渲染（Text Rendering）和手指细节处理上完爆了 Midjourney v6。作为目前最强的开源生图模型，它支持本地部署，并且对提示词的语义理解达到了新的高度。",
                "url":"https://blackforestlabs.ai"
            },
            {
                "type":"APP", "src":"Google", "title":"NotebookLM 音频概览功能", 
                "desc":"Google 的 NotebookLM 增加了一个病毒式传播的功能：Audio Overview。它可以将你上传的任何 PDF、文档或链接，一键转化成一段两名 AI 主持人之间的精彩播客对话。语气自然、充满幽默感，是学习新知识的神器。",
                "url":"https://notebooklm.google.com"
            },
            {
                "type":"VIDEO", "src":"Kuaishou", "title":"可灵 AI (Kling) 网页版上线", 
                "desc":"快手团队研发的‘可灵’视频生成大模型，被誉为中国版的 Sora。它支持生成长达 2 分钟的视频（需延长），并且在人物动作幅度、吞咽食物等物理模拟上表现惊人。现在网页版已面向全球用户开放，支持图生视频和文生视频。",
                "url":"https://klingai.kuaishou.com"
            },
            {
                "type":"APP", "src":"Midjourney", "title":"Midjourney 网页编辑器公测", 
                "desc":"Midjourney 终于摆脱了 Discord！全新的网页版编辑器上线，支持局部重绘（Inpainting）、画布扩展（Outpainting）以及通过拖拽来修改图片构图。这是一个巨大的交互飞跃，让不懂代码的设计师也能轻松使用顶级 AI 绘画。",
                "url":"https://midjourney.com"
            },
            {
                "type":"APP", "src":"Perplexity", "title":"Perplexity Pro 推出深度推理", 
                "desc":"AI 搜索引擎 Perplexity 引入了 o1 级别的推理模型。当你询问复杂的学术或分析类问题时，它会进行多步骤的深度搜索和逻辑链推导，最后给出一份引用详实、逻辑严密的专业报告，而非简单的搜索摘要。",
                "url":"https://perplexity.ai"
            }
        ]
        
        # 循环填充直到满足数量
        full_filler = filler_db * 5
        added = 0
        for item in full_filler:
            if added >= count: break
            if item['title'] in self.seen_titles: continue
            self.news.append({
                "id": str(len(self.news)), "src": item['src'], "type": item['type'],
                "title": item['title'], "desc": item['desc'], "url": item['url'], "time": current_time
            })
            self.seen_titles.add(item['title'])
            added += 1

    def make_ranks(self):
        print("   └─ 生成 Top 20 深度榜单...")
        data = {
            "LLM": [("ChatGPT (GPT-4o)", "OpenAI 旗舰，综合能力全球第一，支持实时语音。", "https://chat.openai.com"), ("Claude 3.5 Sonnet", "代码编写与逻辑推理能力最强，UI 优雅。", "https://claude.ai"), ("DeepSeek-V3", "国产开源天花板，数学代码比肩 GPT-4。", "https://chat.deepseek.com"), ("Gemini 1.5 Pro", "Google 生态核心，超长上下文窗口。", "https://gemini.google.com"), ("Kimi 智能助手", "月之暗面出品，长文档分析首选，中文极佳。", "https://kimi.moonshot.cn"), ("Perplexity", "AI 搜索引擎，直接给出精准答案与引用。", "https://perplexity.ai"), ("Llama 3.1", "Meta 开源巨无霸，当前开源界的最强基石。", "https://llama.meta.com"), ("Qwen 2.5", "阿里出品，全能型开源模型，多语言能力卓越。", "https://tongyi.aliyun.com"), ("Mistral Large", "欧洲最强模型，逻辑严密，适合企业部署。", "https://mistral.ai"), ("Grok-2", "X (推特) 旗下，接入实时社交数据。", "https://x.ai"), ("Doubao", "字节跳动出品，响应极快，语音流畅。", "https://www.doubao.com"), ("GLM-4", "智谱 AI 旗舰，工具调用能力强。", "https://chatglm.cn"), ("Yi-Large", "零一万物出品，全球竞技场前列。", "https://lingyiwanwu.com"), ("MiniMax", "拟人交互最强，语气最像真人。", "https://minimaxi.com"), ("Command R+", "专为 RAG (检索增强) 设计的企业模型。", "https://cohere.com"), ("Copilot", "集成于 Office 的办公助手。", "https://copilot.microsoft.com"), ("HuggingChat", "免费使用多种开源模型。", "https://huggingface.co/chat"), ("Poe", "聚合所有主流大模型。", "https://poe.com"), ("Ernie", "国内知识库覆盖最全。", "https://yiyan.baidu.com"), ("Pi", "主打高情商陪伴聊天。", "https://pi.ai")],
            "Image": [("Midjourney v6", "艺术绘图王者，审美无可匹敌。", "https://midjourney.com"), ("Flux.1 Pro", "最强开源生图，手指/文字渲染极佳。", "https://blackforestlabs.ai"), ("Stable Diffusion", "本地部署必备，插件生态丰富。", "https://stability.ai"), ("DALL·E 3", "语义理解最强，集成于 GPT。", "https://openai.com/dall-e-3"), ("Civitai", "全球最大模型与 LoRA 下载站。", "https://civitai.com"), ("LiblibAI", "国内最大 AI 绘画社区。", "https://www.liblib.art"), ("Leonardo.ai", "专注游戏资产生成。", "https://leonardo.ai"), ("InstantID", "保持人脸一致性最好的项目。", "https://github.com/InstantID/InstantID"), ("Freepik AI", "实时绘图，设计师灵感库。", "https://www.freepik.com/ai"), ("Ideogram 2.0", "图片生成文字效果最好。", "https://ideogram.ai"), ("Krea AI", "实时画布，画哪里生成哪里。", "https://krea.ai"), ("Firefly", "版权合规，适合商业设计。", "https://firefly.adobe.com"), ("Magnific", "图片无损放大与细节增强。", "https://magnific.ai"), ("Tripo SR", "图片转 3D 模型。", "https://www.tripo3d.ai"), ("ControlNet", "SD 核心插件，精准控制构图。", "https://github.com/lllyasviel/ControlNet"), ("SeaArt", "体验接近原生 SD 的在线工具。", "https://www.seaart.ai"), ("Tensor.art", "在线运行模型，免费额度大。", "https://tensor.art"), ("Clipdrop", "移除背景/打光工具箱。", "https://clipdrop.co"), ("Stylar", "图层控制精准的设计工具。", "https://www.dzine.ai"), ("ComfyUI", "节点式工作流，探索上限。", "https://github.com/comfyanonymous/ComfyUI")],
            "Video": [("Runway Gen-3", "视频生成行业标准，运镜控制。", "https://runwayml.com"), ("Kling AI", "生成时长最长，物理模拟真实。", "https://klingai.kuaishou.com"), ("Luma Dream", "生成极快，免费额度大方。", "https://lumalabs.ai"), ("Hailuo", "视频动态幅度大，视觉冲击强。", "https://hailuoai.com/video"), ("Vidu", "一键生成，人物一致性好。", "https://www.vidu.studio"), ("Sora", "OpenAI 期货，定义行业上限。", "https://openai.com/sora"), ("HeyGen", "数字人播报王者，口型同步。", "https://www.heygen.com"), ("Pika Art", "动画风格，局部重绘功能。", "https://pika.art"), ("Hedra", "专注人物对话，表情细腻。", "https://www.hedra.com"), ("Viggle", "让静态角色跳舞。", "https://viggle.ai"), ("AnimateDiff", "让静态图动起来的 SD 插件。", "https://github.com/guoyww/AnimateDiff"), ("Suno", "音乐生成，顺带生成 MV。", "https://suno.com"), ("Udio", "音质更 Hi-Fi 的音乐 AI。", "https://www.udio.com"), ("ElevenLabs", "全球最强 AI 配音。", "https://elevenlabs.io"), ("Sync Labs", "专业口型同步。", "https://synclabs.so"), ("D-ID", "老牌照片说话工具。", "https://www.d-id.com"), ("Synthesia", "企业级数字人演示。", "https://www.synthesia.io"), ("Descript", "像编辑文档一样编辑视频。", "https://www.descript.com"), ("OpusClip", "长视频自动剪辑成短视频。", "https://www.opus.pro"), ("Kaiber", "风格化视频转绘。", "https://kaiber.ai")],
            "Dev": [("Cursor", "AI 原生编辑器，全库理解。", "https://cursor.com"), ("GitHub Copilot", "开发者必备代码补全。", "https://github.com/features/copilot"), ("v0.dev", "文字生成 React 界面。", "https://v0.dev"), ("Replit", "全自动构建 Web 应用。", "https://replit.com"), ("Hugging Face", "全球开源模型托管中心。", "https://huggingface.co"), ("LangChain", "LLM 应用开发框架。", "https://www.langchain.com"), ("Ollama", "本地运行大模型工具。", "https://ollama.com"), ("Supermaven", "超长记忆代码补全，速度快。", "https://supermaven.com"), ("Codeium", "免费强大的代码补全。", "https://codeium.com"), ("Devin", "全自动 AI 软件工程师。", "https://www.cognition-labs.com/devin"), ("Gradio", "Python 构建 AI 演示界面。", "https://www.gradio.app"), ("Streamlit", "数据仪表盘开发框架。", "https://streamlit.io"), ("Dify", "可视化 LLM 应用编排。", "https://dify.ai"), ("Coze", "零代码 AI Bot 搭建。", "https://www.coze.com"), ("Pinecone", "AI 向量数据库。", "https://www.pinecone.io"), ("Vercel", "前端托管，支持 AI 应用。", "https://vercel.com"), ("Tabnine", "私有化代码补全。", "https://www.tabnine.com"), ("Amazon Q", "AWS 开发者助手。", "https://aws.amazon.com/q/developer/"), ("W&B", "模型训练监控平台。", "https://wandb.ai"), ("LlamaIndex", "LLM 数据连接框架。", "https://www.llamaindex.ai")]
        }
        self.ranks = {}
        for cat, items in data.items():
            lst = []
            for i, (name, desc, url) in enumerate(items):
                score = 99.9 - (i * 0.5) + random.uniform(-0.1, 0.1)
                lst.append({"rank": i+1, "name": name, "desc": desc, "url": url, "score": f"{score:.1f}"})
            self.ranks[cat] = lst

    def make_prompts(self):
        print("   └─ 构建 AI 万能公式库...")
        self.prompts = [
            {"tag": "万能通用", "title": "RTF 标准提问法", "content": "[角色 Role]: 你是资深产品经理\n[任务 Task]: 请分析这份竞品报告\n[格式 Format]: 输出为带图表的 Markdown 格式", "desc": "最基础也最有效的结构：指定角色、明确任务、规定格式。"},
            {"tag": "复杂任务", "title": "BROKE 深度思考法", "content": "[背景 Background]: 我们正在开发一款AI应用...\n[角色 Role]: 你是首席架构师\n[目标 Objectives]: 设计后端架构\n[关键结果 Key Results]: 高并发、低延迟\n[演变 Evolve]: 如果用户量翻倍，架构如何调整？", "desc": "适用于需要深度推理和多步规划的复杂任务。"},
            {"tag": "精准控制", "title": "C.R.E.A.T.E 框架", "content": "[Context]: 上下文背景\n[Role]: 设定AI身份\n[Explicit]: 明确具体的限制条件\n[Action]: 需要执行的动作\n[Tone]: 语调（专业/幽默/严肃）\n[Example]: 给出一个参考范例", "desc": "目前公认生成质量最高的精细化控制框架。"},
            {"tag": "Video Gen", "title": "Runway/Sora 电影级公式", "content": "[主体描述] + [环境背景] + [摄影机运动 Camera Movement] + [光线/氛围] + [风格 Style]\n例如: A wide shot of a cyberpunk city street at night, neon reflection on wet ground, drone camera slowly flying forward, cinematic lighting, film grain.", "desc": "生成高质量视频的核心要素：运镜、光影与风格。"},
            {"tag": "Video Gen", "title": "数字人口播公式 (HeyGen)", "content": "[角色形象]: 穿着西装的专业新闻主播\n[背景]: 现代化的演播室大屏幕\n[表情/动作]: 面带微笑，手势自然，眼神注视镜头\n[脚本内容]: (粘贴你的台词)", "desc": "用于生成高质量 AI 数字人视频的脚本结构。"},
            {"tag": "Midjourney", "title": "MJ 摄影写实公式", "content": "/imagine prompt: [主体描述] + [环境背景] + [摄影角度/镜头] + [光线条件] + [相机型号/胶片类型] --ar 16:9 --v 6.0 --style raw", "desc": "生成照片级逼真图像的黄金公式。"},
            {"tag": "Stable Diff", "title": "SD 正负向起手式", "content": "Positive: (masterpiece, best quality:1.2), [Subject], [Style Tags], 4k, 8k\nNegative: (worst quality, low quality:1.4), bad anatomy, watermark, text", "desc": "Stable Diffusion 必备的起手质量控制词。"},
            {"tag": "Coding", "title": "代码专家 Debug", "content": "你是一个 [语言] 专家。请分析以下代码：\n1. 解释这段代码的功能\n2. 指出潜在的 Bug 或性能瓶颈\n3. 给出优化后的代码并添加注释\n[粘贴代码]", "desc": "让 AI 成为你的结对编程导师。"},
            {"tag": "Academic", "title": "论文润色 (降重)", "content": "请作为[学科]领域的审稿人，对以下段落进行润色。\n要求：保持原意，提升学术性，使用更专业的词汇，调整句式结构以降低查重率。", "desc": "学术论文投稿前的最后优化。"},
            {"tag": "Marketing", "title": "小红书爆款公式", "content": "[标题]: 包含emoji，制造悬念/焦虑/惊喜\n[正文]: 痛点场景 + 解决方案 + 情绪价值\n[结尾]: 引导互动 (点赞/收藏)\n[标签]: #热门话题", "desc": "符合算法推荐逻辑的社交媒体文案结构。"},
            {"tag": "Business", "title": "SWOT 战略分析", "content": "请对 [公司/产品] 进行 SWOT 分析：\nStrengths (优势)\nWeaknesses (劣势)\nOpportunities (机会)\nThreats (威胁)\n并基于分析给出3条战略建议。", "desc": "商业计划书必备的分析框架。"},
            {"tag": "Learning", "title": "费曼学习法", "content": "请用“费曼技巧”给我讲解 [复杂概念]。\n要求：用像给12岁孩子讲故事一样的简单语言，使用类比，不要使用行话。", "desc": "快速搞懂一个陌生领域的最佳捷径。"}
        ]

    def save(self):
        final_data = {'news': self.news, 'ranks': self.ranks, 'prompts': self.prompts}
        js = f"window.AI_DATA = {json.dumps(final_data, ensure_ascii=False, indent=2)};"
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f: f.write(js)
            print(f"✅ [{get_beijing_now().strftime('%m-%d %H:%M')}] 数据更新完成 (新闻:{len(self.news)}, 提示词:{len(self.prompts)})")
        except PermissionError:
            print("❌ 写入失败：文件被占用，请关闭正在打开 data.js 的程序。")

if __name__ == "__main__":
    try:
        e = DataEngine()
        e.run_spider()
        e.make_ranks()
        e.make_prompts()
        e.save()
    except Exception as e:
        print(f"出错: {e}")
        traceback.print_exc()
    print("✨ 脚本运行结束，3秒后退出...")
