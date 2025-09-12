import streamlit as st
import requests
import pandas as pd
import os

# Настройка прокси
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''

# Мэппинги
LISTING_TYPE_MAPPING = {
    1: 'Rent (Аренда)',
    2: 'Sale (Продажа)'
}

HEATING_TYPE_MAPPING = {
    11: 'None (Нет)',
    1: 'Central heating (Центральное отопление)',
    5: 'Central heating (Natural gas) (Центральное отопление - газ)',
    2: 'Central heating (Coal) (Центральное отопление - уголь)',
    6: 'Combi boiler (Electric) (Комбинированный котел - электрический)',
    0: 'Air conditioning (Кондиционер)',
    7: 'Combi boiler (Gas) (Комбинированный котел - газ)',
    4: 'Central heating (Metered) (Центральное отопление - счетчик)',
    8: 'Fancoil (AC type) (Фанкойл)',
    13: 'Stove (Coal) (Печь - уголь)',
    9: 'Floor heating (Теплый пол)',
    14: 'Stove (Natural gas) (Печь - газ)',
    12: 'Solar energy (Солнечная энергия)',
    3: 'Central heating (Fuel oil) (Центральное отопление - мазут)',
    10: 'Geothermal energy (Геотермальная энергия)'
}

CITY_MAPPING = {
    0: "Adana", 1: "Adıyaman", 2: "Afyonkarahisar", 3: "Aksaray", 4: "Amasya",
    5: "Ankara", 6: "Antalya", 7: "Ardahan", 8: "Artvin", 9: "Aydın", 10: "Ağrı",
    11: "Balıkesir", 12: "Bartın", 13: "Batman", 14: "Bayburt", 15: "Bilecik",
    16: "Bingöl", 17: "Bitlis", 18: "Bolu", 19: "Burdur", 20: "Bursa", 21: "Denizli",
    22: "Diyarbakır", 23: "Düzce", 24: "Edirne", 25: "Elazığ", 26: "Erzincan",
    27: "Erzurum", 28: "Eskişehir", 29: "Gaziantep", 30: "Giresun", 31: "Gümüşhane",
    32: "Hakkari", 33: "Hatay", 34: "Isparta", 35: "Iğdır", 36: "KKTC", 37: "Kahramanmaraş",
    38: "Karabük", 39: "Karaman", 40: "Kars", 41: "Kastamonu", 42: "Kayseri", 43: "Kilis",
    44: "Kocaeli", 45: "Konya", 46: "Kütahya", 47: "Kırklareli", 48: "Kırıkkale",
    49: "Kırşehir", 50: "Malatya", 51: "Manisa", 52: "Mardin", 53: "Mersin", 54: "Muğla",
    55: "Muş", 56: "Nevşehir", 57: "Niğde", 58: "Ordu", 59: "Osmaniye", 60: "Rize",
    61: "Sakarya", 62: "Samsun", 63: "Siirt", 64: "Sinop", 65: "Sivas", 66: "Tekirdağ",
    67: "Tokat", 68: "Trabzon", 69: "Tunceli", 70: "Uşak", 71: "Van", 72: "Yalova",
    73: "Yozgat", 74: "Zonguldak", 75: "Çanakkale", 76: "Çankırı", 77: "Çorum",
    78: "İstanbul", 79: "İzmir", 80: "Şanlıurfa", 81: "Şırnak"
}

SUBTYPE_MAPPING = {
    0: 'Flat (Квартира)', 7: 'Residence (Резиденция)', 8: 'Villa (Вилла)',
    5: 'Müstakil Ev (Отдельный дом)', 2: 'Kooperatif (Кооператив)',
    10: 'Yazlık (Летний дом)', 1: 'Komple Bina (Целое здание)',
    6: 'Prefabrik Ev (Сборный дом)', 3: 'Köşk / Konak / Yalı (Особняк/Усадьба/Водный дом)',
    11: 'Çiftlik Evi (Фермерский дом)', 9: 'Yalı Dairesi (Водная квартира)', 4: 'Loft (Лофт)'
}

def call_api(endpoint, data):
    """Универсальная функция для вызова API"""
    try:
        url = f'http://127.0.0.1:8000{endpoint}'
        response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Ошибка при обращении к API: {str(e)}")
        return None
    except Exception as e:
        st.error(f"Неожиданная ошибка: {str(e)}")
        return None

