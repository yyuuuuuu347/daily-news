import feedparser
import requests
import json
import os
import datetime
import pytz
from openai import OpenAI

# 从环境变量读取密钥
API_KEY = os.getenv("DEEPSEEK_API_KEY")
API_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
MODEL_NAME = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN")

# 新闻源
RSS_FEEDS = [
    {"name": "BBC中文", "url": "http://www.bbc.co.uk/zhongwen/simp/index.xml"},
    {"name": "联合早报", "url": "https://www.zaobao.com/news/rss.xml"},
    {"name": "FT中文网", "url": "https://www.ftchinese.com/rss/feed"},
    {"name": "TechCrunch", "url": "https://techcrunch.com/feed/"},
    {"name": "少数派", "url": "https://sspai.com/feed"},
    {"name": "阮一峰", "url": "https://www.ruanyifeng.com/blog/atom.xml"},
    {"name": "Dribbble", "url": "https://dribbble.com/feed"},
    {"name": "National Geographic", "url": "https://www.nationalgeographic.com/rss"},
    {"name": "Lifehacker", "url": "https://lifehacker.com/feed"},
    {"name": "Reddit World News", "url": "https://www.reddit.com/r/worldnews/.rss"},
]

def fetch_news():
    """抓取过去24小时的新闻"""
    news_list = []
    now = datetime.datetime.now(datetime.timezone.utc)
    one_day_ago = now - datetime.timedelta(hours=24)
    
    for feed in RSS_FEEDS:
        try:
            d = feedparser.parse(feed["url"])
            for entry in d.entries[:5]:
                pub_time = None
                if hasattr(entry, 'published_parsed'):
                    pub_time = datetime.datetime(*entry.published_parsed[:6], tzinfo=datetime.timezone.utc)
                
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
    """调用DeepSeek总结新闻"""
    if not news_list:
        return "过去24小时没有新闻更新。"
    
    content = "以下是过去24小时的新闻列表：\n"
    for item in news_list:
        content += f"- [{item['source']}] {item['title']}: {item['link']}\n"
    
    client = OpenAI(api_key=API_KEY, base_url=API_BASE_URL)
    
    prompt = f"""
    请根据以下新闻列表，生成一份“每日早报”。
    要求：
    1. 筛选出最重要的9-10条新闻
    2. 每条新闻用一句话概括核心内容
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
    """通过PushPlus推送到微信"""
    url = "http://www.pushplus.plus/send"
    data = {
        "token": PUSHPLUS_TOKEN,
        "title": f"📰 每日早报 {datetime.date.today()}",
        "content": content,
        "template": "txt"
    }
    response = requests.post(url, json=data)
    print("推送结果:", response.text)

if __name__ == "__main__":
    news = fetch_news()
    summary = summarize_news(news)
    if PUSHPLUS_TOKEN:
        push_to_wechat(summary)
    else:
        print("未配置推送Token，直接打印结果：")
        print(summary)
