from fastapi import FastAPI, HTTPException
from typing import List, Optional
import pandas as pd
import numpy as np
import re
import string
import pymysql
import pymysql.cursors
from contextlib import contextmanager
from tensorflow.keras.models import load_model
import pickle
import nltk
from nltk.corpus import stopwords
import pymorphy3
import warnings
from pydantic import BaseModel

warnings.filterwarnings('ignore')

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '1234',
    'database': 'db_comment',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

app = FastAPI()

try:
    model = load_model('model_1.keras')
except Exception as e:
    model = None

try:
    with open('tfidf.pkl', 'rb') as f:
        tfidf = pickle.load(f)
except Exception as e:
    from sklearn.feature_extraction.text import TfidfVectorizer
    tfidf = TfidfVectorizer(max_features=500, ngram_range=(1, 2))

morph = pymorphy3.MorphAnalyzer(lang='ru')
russian_stopwords = stopwords.words("russian")
russian_stopwords.extend(['т.д.', 'т', 'д', 'это', 'который', 'которые', 'которых', 'свой', 'своём', 'всем', 'всё',
                          'её', 'оба', 'ещё', 'должный', 'должные', 'должных'])

st = '\xa0—'
custom_punctuation = string.punctuation + '«»'


def remove_othersymbol(text):
    """Удаляет специальные символы"""
    return ''.join([ch if ch not in st else ' ' for ch in text])


def remove_punctuation(text):
    """Удаляет пунктуацию"""
    return ''.join([ch for ch in text if ch not in custom_punctuation])


def remove_numbers(text):
    """Удаляет цифры"""
    return ''.join([i if not i.isdigit() else ' ' for i in text])


def remove_multiple_spaces(text):
    """Удаляет множественные пробелы"""
    return re.sub(r'\s+', ' ', text, flags=re.I)


def remove_stopwords(text):
    """Удаляет стоп-слова"""
    if not isinstance(text, str):
        return text
    words = text.split()
    filtered_words = [word for word in words if word.lower() not in russian_stopwords]
    return ' '.join(filtered_words)


def lemmatize_text(text):
    """Лемматизация текста"""
    if not isinstance(text, str) or not text.strip():
        return text

    words = text.split()
    lemmatized = []
    for word in words:
        try:
            p = morph.parse(word)[0]
            lemmatized.append(p.normal_form)
        except:
            lemmatized.append(word)
    return ' '.join(lemmatized)


def preprocess_text(text):
    """Полный цикл предобработки текста"""
    if not isinstance(text, str) or not text.strip():
        return ""

    text = text.lower()
    text = remove_othersymbol(text)
    text = remove_punctuation(text)
    text = remove_numbers(text)
    text = remove_multiple_spaces(text)
    text = remove_stopwords(text)
    text = lemmatize_text(text)

    return text.strip()


@contextmanager
def get_db_connection():
    """Контекстный менеджер для подключения к БД"""
    conn = pymysql.connect(**DB_CONFIG)
    try:
        yield conn
    finally:
        conn.close()


class Comment(BaseModel):
    comment_id: int
    comment_text: str
    comment_ton: Optional[int] = None


class SentimentResponse(BaseModel):
    comment_id: int
    comment_text: str
    comment_ton: int
    probability: float


class TextPredictionResponse(BaseModel):
    original_text: str
    processed_text: str
    sentiment: str
    probability: float
    confidence: float


@app.get("/comments", response_model=List[Comment])
def get_comments():
    """Получить все комментарии"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT comment_id, comment_text, comment_ton FROM comments")
                comments = cursor.fetchall()
        return comments
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка базы данных: {str(e)}")


@app.post("/comments/{comment_id}/predict", response_model=SentimentResponse)
def predict_comment(comment_id: int):
    """Предсказать тональность комментария по ID"""
    if model is None:
        raise HTTPException(status_code=503, detail="Модель не загружена")

    if tfidf is None:
        raise HTTPException(status_code=503, detail="Векторизатор не загружен")

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT comment_id, comment_text, comment_ton FROM comments WHERE comment_id = %s",
                    (comment_id,)
                )
                comment = cursor.fetchone()

        if not comment:
            raise HTTPException(status_code=404, detail="Комментарий не найден")

        processed_text = preprocess_text(comment['comment_text'])

        if not processed_text:
            processed_text = "пустой комментарий"

        text_vectorized = tfidf.transform([processed_text]).toarray().astype(np.float32)

        probability = float(model.predict(text_vectorized, verbose=0)[0][0])
        comment_ton = 1 if probability > 0.5 else 0

        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE comments SET comment_ton = %s WHERE comment_id = %s",
                    (comment_ton, comment_id)
                )
                conn.commit()

        return {
            "comment_id": comment_id,
            "comment_text": comment['comment_text'],
            "comment_ton": comment_ton,
            "probability": probability
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при анализе: {str(e)}")


@app.post("/predict/all")
def predict_all_comments():
    """Предсказать тональность для всех комментариев без тональности"""
    if model is None:
        raise HTTPException(status_code=503, detail="Модель не загружена")

    if tfidf is None:
        raise HTTPException(status_code=503, detail="Векторизатор не загружен")

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT comment_id, comment_text FROM comments WHERE comment_ton IS NULL")
                comments = cursor.fetchall()

                if not comments:
                    return {"message": "Нет комментариев для обработки"}

                updated = 0
                errors = 0

                for comment in comments:
                    try:
                        processed_text = preprocess_text(comment['comment_text'])

                        if not processed_text:
                            processed_text = "пустой комментарий"

                        text_vectorized = tfidf.transform([processed_text]).toarray().astype(np.float32)

                        probability = float(model.predict(text_vectorized, verbose=0)[0][0])
                        comment_ton = 1 if probability > 0.5 else 0

                        cursor.execute(
                            "UPDATE comments SET comment_ton = %s WHERE comment_id = %s",
                            (comment_ton, comment['comment_id'])
                        )
                        updated += 1

                    except Exception as e:
                        print(f"Ошибка при обработке ID {comment['comment_id']}: {str(e)}")
                        errors += 1
                        continue

                conn.commit()

        return {
            "message": f"Обработано комментариев: {updated}",
            "errors": errors,
            "total": len(comments)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при массовом анализе: {str(e)}")


@app.post("/predict/text", response_model=TextPredictionResponse)
def predict_text(text: str):
    """Предсказать тональность для произвольного текста"""
    if model is None:
        raise HTTPException(status_code=503, detail="Модель не загружена")

    if tfidf is None:
        raise HTTPException(status_code=503, detail="Векторизатор не загружен")

    try:
        processed_text = preprocess_text(text)

        if not processed_text:
            processed_text = "пустой комментарий"

        text_vectorized = tfidf.transform([processed_text]).toarray().astype(np.float32)

        probability = float(model.predict(text_vectorized, verbose=0)[0][0])
        sentiment = "токсичный" if probability > 0.5 else "нетоксичный"
        confidence = probability if probability > 0.5 else 1 - probability

        return {
            "original_text": text,
            "processed_text": processed_text,
            "sentiment": sentiment,
            "probability": probability,
            "confidence": confidence
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при анализе текста: {str(e)}")