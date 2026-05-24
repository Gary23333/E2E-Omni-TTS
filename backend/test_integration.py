import asyncio
import base64
import json
import httpx
import os

# Read from environment variables; fall back to localhost defaults for local dev
LLM_ENDPOINT = os.environ.get("LLM_ENDPOINT", "http://localhost:8000/v1")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4o")
TTS_ENDPOINT = os.environ.get("TTS_ENDPOINT", "http://localhost:8001/v1")
TTS_MODEL = os.environ.get("TTS_MODEL", "openbmb/VoxCPM2")

AUDIO_PATH = os.environ.get("AUDIO_PATH", "data/noise_samples/cafe.wav")


async def test_llm_omni():
    print("--- [测试 1] LLM Omni 模式接收音频 ---")
    if not os.path.exists(AUDIO_PATH):
        print(f"❌ 错误: 找不到音频文件 {AUDIO_PATH}")
        return

    with open(AUDIO_PATH, "rb") as f:
        audio_bytes = f.read()

    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {
            "role": "user",
            "content": [
                {"type": "input_audio", "input_audio": {"data": f"data:audio/wav;base64,{audio_b64}"}},
                {"type": "text", "text": "请听这段录音并回复我的问题。"}
            ]
        }
    ]

    headers = {"Content-Type": "application/json"}
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"

    body = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": 0.7
    }

    print("⏳ 正在发送音频至 LLM...")
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(LLM_ENDPOINT + "/chat/completions", json=body, headers=headers)
            print(f"📦 状态码: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print("\n✅ LLM 返回内容:")
                print(data["choices"][0]["message"]["content"])
            else:
                print("❌ 错误响应:", resp.text)
    except Exception as e:
        print("❌ 异常:", e)


async def test_tts():
    print("\n--- [测试 2] TTS 生成音频 ---")
    text = "会话动态：过去两天（4月6-7日）未发现活跃的群聊或单聊记录\n日程会议：未查询到日程或会议安排\n文档协作：未发现新建或编辑的文档\n协作者：暂无新增协作者"
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
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=body)
            print(f"📦 状态码: {resp.status_code}")
            if resp.status_code == 200:
                save_path = "test_output_tts.wav"
                with open(save_path, "wb") as f:
                    f.write(resp.content)
                print(f"✅ TTS 音频已成功保存至: {os.path.abspath(save_path)}")
            else:
                print("❌ 错误响应:", resp.text)
    except Exception as e:
        print("❌ 异常:", e)


async def main():
    await test_llm_omni()
    await test_tts()


if __name__ == "__main__":
    asyncio.run(main())
