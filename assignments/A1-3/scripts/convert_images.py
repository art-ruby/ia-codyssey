"""PNG/JPG 원본을 WebP로 일회성 변환한다.

배포본은 변환 결과(.webp)를 커밋해서 쓰고, 이 스크립트는 재현용으로 남긴다.
빌드 파이프라인에 넣지 않는다 — 자산이 거의 바뀌지 않아 빌드마다 돌릴 이유가 없다.
"""
from pathlib import Path

from PIL import Image

TARGET_MAX_WIDTH = 1600
QUALITY = 82


def convert(src: Path) -> Path:
    dst = src.with_suffix(".webp")
    with Image.open(src) as im:
        im = im.convert("RGB")
        if im.width > TARGET_MAX_WIDTH:
            ratio = TARGET_MAX_WIDTH / im.width
            im = im.resize((TARGET_MAX_WIDTH, round(im.height * ratio)), Image.LANCZOS)
        im.save(dst, "WEBP", quality=QUALITY, method=6)
    return dst


def main() -> int:
    images = Path(__file__).resolve().parents[1] / "images"
    sources = sorted(p for p in images.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg"})
    if not sources:
        print("변환할 원본이 없습니다.")
        return 1
    for src in sources:
        dst = convert(src)
        before = src.stat().st_size / 1024
        after = dst.stat().st_size / 1024
        print(f"{src.name:24} {before:8.0f}KB -> {dst.name:24} {after:8.0f}KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
