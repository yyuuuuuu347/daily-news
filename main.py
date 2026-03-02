import feedparser
import requests
import json
import os
import datetime
import pytz
from openai import OpenAI

# --- 从环境变量读取密钥 (安全第一) ---
API_KEY = os.getenv("DEEPSEEK_API_KEY")
API_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
MODEL_NAME = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN")

# 新闻源 (RSS) - 你可以自由增删 [citation:1][citation:3]
RSS_FEEDS = [
    {"name": "BBC中文", "url": "http://www.bbc.co.uk/zhongwen/simp/index.xml"},
    {"name": "纽约时报中文", "url": "https://cn.nytimes.com/rss"},
    {"name": "联合早报", "url": "https://www.zaobao.com/news/rss.xml"},
    # 财经商业
    {"name": "FT中文网", "url": "https://www.ftchinese.com/rss/feed"},
    # 科技
    {"name": "TechCrunch", "url": "https://techcrunch.com/feed/"},
    # 中文科技
    {"name": "少数派", "url": "https://sspai.com/feed"},
    # 独立博客
    {"name": "阮一峰", "url": "https://www.ruanyifeng.com/blog/atom.xml"},
    # 设计创意
    {"name": "Dribbble", "url": "https://dribbble.com/feed"},
    # 科学文化
    {"name": "National Geographic", "url": "https://www.nationalgeographic.com/rss"},
    # 生活趣味
    {"name": "Lifehacker", "url": "https://lifehacker.com/feed"},
    # 聚合
    {"name": "Reddit World News", "url": "https://www.reddit.com/r/worldnews/.rss"},
]
]

def fetch_news():
    """抓取过去24小时的新闻"""
    news_list = []
    now = datetime.datetime.now(datetime.timezone.utc)
    one_day_ago = now - datetime.timedelta(hours=24)
    
    for feed in RSS_FEEDS:
        try:
            d = feedparser.parse(feed["url"])
            for entry in d.entries[:20]:  # 每个源最多取20条
                # 尝试解析发布时间
                pub_time = None
                if hasattr(entry, 'published_parsed'):
                    pub_time = datetime.datetime(*entry.published_parsed[:6], tzinfo=datetime.timezone.utc)
                
                # 如果在24小时内，或者解析失败就取最新几条
                if (pub_time and pub_time > one_day_ago) or (not pub_time):
                    news_list.append({
                        "title": entry.title,
                        "link": entry.link,
                        "source": feed["name"]
                    })
        except Exception as e:
            print(f"抓取 {feed['name']} 失败: {e}")
    
    return news_list

def summarize_news(news_list):
    """调用DeepSeek总结新闻 [citation:3]"""
    if not news_list:
        return "过去24小时没有新闻更新。"
    
    # 拼接新闻文本
    content = "以下是过去24小时的新闻列表：\n"
    for item in news_list:
        content += f"- [{item['source']}] {item['title']}: {item['link']}\n"
    
    client = OpenAI(api_key=API_KEY, base_url=API_BASE_URL)
    
    prompt = f"""
    请根据以下新闻列表，生成一份“每日早报”。
    要求：
    1. 筛选出最重要的9-10条新闻
    2. 每条新闻用一句话精准概括核心内容
    3. 格式简洁，适合微信阅读
    4. 使用中文
    
    新闻列表：
    {content}
    """
    
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    
    return response.choices[0].message.content

def push_to_wechat(content):
    """通过PushPlus推送到微信 [citation:3][citation:4]"""
    url = "http://www.pushplus.plus/send"
    data = {
        "token": PUSHPLUS_TOKEN,
        "title": f"📰 每日早报 {datetime.date.today()}",
        "content": content,
        "template": "txt"  # 普通文本模式
    }
    response = requests.post(url, json=data)
    print("推送结果:", response.text)

if __name__ == "__main__":
    # 1. 抓取新闻 [citation:1][citation:3]
    news = fetch_news()
    # 2. AI总结
    summary = summarize_news(news)
    # 3. 推送到微信
    if PUSHPLUS_TOKEN:
        push_to_wechat(summary)
    else:
        print("未配置推送Token，直接打印结果：")
        print(summary)
