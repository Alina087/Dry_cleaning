from fastapi import FastAPI
import pickle
from pydantic import BaseModel
import pandas as pd
import numpy as np
import warnings
import sklearn
import os

# Отключаем параллельное выполнение для избежания ошибок
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'

warnings.filterwarnings("ignore")

app = FastAPI()


# Функция для безопасной загрузки моделей с исправлением атрибутов
def load_model_with_fix(filepath):
    try:
        with open(filepath, 'rb') as file:
            model = pickle.load(file)

        # Исправляем отсутствующий атрибут monotonic_cst для деревьев
        if hasattr(model, 'estimators_') and model.estimators_ is not None:
            for estimator in model.estimators_:
                if hasattr(estimator, 'monotonic_cst'):
                    delattr(estimator, 'monotonic_cst')
                elif not hasattr(estimator, 'monotonic_cst'):
                    estimator.monotonic_cst = None

        # Для одиночных деревьев
        if hasattr(model, 'monotonic_cst'):
            delattr(model, 'monotonic_cst')
        elif not hasattr(model, 'monotonic_cst'):
            model.monotonic_cst = None

        return model

    except Exception as e:
        print(f"Error loading model from {filepath}: {e}")
        return None


# Загружаем модели с исправлениями
br = load_model_with_fix('C:\\Users\\Huawei\\Downloads\\model_reg_br_fasts3.pkl')
rf = load_model_with_fix('C:\\Users\\Huawei\\Downloads\\model_clas_rf_fasts3.pkl')

# Мэппинги
LISTING_TYPE_MAPPING = {
    1: 'Rent (Аренда)',
    2: 'Sale (Продажа)'
}

SUBTYPE_MAPPING = {
    0: 'Flat (Квартира)',
    7: 'Residence (Резиденция)',
    8: 'Villa (Вилла)',
    5: 'Müstakil Ev (Отдельный дом)',
    2: 'Kooperatif (Кооператив)',
    10: 'Yazlık (Летний дом)',
    1: 'Komple Bina (Целое здание)',
    6: 'Prefabrik Ev (Сборный дом)',
    3: 'Köşk / Konak / Yalı (Особняк/Усадьба/Водный дом)',
    11: 'Çiftlik Evi (Фермерский дом)',
    9: 'Yalı Dairesi (Водная квартира)',
    4: 'Loft (Лофt)'
}


# Для предсказания цены (price не нужен)
class HousingDataForPrice(BaseModel):
    type: int = 0  # Всегда Housing
    sub_type: int
    listing_type: int
    tom: int
    building_age: int
    total_floor_count: int
    floor_no: int
    size: float
    heating_type: int
    city: int
    total_rooms: int


# Для предсказания типа объявления (price нужен!)
class HousingDataForListingType(BaseModel):
    type: int = 0  # Всегда Housing
    sub_type: int
    tom: int
    building_age: int
    total_floor_count: int
    floor_no: int
    size: float
    heating_type: int
    price: float  # Цена как признак для классификации!
    city: int
    total_rooms: int


def safe_predict_regression(model, input_data):
    """Безопасное предсказание для регрессионной модели"""
    try:
        # Дополнительная проверка и исправление атрибутов
        if hasattr(model, 'estimators_'):
            for estimator in model.estimators_:
                if not hasattr(estimator, 'monotonic_cst'):
                    estimator.monotonic_cst = None

        result = model.predict(input_data)[0]
        return result
    except Exception as e:
        print(f"Prediction error: {e}")
        return 0.0


def safe_predict_classification(model, input_data):
    """Безопасное предсказание для классификационной модели"""
    try:
        # Дополнительная проверка и исправление атрибутов
        if hasattr(model, 'estimators_'):
            for estimator in model.estimators_:
                if not hasattr(estimator, 'monotonic_cst'):
                    estimator.monotonic_cst = None

        result = model.predict_proba(input_data)[0]
        return result
    except Exception as e:
        print(f"Classification error: {e}")
        return np.array([0.5, 0.5])  # Возвращаем равные вероятности при ошибке


@app.post("/predict-price")
def predict_price(data: HousingDataForPrice):
    if br is None:
        return {"error": "Regression model not loaded"}

    input_data = pd.DataFrame([data.dict()])
    predicted_price = safe_predict_regression(br, input_data)

    return {
        "predicted_price": float(predicted_price),
        "currency": "TRY",
        "parameters": data.dict()
    }


@app.post("/predict-listing-type")
def predict_listing_type(data: HousingDataForListingType):
    if rf is None:
        return {"error": "Classification model not loaded"}

    input_data = pd.DataFrame([data.dict()])
    probabilities = safe_predict_classification(rf, input_data)
    predicted_class = np.argmax(probabilities) + 1  # +1 т.к. индексы начинаются с 0

    # Формируем ответ с вероятностями для всех классов
    predictions = []
    for i, prob in enumerate(probabilities):
        predictions.append({
            "listing_type_code": i + 1,
            "listing_type": LISTING_TYPE_MAPPING.get(i + 1, f"Unknown {i + 1}"),
            "probability": float(prob)
        })

    predictions.sort(key=lambda x: x["probability"], reverse=True)

    return {
        "predicted_listing_type": predictions[0]["listing_type_code"],
        "predictions": predictions
    }