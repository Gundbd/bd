import streamlit as st
import psycopg2
import pandas as pd
import warnings

# Конфигурация
st.set_page_config(page_title="GosMonety", layout="wide")
warnings.filterwarnings('ignore')

# --- НАСТРОЙКИ БАЗЫ ДАННЫХ ---
DB_HOST = "localhost"
DB_NAME = "money" 
DB_USER = "postgres"
DB_PASS = "12321"

def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME, 
        user=DB_USER,
        password=DB_PASS,
        options='-c client_encoding=UTF8'
    )

# ==========================================
# ОСНОВНОЕ ПРИЛОЖЕНИЕ
# ==========================================
st.title("🪙 База данных: Коллекционеры и Монеты")

# Обновленное меню (добавил 2 пункта)
menu = st.sidebar.selectbox("Выберите раздел", [
    "Монеты и владельцы (View)", 
    "Доступные монеты (View)", 
    "Умный каталог (Фильтры/Сортировка)",
    "Добавить монету",
    "Добавить коллекционера",            # НОВОЕ
    "Выдать монету (Добавить запись)",   # НОВОЕ
    "Все коллекционеры"
])

# --- 1. ВЫЗЫВАЕМ ПРЕДСТАВЛЕНИЕ ИЗ БАЗЫ ---
if menu == "Монеты и владельцы (View)":
    st.subheader("Связь монет и коллекционеров")
    conn = get_connection()
    df = pd.read_sql('SELECT * FROM cns.v_coins_with_owners', conn)
    conn.close()
    df['owner_name'] = df['owner_name'].fillna('🟢 Доступна (нет владельца)')
    st.dataframe(df, use_container_width=True)

# --- 2. ВЫЗЫВАЕМ ПРЕДСТАВЛЕНИЕ СВОБОДНЫХ МОНЕТ ---
elif menu == "Доступные монеты (View)":
    st.subheader("Монеты, которые никому не принадлежат")
    conn = get_connection()
    df = pd.read_sql('SELECT * FROM cns.v_available_coins', conn)
    conn.close()
    st.dataframe(df, use_container_width=True)

# --- 3. УМНЫЙ КАТАЛОГ ---
elif menu == "Умный каталог (Фильтры/Сортировка)":
    st.subheader("Настройте выборку под себя")
    conn = get_connection()
    countries = pd.read_sql("SELECT name FROM cns.country", conn)
    metals = pd.read_sql("SELECT name FROM cns.metal", conn)
    conn.close()

    col1, col2, col3 = st.columns(3)
    with col1:
        filter_country = st.selectbox("Страна", ["Все"] + countries['name'].tolist())
    with col2:
        filter_metal = st.selectbox("Металл", ["Все"] + metals['name'].tolist())
    with col3:
        sort_by = st.selectbox("Сортировать по", ["ID", "Номинал", "Вес", "Год"])
        sort_order = st.radio("Порядок", ["По возрастанию", "По убыванию"], horizontal=True)

    query = """
        SELECT c.id, co.name AS country, m.name AS metal, 
               c.denomination, c.weight, EXTRACT(YEAR FROM c.year) AS year
        FROM cns.coins c
        JOIN cns.country co ON c.id_country = co.id
        JOIN cns.metal m ON c.id_metal = m.id
        WHERE 1=1
    """
    if filter_country != "Все": query += f" AND co.name = '{filter_country}'"
    if filter_metal != "Все": query += f" AND m.name = '{filter_metal}'"

    sort_map = {"ID": "c.id", "Номинал": "c.denomination", "Вес": "c.weight", "Год": "year"}
    order = "ASC" if sort_order == "По возрастанию" else "DESC"
    query += f" ORDER BY {sort_map[sort_by]} {order}"

    conn = get_connection()
    df = pd.read_sql(query, conn)
    conn.close()
    st.write(f"**Найдено записей:** {len(df)}")
    st.dataframe(df, use_container_width=True)

