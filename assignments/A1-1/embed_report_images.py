from pathlib import Path
import re
import zipfile


ROOT = Path(__file__).resolve().parent
REPO = ROOT / "python-prompt-manager"
DOCX = REPO / "Python_Git_미션과제_제출보고서.docx"
MARKDOWN = REPO / "Python_Git_미션과제_제출보고서.md"


with zipfile.ZipFile(DOCX) as archive:
    media = sorted(
        (name for name in archive.namelist() if re.fullmatch(r"word/media/image\d+\.png", name)),
        key=lambda name: int(re.search(r"image(\d+)\.png", name).group(1)),
    )
    if len(media) != 28:
        raise RuntimeError(f"예상 이미지 28개와 다릅니다: {len(media)}")

    for number, member in enumerate(media, start=1):
        target = REPO / f"report-figure-{number:02d}.png"
        target.write_bytes(archive.read(member))


text = MARKDOWN.read_text(encoding="utf-8")
text = text.replace(
    "> 원본 DOCX에 포함된 실행 화면 캡처는 Markdown 단일 파일 변환 과정에서 제외했으며, 그림 번호와 캡션은 본문에 유지했습니다.",
    "> 원본 DOCX에 포함된 실행 화면 캡처 28개를 추출하여 각 그림 캡션과 함께 배치했습니다.",
)


def add_image(match: re.Match[str]) -> str:
    caption = match.group(1)
    number = int(match.group(2))
    return f"![{caption}](report-figure-{number:02d}.png)\n\n*{caption}*"


text, count = re.subn(r"^\*(그림 (\d+)\.[^\n]+)\*$", add_image, text, flags=re.MULTILINE)
if count != 28:
    raise RuntimeError(f"예상 그림 캡션 28개와 다릅니다: {count}")

MARKDOWN.write_text(text, encoding="utf-8")
print(f"images={len(media)} markdown_links={count}")
