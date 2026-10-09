"""TTS Worker — Edge TTS + word-level boundaries

argv[1] = text, argv[2] = mp3 output path, argv[3] = optional JSON meta path.

edge-tts defaults to `boundary="SentenceBoundary"`, which returns one timing
for the whole sentence and nothing per word. Passing `boundary="WordBoundary"`
makes the service emit one event per spoken word; those offsets are what the
FM page needs to keep its green highlight in step with the narration.
"""
import sys, json, asyncio, edge_tts

VOICE = "en-US-GuyNeural"


async def main():
    text = sys.argv[1]
    out = sys.argv[2]
    meta = sys.argv[3] if len(sys.argv) > 3 else None

    communicate = edge_tts.Communicate(
        text, voice=VOICE, rate="-5%", pitch="-8Hz", boundary="WordBoundary"
    )

    boundaries = []
    with open(out, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                boundaries.append({
                    "text": chunk["text"],
                    "offset": chunk["offset"],      # 100-nanosecond ticks
                    "duration": chunk["duration"],
                })

    if meta:
        with open(meta, "w", encoding="utf-8") as f:
            json.dump(boundaries, f, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(main())
