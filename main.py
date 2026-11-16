import os
from fastapi import FastAPI, Request
import requests

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

    # 2. Делаем запрос к OpenRouter
    response = requests.post(
        OPENROUTER_API_URL,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "HTTP-Referer": "https://dialogs.yandex.ru", # Обязательно для OpenRouter
            "X-Title": "Alice Skill"                     # Обязательно для OpenRouter
        },
        json={
            "model": "meta-llama/llama-3.1-8b-instruct:free", # Бесплатная модель (можно сменить на другую с :free)
            "messages": [{"role": "user", "content": user_text}],
        }
    )

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
