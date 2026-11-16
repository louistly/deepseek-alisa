import os
from fastapi import FastAPI, Request
import httpx
import asyncio

# Меняем название переменной на OPENROUTER_API_KEY
if 'OPENROUTER_API_KEY' not in os.environ:
    raise ValueError('OPENROUTER_API_KEY not set in environment')

app = FastAPI()

# 1. Меняем URL на OpenRouter
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

@app.post("/")
async def main(request: Request):
    body = await request.json()
    
    user_text = body.get("request", {}).get("original_utterance", "")
    if not user_text:
        return {
            "version": body.get("version", "1.0"),
            "session": body.get("session"),
            "response": {
                "end_session": False,
                "text": "Я слушаю. Задайте ваш вопрос."
            }
        }

       # Устанавливаем таймаут в 3.5 секунды, чтобы успеть до лимита Алисы (4.5 сек)
    timeout_settings = httpx.Timeout(3.5, connect=2.0)

    try:
        async with httpx.AsyncClient(timeout=timeout_settings) as client:
            response = await client.post(
                OPENROUTER_API_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "HTTP-Referer": "https://dialogs.yandex.ru",
                    "X-Title": "Alice Skill"
                },
                json={
                    "model": "arcee-ai/trinity-mini:free", # Очень быстрая бесплатная модель
                    "messages": [{"role": "user", "content": user_text}],
                    "max_tokens": 150 # Ограничиваем длину ответа, чтобы успеть за 4.5 секунды
                }
            )
    except httpx.TimeoutException:
        print("ОШИБКА: OpenRouter не ответил за 3.5 секунды.")
        return {
            "version": body["version"],
            "session": body["session"],
            "response": {
                "end_session": False,
                "text": "Нейросеть задумалась слишком надолго. Попробуйте переформулировать вопрос или спросить что-то покороче."
            }
        }
    except Exception as e:
        print(f"ОШИБКА сети: {e}")
        return {
            "version": body["version"],
            "session": body["session"],
            "response": {
                "end_session": False,
                "text": "Произошла сетевая ошибка при обращении к нейросети."
            }
        }

    # === БЛОК ОБРАБОТКИ ОШИБОК ===
    if response.status_code != 200:
        print(f"ОШИБКА OpenRouter: Статус {response.status_code}. Ответ: {response.text}")
        answer = "Извините, произошла ошибка при обращении к нейросети."
    else:
        try:
            data_json = response.json()
            
            if "error" in data_json:
                error_msg = data_json["error"].get("message", "Неизвестная ошибка")
                print(f"API OpenRouter вернул ошибку: {error_msg}")
                answer = f"Ошибка OpenRouter: {error_msg}"
            else:
                answer = data_json.get("choices", [{}])[0].get("message", {}).get("content", "")
                if not answer:
                    print(f"Нейросеть вернула пустой ответ: {data_json}")
                    answer = "Нейросеть не смогла сгенерировать ответ."
        except Exception as e:
            print(f"Ошибка при чтении ответа: {e}")
            answer = "Произошла внутренняя ошибка при обработке ответа."
    # === КОНЕЦ БЛОКА ОБРАБОТКИ ОШИБОК ===

    return {
        "version": body["version"],
        "session": body["session"],
        "response": {
            "end_session": False,
            "text": answer
        }
    }