# Основное приложение
st.set_page_config(page_title="Предсказать недвижимость", layout="wide")

# Сайдбар для навигации
st.sidebar.title("🏠 Предсказать недвижимость")
page = st.sidebar.radio("Навигация", ["Предсказание цены", "Предсказание типа объявления", "Руководство пользователя"])

if page == "Предсказание цены":
    st.title("Предсказание цены жилья")

    # Форма для ввода данных
    col1, col2 = st.columns(2)

    with col1:
        listing_type = st.selectbox(
            "Тип объявления",
            options=list(LISTING_TYPE_MAPPING.keys()),
            format_func=lambda x: LISTING_TYPE_MAPPING[x],
            index=1
        )
        sub_type = st.selectbox(
            "Тип недвижимости",
            options=list(SUBTYPE_MAPPING.keys()),
            format_func=lambda x: SUBTYPE_MAPPING[x],
            index=0
        )
        tom = st.slider("Время на рынке (дни)", 0, 180, 30)
        building_age = st.selectbox(
            "Возраст здания",
            options=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
            format_func=lambda x: {
                0: "0 лет (Новостройка)", 1: "1 год", 2: "2 года", 3: "3 года",
                4: "4 года", 5: "5 лет", 6: "6-10 лет", 7: "11-15 лет",
                8: "16-20 лет", 9: "21-25 лет", 10: "26-30 лет", 11: "31-35 лет",
                12: "36-40 лет", 13: "40+ лет"
            }[x],
            index=0
        )
        total_floor_count = st.selectbox(
            "Общее количество этажей",
            options=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
            format_func=lambda x: {
                0: "1 этаж", 3: "2 этажа", 5: "3 этажа", 6: "4 этажей", 7: "5 этажей", 8: "6 этажей", 9: "7 этажей",
                10: "8 этажей",
                11: "9 этажей", 1: "10 этажей", 2: "10-20 этажей", 4: "20+ этажей"
            }[x],
            index=4
        )

    with col2:
        floor_no = st.selectbox(
            "Этаж",
            options=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24],
            format_func=lambda x: {
                0: "Цокольный этаж (-1)", 1: "0 этаж", 2: "1 этаж", 13: "2 этаж", 15: "3 этаж",
                16: "4 этаж", 17: "5 этаж", 18: "6 этаж", 19: "7 этаж", 20: "8 этаж",
                21: "9 этаж", 3: "10 этаж", 4: "11 этаж", 5: "12 этаж", 6: "13 этаж", 7: "14 этаж", 8: "15 этаж",
                9: "16 этаж", 10: "17 этаж", 11: "18 этаж", 12: "19 этаж", 14: "20+ этаж", 24: "Последний этаж (Top)", 22: "Весь этаж (Full)", 23: "Другое (Other)"
            }[x],
            index=1
        )
        size = st.slider("Площадь (м²)", 30.0, 500.0, 90.0, step=1.0)
        heating_type = st.selectbox(
            "Тип отопления",
            options=list(HEATING_TYPE_MAPPING.keys()),
            format_func=lambda x: HEATING_TYPE_MAPPING[x],
            index=8
        )
        city = st.selectbox(
            "Город",
            options=list(CITY_MAPPING.keys()),
            format_func=lambda x: CITY_MAPPING[x],
            index=0
        )
        total_rooms = st.slider("Количество комнат", 1, 10, 3)

    if st.button("Предсказать цену", type="primary"):
        data = {
            "type": 0,
            "sub_type": sub_type,
            "listing_type": listing_type - 1,
            "tom": tom,
            "building_age": building_age,
            "total_floor_count": total_floor_count,
            "floor_no": floor_no,
            "size": size,
            "heating_type": heating_type,
            "city": city,
            "total_rooms": total_rooms
        }

        with st.spinner("Рассчитываем цену..."):
            result = call_api("/predict-price", data)

            if result and "predicted_price" in result:
                predicted_price = result["predicted_price"]
                st.success(f"### Предсказанная цена: {predicted_price:,.0f} TRY")

                st.info(f"""
                **Детали предсказания:**
                - Площадь: {size} м²
                - Комнат: {total_rooms}
                - Город: {CITY_MAPPING[city]}
                - Тип объявления: {LISTING_TYPE_MAPPING[listing_type]}
                - Тип недвижимости: {SUBTYPE_MAPPING[sub_type]}
                """)
            elif result and "error" in result:
                st.error(f"Ошибка: {result['error']}")