# --- 4. ДОБАВЛЕНИЕ МОНЕТЫ ---
elif menu == "Добавить монету": 
    st.subheader("Добавить новую монету в базу")
    with st.form("add_coin_form"):
        conn = get_connection()
        countries = pd.read_sql("SELECT id, name FROM cns.country", conn)
        metals = pd.read_sql("SELECT id, name FROM cns.metal", conn)
        conn.close()

        col1, col2 = st.columns(2)
        with col1:
            selected_country = st.selectbox("Страна", countries['name'])
            country_id = int(countries[countries['name'] == selected_country]['id'].values[0])
            selected_metal = st.selectbox("Металл", metals['name'])
            metal_id = int(metals[metals['name'] == selected_metal]['id'].values[0])
        with col2: 
            denomination = float(st.number_input("Номинал", min_value=0.01, step=0.01))
            weight = float(st.number_input("Вес", min_value=0.001, step=0.001))
            year = st.date_input("Год выпуска монеты")
        
        feautures = st.text_area("Описание", placeholder="Памятная монета...")
        submitted = st.form_submit_button("💾 Сохранить монету в БД")

        if submitted:
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO cns.coins (id_country, id_metal, denomination, weight, year, feautures)
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', (country_id, metal_id, denomination, weight, year, feautures))
                conn.commit()
                st.success(f"Монета номиналом {denomination} успешно добавлена!")
                cursor.close(); conn.close()
            except Exception as e: 
                st.error(f"Ошибка базы данных: {e}")

# --- 5. НОВОЕ: ДОБАВЛЕНИЕ КОЛЛЕКЦИОНЕРА ---
elif menu == "Добавить коллекционера":
    st.subheader("Регистрация нового коллекционера")
    with st.form("add_collector_form"):
        conn = get_connection()
        countries = pd.read_sql("SELECT id, name FROM cns.country", conn)
        conn.close()

        col1, col2 = st.columns(2)
        with col1:
            last_name = st.text_input("Фамилия*")
            first_name = st.text_input("Имя*")
            patronomic = st.text_input("Отчество (можно пустым)")
        with col2:
            selected_country = st.selectbox("Страна*", countries['name'])
            country_id = int(countries[countries['name'] == selected_country]['id'].values[0])
            email = st.text_input("Email (можно пустым)")

        submitted = st.form_submit_button("➕ Зарегистрировать")
        if submitted:
            if not last_name or not first_name:
                st.error("Фамилия и Имя обязательны!")
            else:
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO cns.collectors (last_name, first_name, patronomic, id_country, email)
                        VALUES (%s, %s, %s, %s, %s)
                    ''', (last_name, first_name, patronomic if patronomic else None, country_id, email if email else None))
                    conn.commit()
                    st.success(f"Коллекционер {last_name} {first_name} добавлен!")
                    cursor.close(); conn.close()
                except Exception as e: 
                    st.error(f"Ошибка базы данных: {e}")

# --- 6. НОВОЕ: ДОБАВЛЕНИЕ ЗАПИСИ (ВЫДАЧА МОНЕТЫ) ---
elif menu == "Выдать монету (Добавить запись)":
    st.subheader("Связать монету с коллекционером")
    with st.form("add_record_form"):
        conn = get_connection()
        # Достаем списки для красивых выпадающих меню
        coins_df = pd.read_sql('''
            SELECT c.id, c.denomination || ' (' || m.name || ', ' || co.name || ')' as label 
            FROM cns.coins c 
            JOIN cns.metal m ON c.id_metal = m.id 
            JOIN cns.country co ON c.id_country = co.id
        ''', conn)
        collectors_df = pd.read_sql("SELECT id, last_name || ' ' || first_name AS label FROM cns.collectors", conn)
        sources_df = pd.read_sql("SELECT id, name FROM cns.source", conn)
        conn.close()

        selected_coin = st.selectbox("Какую монету выдаем?", coins_df['label'])
        coin_id = int(coins_df[coins_df['label'] == selected_coin]['id'].values[0])

        selected_collector = st.selectbox("Кому выдаем?", collectors_df['label'])
        collector_id = int(collectors_df[collectors_df['label'] == selected_collector]['id'].values[0])

        selected_source = st.selectbox("Откуда поступила?", sources_df['name'])
        source_id = int(sources_df[sources_df['name'] == selected_source]['id'].values[0])

        submitted = st.form_submit_button("📝 Оформить выдачу")
        if submitted:
            try:
                conn = get_connection()
                cursor = conn.cursor()
                # Дата подставляется автоматически - текущий день
                cursor.execute('''
                    INSERT INTO cns.record (id_coin, id_collector, id_source, date)
                    VALUES (%s, %s, %s, CURRENT_DATE)
                ''', (coin_id, collector_id, source_id))
                conn.commit()
                st.success("Запись успешно добавлена! Монета теперь у коллекционера.")
                cursor.close(); conn.close()
            except Exception as e: 
                st.error(f"Ошибка базы данных: {e}")

# --- 7. СПИСОК КОЛЛЕКЦИОНЕРОВ ---
elif menu == "Все коллекционеры": 
    st.subheader("Все коллекционеры в базе")
    conn = get_connection()
    df = pd.read_sql('SELECT id, last_name, first_name, patronomic, email FROM cns.collectors', conn)
    conn.close()
    st.dataframe(df, use_container_width=True)