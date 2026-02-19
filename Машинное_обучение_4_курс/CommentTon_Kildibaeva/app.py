import streamlit as st
import requests
import pandas as pd

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Анализ тональности комментариев",
    page_icon="💬",
    layout="wide"
)

st.title("💬 Анализ тональности комментариев")

tab1, tab2 = st.tabs(["📋 Все комментарии", "✏️ Проверить текст"])


@st.cache_data(ttl=60)
def get_comment_probability(comment_id):
    try:
        response = requests.post(f"{API_URL}/comments/{comment_id}/predict", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                'toxic_prob': data['probability'],
                'positive_prob': 1 - data['probability']
            }
    except:
        pass
    return None


with tab1:
    st.header("📋 Все комментарии")
    with st.spinner("Загрузка комментариев..."):
        response = requests.get(f"{API_URL}/comments")

    if response.status_code == 200:
        comments = response.json()
        if comments:
            df = pd.DataFrame(comments)

            display_data = []

            progress_bar = st.progress(0)
            status_text = st.empty()

            for idx, row in df.iterrows():
                status_text.text(f"Загрузка вероятностей: {idx + 1}/{len(df)}")

                comment_info = {
                    'ID': row['comment_id'],
                    'Текст комментария': row['comment_text'][:100] + "..." if len(row['comment_text']) > 100 else row[
                        'comment_text'],
                    'Тональность': row['comment_ton']
                }

                if pd.notna(row['comment_ton']):
                    prob_data = get_comment_probability(row['comment_id'])
                    if prob_data:
                        if row['comment_ton'] == 0:
                            comment_info[
                                'Тональность с вероятностью'] = f"✅ Позитивный ({prob_data['positive_prob']:.2%})"
                        else:
                            comment_info['Тональность с вероятностью'] = f"🔴 Токсичный ({prob_data['toxic_prob']:.2%})"
                    else:
                        comment_info['Тональность с вероятностью'] = "✅ Позитивный" if row[
                                                                                           'comment_ton'] == 0 else "🔴 Токсичный"
                else:
                    comment_info['Тональность с вероятностью'] = "⏳ Не определен"

                display_data.append(comment_info)
                progress_bar.progress((idx + 1) / len(df))

            progress_bar.empty()
            status_text.empty()

            df_display = pd.DataFrame(display_data)

            st.dataframe(
                df_display[['ID', 'Текст комментария', 'Тональность с вероятностью']],
                use_container_width=True,
                column_config={
                    "ID": "ID",
                    "Текст комментария": "Текст комментария",
                    "Тональность с вероятностью": "Тональность"
                }
            )

            pending = len(df[df['comment_ton'].isna()])
            if pending > 0:
                st.info(f"📊 Необработанных комментариев: {pending}")

                col1, col2, col3 = st.columns(3)
                with col2:
                    if st.button("🧠 Проанализировать все", use_container_width=True):
                        with st.spinner("Анализ комментариев..."):
                            resp = requests.post(f"{API_URL}/predict/all")
                            if resp.status_code == 200:
                                st.success(f"✅ {resp.json()['message']}")
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error("❌ Ошибка анализа")
        else:
            st.warning("Нет комментариев")
    else:
        st.error("Ошибка загрузки")

with tab2:
    st.header("✏️ Проверить тональность текста")

    st.markdown("Введите текст комментария для анализа его тональности:")

    user_text = st.text_area("Текст комментария", height=150, placeholder="Введите комментарий для анализа...",
                             key="text_input")

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        analyze_button = st.button("🔮 Анализировать", use_container_width=True)

    if analyze_button and user_text:
        with st.spinner("Анализ текста..."):
            try:
                response = requests.post(
                    f"{API_URL}/predict/text",
                    params={"text": user_text},
                    timeout=10)

                if response.status_code == 200:
                    result = response.json()

                    col_res1, col_res2 = st.columns(2)

                    with col_res1:
                        st.markdown("### 📊 Результат анализа")

                        if result['sentiment'] == "токсичный":
                            sentiment_display = "🔴 Токсичный"
                            prob_value = result['probability']
                            other_prob = 1 - prob_value
                            other_sentiment = "✅ Позитивный"
                        else:
                            sentiment_display = "✅ Позитивный"
                            prob_value = 1 - result['probability']
                            other_prob = result['probability']
                            other_sentiment = "🔴 Токсичный"

                        st.metric("Тональность", sentiment_display)
                        st.metric("Уверенность", f"{prob_value:.2%}")
                        st.metric(f"Шанс на {other_sentiment}", f"{other_prob:.2%}")
                else:
                    st.error(f"❌ Ошибка при анализе: {response.status_code}")
            except Exception as e:
                st.error(f"❌ Неизвестная ошибка: {str(e)}")

    elif analyze_button and not user_text:
        st.warning("⚠️ Введите текст для анализа")
