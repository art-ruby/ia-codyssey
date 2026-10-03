"""새 소식 기본 출처(설계 §5). 2026-10-04에 서비스 User-Agent로 응답을 확인한 주소다."""
from __future__ import annotations

MAX_SOURCES = 20
NAME_LIMIT = 40

# (키, 이름, 피드 주소, 종류, 기본 켜짐)
DEFAULT_SOURCES: tuple[tuple[str, str, str, str, bool], ...] = (
    ("openai", "OpenAI News", "https://openai.com/news/rss.xml", "official", True),
    ("google-ai", "Google AI 블로그", "https://blog.google/technology/ai/rss/", "official", True),
    ("deepmind", "Google DeepMind 블로그", "https://deepmind.google/blog/rss.xml", "official", True),
    ("huggingface", "Hugging Face 블로그", "https://huggingface.co/blog/feed.xml", "official", True),
    ("geeknews", "GeekNews", "https://news.hada.io/rss/news", "community", True),
    ("hn-ai", "Hacker News (AI, 100점 이상)", "https://hnrss.org/newest?q=AI&points=100", "community", True),
    # 연달아 요청하면 429를 주고 클라우드 IP를 자주 막아 기본값은 끔.
    ("reddit-localllama", "Reddit r/LocalLLaMA", "https://www.reddit.com/r/LocalLLaMA/.rss", "community", False),
)
