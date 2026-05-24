import asyncio
import httpx
import os

TTS_ENDPOINT = os.environ.get("TTS_ENDPOINT", "http://localhost:8001/v1")
TTS_MODEL = os.environ.get("TTS_MODEL", "openbmb/VoxCPM2")


async def test_tts():
    print("\n--- [测试 2] TTS 生成定制音频 ---")
    text = """会话动态：过去两天（4月6-7日）未发现活跃的群聊或单聊记录
日程会议：未查询到日程或会议安排
文档协作：未发现新建或编辑的文档
协作者：暂无新增协作者"""
    voice = "(A warm young woman)"

    url = f"{TTS_ENDPOINT}/audio/speech"
    body = {
        "model": TTS_MODEL,
        "input": f"{voice}{text}",
        "voice": "default",
        "response_format": "wav"
    }

    print("⏳ 正在请求 TTS 合成...")
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=body)
            print(f"📦 状态码: {resp.status_code}")
            if resp.status_code == 200:
                save_path = "./test_output_tts.wav"
                with open(save_path, "wb") as f:
                    f.write(resp.content)
                print(f"✅ TTS 定制音频已成功保存至: {os.path.abspath(save_path)}")
            else:
                print("❌ 错误响应:", resp.text)
    except Exception as e:
        print("❌ 异常:", e)


if __name__ == "__main__":
    asyncio.run(test_tts())
