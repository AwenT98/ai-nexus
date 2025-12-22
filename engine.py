import os
import sys
import time
import datetime
import json
import random
import re
import traceback

print("🔄 正在初始化 AI Nexus 引擎 (真实时间版)...")

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

# === 3. 配置 ===
DATA_FILE = "data.js"
HEADERS = { 
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" 
}

# 获取当前北京时间（用于备用数据和全局更新时间）
def get_current_time_str():
    utc_now = datetime.datetime.utcnow()
    cst_time = utc_now + datetime.timedelta(hours=8)
    return cst_time.strftime("%m-%d %H:%M")

class DataEngine:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.news = []
        self.ranks = {}
        self.prompts = []
        self.seen_titles = set()

    def fetch(self, url):
        try: return self.session.get(url, timeout=15, verify=False)
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
            "Free": "免费", "Agent": "智能体", "Open Source": "开源", "Library": "库",
            "Framework": "框架", "Model": "模型", "Chat": "聊天", "Voice": "语音",
            "Synthesis": "合成", "Detection": "检测", "Studio": "工作室", "Web": "网页",
            "Browser": "浏览器", "Plugin": "插件", "Extension": "扩展", "Platform": "平台",
            "Announcing": "宣布", "Introducing": "介绍", "New": "新", "Search": "搜索"
        }
        for k, v in repls.items():
            text = re.sub(k, v, text, flags=re.IGNORECASE)
        return text

    # === 新增：时间解析工具 ===
    def parse_ph_time(self, iso_str):
        """解析 Product Hunt 的 ISO 时间并转为北京时间"""
        try:
            # 格式通常为: 2023-12-22T08:00:00-08:00 或 Z 结尾
            # 简单处理：截取前19位转时间对象，视为 UTC (PH feed 时区较乱，视为 UTC+8 修正)
            dt = datetime.datetime.strptime(iso_str[:19], "%Y-%m-%dT%H:%M:%S")
            # 假设源是 UTC，+8小时
            cst_time = dt + datetime.timedelta(hours=8)
            return cst_time.strftime("%m-%d %H:%M")
        except:
            return get_current_time_str() # 解析失败回退到当前时间

    def parse_hn_time(self, unix_ts):
        """解析 Hacker News 的 Unix 时间戳并转为北京时间"""
        try:
            dt = datetime.datetime.utcfromtimestamp(int(unix_ts))
            cst_time = dt + datetime.timedelta(hours=8)
            return cst_time.strftime("%m-%d %H:%M")
        except:
            return get_current_time_str()

    # === 核心 1：情报抓取 (真实时间版) ===
    def run_spider(self):
        print("   └─ 正在挖掘软件情报 (目标: 60+ 条)...")
        self.news = []
        self.seen_titles.clear()
        
        # 1. Product Hunt (解析 published 时间)
        r = self.fetch("https://www.producthunt.com/feed/category/artificial-intelligence")
        if r:
            try:
                root = ET.fromstring(r.content)
                # 命名空间处理
                ns = {'atom': 'http://www.w3.org/2005/Atom'}
                for entry in root.findall('atom:entry', ns)[:30]:
                    raw_title = entry.find('atom:title', ns).text
                    if raw_title in self.seen_titles: continue
                    
                    # 获取发布时间
                    pub_node = entry.find('atom:published', ns)
                    if pub_node is not None:
                        real_time = self.parse_ph_time(pub_node.text)
                    else:
                        real_time = self.parse_ph_time(entry.find('atom:updated', ns).text)

                    self.news.append({
                        "id": str(len(self.news)), 
                        "src": "Product Hunt", "type": "APP",
                        "title": self.smart_trans(raw_title),
                        "desc": self.smart_trans(entry.find('atom:summary', ns).text),
                        "url": entry.find('atom:link', ns).attrib['href'],
                        "time": real_time  # 使用真实时间
                    })
                    self.seen_titles.add(raw_title)
                    print("📱", end="", flush=True)
            except Exception as e: 
                # print(f"PH Error: {e}") 
                pass

        # 2. Hacker News (解析 time 时间戳)
        r = self.fetch("https://hacker-news.firebaseio.co/v0/topstories.json")
        if r:
            try:
                ids = r.json()[:80]
                keys = ['Show HN', 'Launch', 'Tool', 'App', 'Open Source', 'GPT', 'LLM']
                for i in ids:
                    if len(self.news) >= 50: break
                    item = self.fetch(f"https://hacker-news.firebaseio.co/v0/item/{i}.json").json()
                    t = item.get('title', '')
                    if t in self.seen_titles: continue
                    if any(k in t for k in keys):
                        # 获取真实时间
                        real_time = self.parse_hn_time(item.get('time', time.time()))
                        
                        self.news.append({
                            "id": str(len(self.news)),
                            "src": "Hacker News", "type": "DEV",
                            "title": self.smart_trans(t),
                            "desc": self.smart_trans(f"开发者热门项目: {t}"),
                            "url": item.get('url', f"https://news.ycombinator.com/item?id={i}"),
                            "time": real_time # 使用真实时间
                        })
                        self.seen_titles.add(t)
                        print("💻", end="", flush=True)
            except: pass
        print("")
        if len(self.news) < 60: self.inject_filler(60 - len(self.news))

    def inject_filler(self, count):
        # 备用库使用“当前脚本运行时间”，因为它们是静态填充
        current_fill_time = get_current_time_str()
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
        
        added = 0
        for item in filler_db:
            if added >= count: break
            if item['title'] in self.seen_titles: continue
            self.news.append({
                "id": str(len(self.news)), "src": item['src'], "type": item['type'],
                "title": item['title'], "desc": item['desc'], "url": item['url'], 
                "time": current_fill_time # 备用数据使用当前时间
            })
            self.seen_titles.add(item['title'])
            added += 1

    # === 2. 榜单生成 (80条独家描述) ===
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

    # === 3. 超级提示词库 (扩容至60+, 支持12个轮换) ===
    def make_prompts(self):
        print("   └─ 构建海量 AI 提示词库 (含轮换池)...")
        self.prompts = [
            # === Midjourney / Art ===
            {"tag": "Midjourney", "title": "赛博朋克电影感人像", "content": "Cinematic shot, cyberpunk street samurai girl, neon lights, rain-soaked streets of Tokyo, highly detailed, photorealistic, 8k, bokeh, depth of field --ar 16:9 --v 6.0", "desc": "高质感赛博朋克风格，适合壁纸。"},
            {"tag": "Midjourney", "title": "极简主义 Logo 设计", "content": "Minimalist logo design for a coffee shop named 'Zen Brew', simple lines, vector style, flat design, white background, black ink --no shading --v 6.0", "desc": "商业 Logo 灵感生成。"},
            {"tag": "Midjourney", "title": "吉卜力动画风格", "content": "Studio Ghibli style, lush green meadow, fluffy clouds, blue sky, summer breeze, anime style, hand-drawn texture, vibrant colors --ar 16:9 --niji 6", "desc": "治愈系宫崎骏风格风景。"},
            {"tag": "Midjourney", "title": "3D 等距房间模型", "content": "Isometric 3D render of a cozy gamer room, neon lighting, computer setup, bean bag, night time, cute style, blender render, high fidelity --ar 1:1 --v 6.0", "desc": "可爱的 3D 室内设计模型。"},
            {"tag": "Midjourney", "title": "未来主义建筑设计", "content": "Futuristic eco-friendly skyscraper, vertical gardens, glass and steel, solar panels, utopia city background, architectural photography, morning light --ar 9:16 --v 6.0", "desc": "概念建筑设计灵感。"},
            {"tag": "Midjourney", "title": "水墨画风格山水", "content": "Chinese ink painting style, misty mountains, pine trees, waterfalls, traditional boat on river, black and white with subtle red accents, minimalist composition --ar 16:9", "desc": "中国传统水墨艺术风格。"},
            {"tag": "Midjourney", "title": "皮克斯风格角色", "content": "Pixar style 3D character, a cute robot holding a flower, soft lighting, expressive eyes, vibrant colors, clean background --ar 3:4 --v 6.0", "desc": "动画电影角色设计。"},
            {"tag": "Midjourney", "title": "复古胶片摄影", "content": "1990s polaroid photo, friends laughing at a diner, flash photography, vintage grain, candid shot, nostalgic vibe --ar 4:3 --v 6.0", "desc": "怀旧复古的生活瞬间。"},
            {"tag": "Midjourney", "title": "微距摄影", "content": "Macro photography of a water droplet on a rose petal, extreme detail, refraction of light, soft green bokeh background, 8k resolution --ar 1:1", "desc": "极致细节的微距摄影。"},
            {"tag": "Midjourney", "title": "扁平化矢量插画", "content": "Flat vector illustration of a startup team working in a modern office, vibrant colors, simple shapes, corporate memphis style, white background --ar 16:9", "desc": "适合网页和 PPT 的插画。"},
            {"tag": "Midjourney", "title": "抽象油画", "content": "Abstract oil painting, chaotic brushstrokes, vivid colors, emotional expression, thick impasto texture, heavy palette knife usage --ar 3:4", "desc": "充满情感的艺术油画。"},
            {"tag": "Midjourney", "title": "蒸汽朋克机械", "content": "Steampunk mechanical owl, brass gears, copper pipes, glowing steam vents, intricate details, vintage engineering blueprint style --ar 1:1", "desc": "复古机械美学设计。"},

            # === ChatGPT / Coding & Tech ===
            {"tag": "Coding", "title": "代码 Bug 修复专家", "content": "Analyze the following code snippet. Identify any logical errors, syntax bugs, or security vulnerabilities. Explain why they are issues and provide the corrected code with comments explaining the changes: [Paste Code Here]", "desc": "快速定位并修复代码错误。"},
            {"tag": "Coding", "title": "Python 编程导师", "content": "Act as a senior Python developer. Explain the concept of [Decorators] to a junior developer. Use simple analogies, provide a basic code example, and then a practical real-world use case.", "desc": "深入浅出讲解编程概念。"},
            {"tag": "Coding", "title": "生成正则表达式", "content": "I need a Regular Expression (Regex) that matches [Email addresses from specific domains]. Please explain how the regex works step-by-step.", "desc": "搞定复杂的正则匹配。"},
            {"tag": "Coding", "title": "SQL 查询优化", "content": "Optimize the following SQL query for better performance. Assume a large dataset. Explain what indexing strategies might help: [Paste SQL Here]", "desc": "提升数据库查询效率。"},
            {"tag": "Coding", "title": "编写单元测试", "content": "Write comprehensive unit tests (using Pytest/Jest) for the following function. Cover edge cases and potential failure points: [Paste Function Here]", "desc": "自动化生成测试用例。"},
            {"tag": "Coding", "title": "代码转译 (Java -> Python)", "content": "Rewrite the following Java code into idiomatic Python. Ensure the functionality remains the same but use Pythonic best practices: [Paste Code Here]", "desc": "跨语言代码转换。"},
            {"tag": "Coding", "title": "API 文档生成", "content": "Generate a Swagger/OpenAPI documentation YAML for the following API endpoint description. Include request/response examples.", "desc": "自动生成 API 接口文档。"},
            {"tag": "Coding", "title": "Git Commit 规范写手", "content": "Write a semantic Git commit message for the following changes. Use the format 'type(scope): description'. Changes: [List Changes]", "desc": "生成规范的代码提交记录。"},
            {"tag": "Coding", "title": "解释复杂代码", "content": "Explain the following code snippet line-by-line in plain English as if you are explaining it to a 10-year-old: [Paste Code]", "desc": "看懂别人的屎山代码。"},
            {"tag": "Coding", "title": "Linux 命令行助手", "content": "I need a Linux terminal command to [find all files larger than 100MB and delete them]. Please explain the flags used.", "desc": "查询复杂的 Shell 命令。"},

            # === ChatGPT / Writing & Marketing ===
            {"tag": "Writing", "title": "小红书爆款文案", "content": "你是一位拥有百万粉丝的小红书博主。请为[某款护肤品]写一篇种草笔记。要求：标题要用震惊体加Emoji，正文要有痛点场景描述，语气要像闺蜜聊天，最后加上5个相关热门标签。", "desc": "针对小红书平台的流量文案。"},
            {"tag": "Writing", "title": "SEO 博客文章大纲", "content": "Generate a detailed blog post outline for the topic '[AI in Healthcare]'. Include a catchy title, H2 headings for key sections, bullet points for sub-topics, and a conclusion. Optimize for SEO keywords.", "desc": "快速构建文章结构。"},
            {"tag": "Writing", "title": "冷邮件 (Cold Email) 推销", "content": "Write a persuasive cold email to a potential client offering [Web Design Services]. Keep it under 150 words. Hook them in the first sentence, state the value proposition clearly, and end with a call to action.", "desc": "商务拓展邮件模板。"},
            {"tag": "Writing", "title": "Youtube 视频脚本", "content": "Write a script for a 5-minute YouTube video about '[How to start investing]'. Include an engaging hook intro, 3 main tips with examples, and an outro asking for subscribers.", "desc": "视频博主脚本生成。"},
            {"tag": "Writing", "title": "推特/微博 连载贴", "content": "Turn the following article summary into a Twitter thread (10 tweets max). Make the first tweet a hook, and the last tweet a summary. Use emojis sparingly. Content: [Paste Text Here]", "desc": "长文转社交媒体短贴。"},
            {"tag": "Writing", "title": "产品发布新闻稿", "content": "Write a professional press release for the launch of a new product: [Product Name]. Highlight key features, availability, and quotes from the CEO.", "desc": "正式的媒体新闻稿。"},
            {"tag": "Writing", "title": "朋友圈营销文案", "content": "Write a short, engaging WeChat Moments post to promote [New Coffee Shop]. Use emojis, keep it casual, and include a call to action to visit.", "desc": "私域流量营销文案。"},
            {"tag": "Writing", "title": "复杂的概念简化", "content": "Rewrite the following technical text to make it easy to understand for a general audience. Avoid jargon and use simple analogies: [Paste Text]", "desc": "让你的文章通俗易懂。"},
            {"tag": "Writing", "title": "起标题大师", "content": "Generate 10 catchy, click-worthy headlines for an article about [Remote Work]. Use different styles: question, listicle, controversial, and how-to.", "desc": "拯救取名废。"},
            {"tag": "Writing", "title": "英文润色 (学术)", "content": "Please proofread and edit the following academic abstract for clarity, flow, and academic tone. Improve vocabulary where appropriate: [Paste Abstract]", "desc": "论文投稿前的最后检查。"},

            # === ChatGPT / Productivity & Office ===
            {"tag": "Productivity", "title": "会议纪要生成", "content": "Summarize the following meeting transcript into a structured report. Include: 1. Date & Attendees, 2. Key Discussion Points, 3. Action Items (with assignees), 4. Next Steps. Transcript: [Paste Here]", "desc": "整理杂乱的会议记录。"},
            {"tag": "Productivity", "title": "Excel 公式生成器", "content": "I have data in Column A (Dates) and Column B (Sales). I need an Excel formula to calculate the [Sum of Sales for the month of January]. Please explain the formula.", "desc": "解决复杂的 Excel 表格问题。"},
            {"tag": "Productivity", "title": "周报生成器", "content": "Based on these bullet points of my work this week, write a professional weekly report for my manager. Highlight achievements and blockings: [List Tasks Here]", "desc": "快速生成职场周报。"},
            {"tag": "Productivity", "title": "邮件回复 (委婉拒绝)", "content": "Write a polite and professional email declining a job offer because the salary doesn't meet my expectations, but keep the door open for future opportunities.", "desc": "高情商职场邮件回复。"},
            {"tag": "Productivity", "title": "英语口语陪练", "content": "Act as a spoken English teacher. I will speak to you in English, and you will reply to me to practice. Strictly correct my grammar mistakes in bold, and ask me a question to keep the conversation going.", "desc": "英语学习与纠错。"},
            {"tag": "Productivity", "title": "SWOT 分析", "content": "Perform a SWOT analysis (Strengths, Weaknesses, Opportunities, Threats) for [Small E-commerce Business]. Present the result in a bulleted list.", "desc": "商业决策辅助工具。"},
            {"tag": "Productivity", "title": "OKRs 设定助手", "content": "Help me draft OKRs (Objectives and Key Results) for a [Marketing Manager] for the next quarter. The main goal is to increase brand awareness.", "desc": "制定工作目标。"},
            {"tag": "Productivity", "title": "面试模拟官", "content": "I am interviewing for a [Product Manager] position. Ask me a common interview question, wait for my answer, and then give me feedback on how to improve it.", "desc": "准备求职面试。"},
            {"tag": "Productivity", "title": "PPT 大纲生成", "content": "Create a 10-slide presentation outline for a pitch deck about [AI Education App]. Include slide titles and key bullet points for each slide.", "desc": "快速搞定 PPT 结构。"},
            {"tag": "Productivity", "title": "合同条款审查", "content": "Review the following contract clause for any potential risks or unfair terms for the freelancer: [Paste Clause]", "desc": "简单的法律文本分析。"},
            
            # === ChatGPT / Roleplay & Fun ===
            {"tag": "Fun", "title": "苏格拉底式提问", "content": "I want you to act as a Socratic philosopher. You will explore my beliefs by asking probing questions. Do not give me answers, but guide me to discover them myself. My topic is: [Justice]", "desc": "深度哲学思考引导。"},
            {"tag": "Fun", "title": "文字冒险游戏", "content": "Act as a text-based adventure game. I start in a dark forest. Describe the surroundings and give me 3 options. Wait for my input before continuing.", "desc": "在对话框里玩 RPG 游戏。"},
            {"tag": "Fun", "title": "塔罗牌占卜", "content": "Act as a mystical Tarot reader. I will ask a question, and you will draw 3 cards (Past, Present, Future), describe them visually, and interpret their meaning for my situation. My question is: [Insert Question]", "desc": "趣味 AI 占卜。"},
            {"tag": "Fun", "title": "米其林大厨菜谱", "content": "I have these ingredients in my fridge: [Eggs, Tomatoes, Cheese]. Suggest a gourmet recipe I can make, describe the plating, and suggest a wine pairing.", "desc": "创意烹饪指南。"},
            {"tag": "Fun", "title": "说唱歌手 AI", "content": "Write a rap song about [Coding in Python] in the style of Eminem. Use multi-syllable rhymes and a fast flow.", "desc": "生成押韵的歌词。"},
            {"tag": "Fun", "title": "旅行规划师", "content": "Plan a 3-day itinerary for a trip to [Kyoto, Japan]. I love food and history but hate crowded tourist traps. Include restaurant recommendations.", "desc": "个性化旅行路线。"},
            {"tag": "Fun", "title": "电影推荐", "content": "I like movies like [Inception] and [Interstellar]. Recommend 5 similar sci-fi movies that are mind-bending, with a brief reason for each.", "desc": "解决剧荒。"},
            {"tag": "Fun", "title": "梦境解析", "content": "I dreamt about [flying over a city but my wings were heavy]. Interpret this dream from a Jungian psychological perspective.", "desc": "探索潜意识。"}
        ]

    # === 4. 保存数据 ===
    def save(self):
        final_data = {'news': self.news, 'ranks': self.ranks, 'prompts': self.prompts}
        js = f"window.AI_DATA = {json.dumps(final_data, ensure_ascii=False, indent=2)};"
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f: f.write(js)
            print(f"✅ [{get_current_time_str()}] 数据更新完成！(新闻:{len(self.news)}, 提示词:{len(self.prompts)})")
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
    # time.sleep(3) # 在GitHub Actions中不需要sleep
