import os
import sys
import time
import datetime
import json
import random
import re
import traceback

print("🔄 正在初始化 AI Nexus 引擎 (智能摘要增强版)...")

# === 1. 依赖检查 ===
try:
    import requests
    import urllib3
    import xml.etree.ElementTree as ET
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    print("\n❌ 严重错误：缺少 requests 库。")
    print("   请在窗口运行: pip install requests")
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
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
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
        try: return self.session.get(url, timeout=10, verify=False) # 缩短超时防止卡死
        except: return None

    def smart_trans(self, text):
        if not text: return ""
        text = text.strip()
        if TRANSLATE_AVAILABLE:
            try: return translator.translate(text[:500])
            except: pass
        
        repls = {
            "AI ": "AI ", "Generator": "生成器", "Assistant": "助手", "Video": "视频",
            "Image": "图像", "Text": "文本", "Tool": "工具", "Launch": "发布", 
            "GPT": "GPT", "Code": "代码", "Create": "创建", "Design": "设计",
            "Free": "免费", "Agent": "智能体", "Open Source": "开源", "Library": "库"
        }
        for k, v in repls.items():
            text = re.sub(k, v, text, flags=re.IGNORECASE)
        return text

    # === 🌟 核心升级：智能提取网页摘要 ===
    def get_smart_summary(self, url, default_title):
        """
        访问目标网页，尝试提取 <meta name="description"> 或 og:description
        """
        print(f"   🔍 正在深入抓取摘要: {default_title[:10]}...", end="", flush=True)
        try:
            r = self.session.get(url, timeout=5, verify=False)
            if r.status_code != 200: 
                print(" [跳过]")
                return default_title
            
            html = r.text
            # 1. 尝试找 og:description (通常质量最高)
            og_match = re.search(r'<meta\s+property=["\']og:description["\']\s+content=["\'](.*?)["\']', html, re.IGNORECASE)
            if og_match:
                desc = og_match.group(1)
                print(" [OG成功]")
                return self.smart_trans(desc)
            
            # 2. 尝试找 name="description"
            meta_match = re.search(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']', html, re.IGNORECASE)
            if meta_match:
                desc = meta_match.group(1)
                print(" [Meta成功]")
                return self.smart_trans(desc)
            
            print(" [未找到]")
            return default_title # 没找到就返回标题
        except Exception as e:
            print(f" [出错]")
            return default_title

    def parse_time(self, raw, is_unix=False):
        try:
            if not raw: return get_beijing_now().strftime("%m-%d %H:%M")
            if is_unix:
                dt = datetime.datetime.utcfromtimestamp(int(raw))
            else:
                dt = datetime.datetime.strptime(raw[:19], "%Y-%m-%dT%H:%M:%S")
                # 简单修正时区
                if "-08:00" in raw or "-07:00" in raw: dt += datetime.timedelta(hours=16)
            
            cst = dt + datetime.timedelta(hours=8)
            return cst.strftime("%m-%d %H:%M")
        except: return get_beijing_now().strftime("%m-%d %H:%M")

    # === 情报抓取 ===
    def run_spider(self):
        print("   └─ 正在挖掘软件情报...")
        self.news = []
        self.seen_titles.clear()
        
        # 1. Product Hunt (自带摘要，无需深挖)
        r = self.fetch("https://www.producthunt.com/feed/category/artificial-intelligence")
        if r and r.status_code == 200:
            try:
                root = ET.fromstring(r.content)
                ns = {'atom': 'http://www.w3.org/2005/Atom'}
                entries = root.findall('atom:entry', ns) or root.findall('{http://www.w3.org/2005/Atom}entry')
                for entry in entries[:20]: # 限制数量防止超时
                    try:
                        title = (entry.find('atom:title', ns) or entry.find('{http://www.w3.org/2005/Atom}title')).text
                        if title in self.seen_titles: continue
                        
                        summary_node = entry.find('atom:summary', ns) or entry.find('{http://www.w3.org/2005/Atom}summary')
                        desc = summary_node.text if summary_node is not None else title
                        
                        link = (entry.find('atom:link', ns) or entry.find('{http://www.w3.org/2005/Atom}link')).attrib['href']
                        
                        # 解析时间
                        pub = entry.find('atom:published', ns) or entry.find('{http://www.w3.org/2005/Atom}published')
                        time_str = self.parse_time(pub.text if pub is not None else "")

                        self.news.append({
                            "id": str(len(self.news)), "src": "Product Hunt", "type": "APP",
                            "title": self.smart_trans(title),
                            "desc": self.smart_trans(desc), # PH自带摘要，通常够用
                            "url": link, "time": time_str
                        })
                        self.seen_titles.add(title)
                        print("📱", end="", flush=True)
                    except: continue
            except: pass

        # 2. Hacker News (只有标题，需要深挖！)
        r = self.fetch("https://hacker-news.firebaseio.co/v0/topstories.json")
        if r:
            try:
                ids = r.json()[:60] # 检查前60条
                keys = ['Show HN', 'Launch', 'Tool', 'App', 'Open Source', 'GPT', 'LLM']
                count = 0
                for i in ids:
                    if count >= 15: break # HN 限制抓 15 条，因为每条都要深挖，太慢会超时
                    item = self.fetch(f"https://hacker-news.firebaseio.co/v0/item/{i}.json").json()
                    if not item: continue
                    t = item.get('title', '')
                    if t in self.seen_titles: continue
                    if any(k in t for k in keys):
                        url = item.get('url', f"https://news.ycombinator.com/item?id={i}")
                        
                        # === 这里调用深挖函数 ===
                        # 如果没有URL（只是讨论），就用标题
                        if 'url' in item:
                            rich_desc = self.get_smart_summary(url, t)
                        else:
                            rich_desc = "Hacker News 社区深度技术讨论 (点击查看详情)"

                        self.news.append({
                            "id": str(len(self.news)), "src": "Hacker News", "type": "DEV",
                            "title": self.smart_trans(t),
                            "desc": rich_desc, # 这里现在是抓取到的详细摘要了！
                            "url": url,
                            "time": self.parse_time(item.get('time', 0), True)
                        })
                        self.seen_titles.add(t)
                        count += 1
                        print("💻", end="", flush=True)
            except: pass
        print("")
        if len(self.news) < 40: self.inject_filler(40 - len(self.news))

    def inject_filler(self, count):
        current_time = get_beijing_now().strftime("%m-%d %H:%M")
        filler_db = [
            {"type":"APP", "src":"OpenAI", "title":"OpenAI o1 预览版上线", "desc":"具有极强推理能力的全新模型，擅长解决复杂数学和编程问题。", "url":"https://openai.com"},
            {"type":"DEV", "src":"Meta", "title":"Llama 3.2 开源发布", "desc":"可以在移动设备上运行的轻量级多模态模型。", "url":"https://llama.meta.com"},
            {"type":"APP", "src":"Anthropic", "title":"Claude 3.5 Sonnet 更新", "desc":"代码能力进一步增强，引入 Artifacts 实时预览功能。", "url":"https://claude.ai"},
            {"type":"VIDEO", "src":"Runway", "title":"Gen-3 Alpha 视频生成开放", "desc":"好莱坞级别的视频生成模型，支持精准的运镜控制。", "url":"https://runwayml.com"},
            {"type":"APP", "src":"Cursor", "title":"Cursor 编辑器 Composer", "desc":"允许在一个窗口同时编辑多个文件，编程效率革命。", "url":"https://cursor.com"},
            {"type":"IMAGE", "src":"BlackForest", "title":"Flux.1 Pro 图像模型发布", "desc":"目前开源界最强的生图模型，文字渲染能力极佳。", "url":"https://blackforestlabs.ai"},
            {"type":"APP", "src":"Google", "title":"NotebookLM 音频概览", "desc":"将你的文档一键转化为两个 AI 主持人的播客对话。", "url":"https://notebooklm.google.com"},
            {"type":"VIDEO", "src":"Kuaishou", "title":"可灵 AI (Kling) 网页版上线", "desc":"生成时长可达 10 秒，物理规律模拟极其真实。", "url":"https://klingai.kuaishou.com"},
            {"type":"APP", "src":"Midjourney", "title":"Midjourney 网页编辑器公测", "desc":"新增局部重绘和画布扩展的 Web 端交互界面，无需 Discord。", "url":"https://midjourney.com"},
            {"type":"APP", "src":"Perplexity", "title":"Perplexity Pro 搜索升级", "desc":"引入推理模型进行深度搜索，提供更精准的学术引用。", "url":"https://perplexity.ai"},
            {"type":"VIDEO", "src":"Luma", "title":"Dream Machine 1.5 发布", "desc":"视频生成速度提升 2 倍，且质量更加稳定。", "url":"https://lumalabs.ai"},
            {"type":"APP", "src":"Suno", "title":"Suno v3.5 音乐生成更新", "desc":"支持生成 4 分钟完整歌曲，结构更像真实音乐。", "url":"https://suno.com"},
            {"type":"DEV", "src":"Mistral", "title":"Mistral Large 2 发布", "desc":"在编码和推理任务上超越了 Llama 3 405B。", "url":"https://mistral.ai"},
            {"type":"APP", "src":"Notion", "title":"Notion AI 连接其它应用", "desc":"现在可以搜索 Slack 和 Google Drive 中的内容。", "url":"https://notion.so"},
            {"type":"IMAGE", "src":"Ideogram", "title":"Ideogram 2.0 字体生成", "desc":"目前在图片中生成海报级文字效果最好的模型。", "url":"https://ideogram.ai"},
            {"type":"APP", "src":"ChatGPT", "title":"ChatGPT 高级语音模式", "desc":"实时打断、情感丰富，就像和真人打电话一样。", "url":"https://openai.com"},
            {"type":"VIDEO", "src":"HeyGen", "title":"HeyGen 互动数字人 API", "desc":"可以在 Zoom 会议中实时互动的 AI 数字分身。", "url":"https://heygen.com"},
            {"type":"APP", "src":"Zapier", "title":"Zapier Central 发布", "desc":"教 AI 机器人跨越 6000+ 应用自动执行任务。", "url":"https://zapier.com"},
            {"type":"DEV", "src":"LangChain", "title":"LangGraph 稳定版发布", "desc":"构建复杂、有状态的多智能体应用的全新框架。", "url":"https://langchain.com"},
            {"type":"IMAGE", "src":"Krea", "title":"Krea AI 实时画布更新", "desc":"画笔画哪里，AI 就实时生成哪里，延迟极低。", "url":"https://krea.ai"},
            {"type":"APP", "src":"ElevenLabs", "title":"Reader App 阅读器", "desc":"用极其逼真的 AI 语音朗读任何文章和 PDF。", "url":"https://elevenlabs.io"},
            {"type":"DEV", "src":"Vercel", "title":"v0.dev 企业版发布", "desc":"支持生成多页面应用，并导出高质量 React 代码。", "url":"https://v0.dev"},
            {"type":"APP", "src":"Figma", "title":"Figma AI 设计助手", "desc":"通过文本描述自动生成 UI 界面和图层结构。", "url":"https://figma.com"},
            {"type":"VIDEO", "src":"Pika", "title":"Pika Art 1.5 特效更新", "desc":"新增 Pikalert 等趣味特效，让视频物体甚至融化。", "url":"https://pika.art"},
            {"type":"APP", "src":"GitHub", "title":"Copilot Workspace 预览", "desc":"从 issue 到 pull request 的全自动开发环境。", "url":"https://githubnext.com"},
            {"type":"DEV", "src":"HuggingFace", "title":"LeRobot 开源机器人库", "desc":"将 AI 大模型引入实体机器人控制的开源项目。", "url":"https://github.com/huggingface/lerobot"},
            {"type":"APP", "src":"Gamma", "title":"Gamma 演示文稿生成", "desc":"现在支持导入 Word 文档并一键转换为精美 PPT。", "url":"https://gamma.app"},
            {"type":"APP", "src":"Arc", "title":"Arc 浏览器 Browse for Me", "desc":"为你浏览网页并生成摘要的 AI 搜索体验。", "url":"https://arc.net"},
            {"type":"DEV", "src":"NVIDIA", "title":"Nemotron-4 340B 开源", "desc":"英伟达发布的最强开源合成数据生成模型。", "url":"https://developer.nvidia.com"},
            {"type":"APP", "src":"Character.ai", "title":"Character.ai 通话功能", "desc":"现在可以与你创建的 AI 角色进行实时语音通话。", "url":"https://character.ai"},
            {"type":"VIDEO", "src":"Sora", "title":"Sora 更多演示视频流出", "desc":"展示了惊人的物理一致性和长视频生成能力。", "url":"https://openai.com/sora"},
            {"type":"DEV", "src":"Stability", "title":"Stable Audio Open", "desc":"用于生成简短音频样本和音效的开源模型。", "url":"https://stability.ai"},
            {"type":"APP", "src":"Microsoft", "title":"Windows Recall 功能预览", "desc":"Windows AI 能够“回忆”你在电脑上做过的任何事情。", "url":"https://microsoft.com"},
            {"type":"APP", "src":"Apple", "title":"Apple Intelligence 发布", "desc":"集成于 iOS 18 的个人智能系统，深度整合 Siri。", "url":"https://apple.com"},
            {"type":"DEV", "src":"Cohere", "title":"Aya 23 多语言模型", "desc":"支持 23 种语言的高性能开源大语言模型。", "url":"https://cohere.com"},
            {"type":"APP", "src":"Adobe", "title":"Lightroom 生成式移除", "desc":"一键移除照片中不需要的物体，效果自然。", "url":"https://adobe.com"},
            {"type":"APP", "src":"Canva", "title":"Canva Magic Studio", "desc":"全套 AI 设计工具更新，支持更多自动化排版。", "url":"https://canva.com"},
            {"type":"DEV", "src":"Groq", "title":"Groq API 速度测试", "desc":"展示了每秒 500 token 的极速推理能力。", "url":"https://groq.com"},
            {"type":"APP", "src":"Slack", "title":"Slack AI 总结功能", "desc":"自动总结频道内的长对话和未读消息。", "url":"https://slack.com"},
            {"type":"VIDEO", "src":"Vidu", "title":"Vidu 视频生成模型", "desc":"清华团队打造，中国版的 Sora，一键生成连贯视频。", "url":"https://www.vidu.studio"}
        ]
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
