"""TTS Worker — Edge TTS (natural male voice)"""
import sys, asyncio, edge_tts

VOICE = "en-US-GuyNeural"

async def main():
    text = sys.argv[1]
    out = sys.argv[2]
    communicate = edge_tts.Communicate(text, voice=VOICE, rate="-5%", pitch="-8Hz")
    await communicate.save(out)

if __name__ == "__main__":
    asyncio.run(main())