import asyncio, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, "src")
from engram.core.logging import setup_logging; setup_logging(level="INFO")
from engram.extractors import BilibiliExtractor

async def main():
    url = "https://www.bilibili.com/video/BV1GJ411x7h7"
    ext = BilibiliExtractor()
    result = await ext.extract(url)
    print(f"Title: {result.title}")
    print(f"Content len: {len(result.content)}")
    print(f"Method: {result.raw_data.get('method')}")

    bvid = ext._extract_bvid(url)
    ts = await ext.get_timestamped_transcript(bvid)
    if ts:
        print(f"Timestamped lines: {len(ts.splitlines())}")
        print(ts[:400])
    else:
        print("No timestamped transcript")
    await ext.close()

asyncio.run(main())
