import os
from fastapi import FastAPI, Request
import requests

if 'DEEPSEEK_API_KEY' not in os.environ:
    raise ValueError('DEEPSEEK_API_KEY not set in environment')

app = FastAPI()

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

@app.post("/")
async def main(request: Request):
    body = await request.json()
    
    # Иногда Алиса присылает пустой запрос при первом запуске навыка
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

    # Делаем запрос к DeepSeek
    response = requests.post(
        DEEPSEEK_API_URL,
        headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
        json={
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": user_text}],
        }
    )

    # === НАЧАЛО БЛОКА ОБРАБОТКИ ОШИБОК ===
    if response.status_code != 200:
        # Если ключ неверный или закончились деньги, мы увидим это в логах Render
        print(f"ОШИБКА DeepSeek: Статус {response.status_code}. Ответ: {response.text}")
        answer = "Извините, произошла ошибка при обращении к DeepSeek. Проверьте логи на сервере."
    else:
        try:
            data_json = response.json()
            
            # Проверяем, не вернул ли DeepSeek ошибку внутри тела ответа
            if "error" in data_json:
                error_msg = data_json["error"].get("message", "Неизвестная ошибка")
                print(f"API DeepSeek вернул ошибку: {error_msg}")
                answer = f"Ошибка DeepSeek: {error_msg}"
            else:
                # Безопасно достаем текст ответа
                answer = data_json.get("choices", [{}])[0].get("message", {}).get("content", "")
                if not answer:
                    print(f"DeepSeek вернул пустой ответ: {data_json}")
                    answer = "DeepSeek не смог сгенерировать ответ."
        except Exception as e:
            print(f"Ошибка при чтении ответа от DeepSeek: {e}")
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