elif page == "Предсказание типа объявления":
    st.title("Предсказание типа объявления")

    col1, col2 = st.columns(2)

    with col1:
        size = st.slider("Площадь (м²)", 30.0, 500.0, 90.0, step=1.0, key="type_size")
        total_rooms = st.slider("Количество комнат", 1, 10, 3, key="type_rooms")
        total_floor_count = st.selectbox(
            "Общее количество этажей",
            options=[0, 1, 2, 3, 4, 5, 6, 7, 8],
            format_func=lambda x: {
                0: "1 этаж", 3: "2 этажа", 5: "3 этажа", 6: "4 этажей", 7: "5 этажей", 8: "6 этажей", 9: "7 этажей", 10: "8 этажей",
                11: "9 этажей", 1: "10 этажей", 2: "10-20 этажей", 4: "20+ этажей"
            }[x],
            index=4,
            key="type_floors"
        )
        price = st.number_input("Цена (TRY)", min_value=0, value=500000, step=10000, key="type_price")

    with col2:
        city = st.selectbox(
            "Город",
            options=list(CITY_MAPPING.keys()),
            format_func=lambda x: CITY_MAPPING[x],
            index=0,
            key="type_city"
        )
        sub_type = st.selectbox(
            "Тип недвижимости",
            options=list(SUBTYPE_MAPPING.keys()),
            format_func=lambda x: SUBTYPE_MAPPING[x],
            index=0,
            key="type_subtype"
        )
        building_age = st.selectbox(
            "Возраст здания",
            options=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
            format_func=lambda x: {
                0: "0 лет (Новостройка)", 1: "1 год", 4: "2 года", 7: "3 года",
                10: "4 года", 12: "5 лет", 13: "6-10 лет", 2: "11-15 лет",
                3: "16-20 лет", 5: "21-25 лет", 6: "26-30 лет", 8: "31-35 лет",
                9: "36-40 лет", 11: "40+ лет"
            }[x],
            index=0,
            key="type_age"
        )
        heating_type = st.selectbox(
            "Тип отопления",
            options=list(HEATING_TYPE_MAPPING.keys()),
            format_func=lambda x: HEATING_TYPE_MAPPING[x],
            index=8,
            key="type_heating"
        )

    if st.button("Предсказать тип объявления", type="primary"):
        data = {
            "type": 0,
            "sub_type": sub_type,
            "listing_type": 2,
            "tom": 30,
            "building_age": building_age,
            "total_floor_count": total_floor_count,
            "floor_no": 2,
            "size": size,
            "heating_type": heating_type,
            "city": city,
            "total_rooms": total_rooms,
            "price": price
        }

        with st.spinner("Определяем тип объявления..."):
            result = call_api("/predict-listing-type", data)

            if result and "predictions" in result:
                predictions = result["predictions"]
                st.success(f"### Наиболее вероятный тип: **{predictions[0]['listing_type']}**")

                st.subheader("Вероятности по всем типам:")
                prob_df = pd.DataFrame(predictions)
                prob_df['probability'] = prob_df['probability'].apply(lambda x: f"{x:.2%}")
                st.dataframe(prob_df[['listing_type', 'probability']], use_container_width=True)

            elif result and "error" in result:
                st.error(f"Ошибка: {result['error']}")


else:  # Руководство пользователя
    st.title("Руководство пользователя")

    st.markdown("""
    ## 🏠 Предсказать недвижимость - Руководство

    ### 📋 О приложении
    Приложение для предсказания:
    - **Цены недвижимости** на основе параметров
    - **Типа объявления** (аренда/продажа)

    ### 🎯 Как использовать

    #### 1. Предсказание цены
    - Заполните параметры жилья (без цены)
    - Нажмите "Предсказать цену"
    - Получите оценку стоимости в TRY

    #### 2. Предсказание типа объявления  
    - Введите характеристики + цену
    - Узнайте, для аренды или продажи недвижимость

    ### ⚠️ Важно
    - Модели обучены на турецких данных
    - Для точных результатов используйте актуальные параметры
    """)