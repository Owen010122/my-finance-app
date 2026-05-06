import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime, date
import os

# ====================== 設定 ======================
st.set_page_config(page_title="我的記賬本", layout="wide")
st.title("💰 我的收入支出記賬本")

# 多語言支援
if "language" not in st.session_state:
    st.session_state.language = "zh"

def t(text_zh, text_en):
    return text_zh if st.session_state.language == "zh" else text_en

# ====================== 資料庫 ======================
DB_FILE = "finance.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            type TEXT NOT NULL,          -- income / expense
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_data():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM transactions ORDER BY date DESC", conn)
    conn.close()
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
    return df

def add_transaction(date_val, typ, cat, amt, desc):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("INSERT INTO transactions (date, type, category, amount, description) VALUES (?, ?, ?, ?, ?)",
                 (date_val, typ, cat, amt, desc))
    conn.commit()
    conn.close()

def delete_all_data():
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    init_db()

# ====================== 側邊欄 ======================
with st.sidebar:
    st.header(t("導航", "Navigation"))
    page = st.radio(t("選擇頁面", "Select Page"),
                    [t("首頁", "Home"), t("記賬", "Add Record"), 
                     t("明細", "Transactions"), t("統計", "Statistics"), t("設定", "Settings")])
    
    st.divider()
    if st.button(t("切換語言 / Switch Language", "切換語言 / Switch Language")):
        st.session_state.language = "en" if st.session_state.language == "zh" else "zh"
        st.rerun()

# ====================== 首頁 ======================
if page == t("首頁", "Home"):
    df = get_data()
    st.header(t("最近一個月概覽", "Recent Month Overview"))
    
    if df.empty:
        st.info(t("尚無記錄，請先記賬", "No records yet. Please add some transactions."))
    else:
        today = date.today()
        first_day = today.replace(day=1)
        last_month = (first_day - pd.Timedelta(days=1)).replace(day=1)
        
        recent = df[df['date'].dt.date >= first_day]
        income = recent[recent['type'] == 'income']['amount'].sum()
        expense = recent[recent['type'] == 'expense']['amount'].sum()
        balance = income - expense
        
        col1, col2, col3 = st.columns(3)
        col1.metric(t("收入", "Income"), f"¥{income:,.2f}")
        col2.metric(t("支出", "Expense"), f"¥{expense:,.2f}")
        col3.metric(t("結餘", "Balance"), f"¥{balance:,.2f}", delta=f"¥{balance:,.2f}")
        
        st.subheader(t("最佳交易記錄（最高金額）", "Top Transactions"))
        if not recent.empty:
            top = recent.nlargest(5, 'amount')
            st.dataframe(top[['date', 'type', 'category', 'amount', 'description']], use_container_width=True)

# ====================== 記賬 ======================
elif page == t("記賬", "Add Record"):
    st.header(t("新增記錄", "Add New Record"))
    
    with st.form("add_form"):
        col1, col2 = st.columns(2)
        with col1:
            trans_date = st.date_input(t("日期", "Date"), value=date.today())
            trans_type = st.selectbox(t("類型", "Type"), [t("收入", "Income"), t("支出", "Expense")])
        with col2:
            amount = st.number_input(t("金額 (元)", "Amount (¥)"), min_value=0.01, step=0.01)
            if trans_type == t("收入", "Income"):
                categories = ["薪資", "獎金", "投資", "其他收入"]
            else:
                categories = ["飲食", "交通", "購物", "房租", "娛樂", "醫療", "其他支出"]
            category = st.selectbox(t("分類", "Category"), categories)
        
        description = st.text_input(t("備註", "Notes"), "")
        
        submitted = st.form_submit_button(t("儲存記錄", "Save Record"))
        if submitted and amount > 0:
            typ = "income" if trans_type == t("收入", "Income") else "expense"
            add_transaction(trans_date.strftime("%Y-%m-%d"), typ, category, amount, description)
            st.success(t("記錄已儲存！", "Record saved successfully!"))
            st.rerun()

# ====================== 明細 ======================
elif page == t("明細", "Transactions"):
    st.header(t("所有交易明細", "All Transactions"))
    df = get_data()
    if df.empty:
        st.info(t("尚無記錄", "No records yet."))
    else:
        # 篩選
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(t("開始日期", "Start Date"), value=date.today().replace(day=1))
        with col2:
            end_date = st.date_input(t("結束日期", "End Date"), value=date.today())
        
        mask = (df['date'].dt.date >= start_date) & (df['date'].dt.date <= end_date)
        filtered = df[mask].copy()
        filtered['type'] = filtered['type'].map({'income': t("收入", "Income"), 'expense': t("支出", "Expense")})
        
        st.dataframe(filtered[['date', 'type', 'category', 'amount', 'description']], 
                     use_container_width=True, hide_index=True)

# ====================== 統計 ======================
elif page == t("統計", "Statistics"):
    st.header(t("統計分析", "Statistics"))
    df = get_data()
    if df.empty:
        st.info(t("尚無資料", "No data yet."))
    else:
        # 月度/年度
        df['month'] = df['date'].dt.to_period('M').astype(str)
        df['year'] = df['date'].dt.year
        
        tab1, tab2 = st.tabs([t("月度統計", "Monthly"), t("年度統計", "Yearly")])
        
        with tab1:
            monthly = df.groupby(['month', 'type'])['amount'].sum().unstack(fill_value=0)
            st.plotly_chart(px.bar(monthly, title=t("每月收入 vs 支出", "Monthly Income vs Expense")), use_container_width=True)
            
            # 分類統計
            st.subheader(t("支出分類餅圖", "Expense by Category"))
            expense_cat = df[df['type']=='expense'].groupby('category')['amount'].sum()
            if not expense_cat.empty:
                st.plotly_chart(px.pie(expense_cat.reset_index(), names='category', values='amount'), 
                              use_container_width=True)
        
        with tab2:
            yearly = df.groupby(['year', 'type'])['amount'].sum().unstack(fill_value=0)
            st.plotly_chart(px.bar(yearly, title=t("年度收入 vs 支出", "Yearly Income vs Expense")), use_container_width=True)

# ====================== 設定 ======================
elif page == t("設定", "Settings"):
    st.header(t("設定", "Settings"))
    
    st.subheader(t("資料管理", "Data Management"))
    if st.button(t("匯出所有資料 (CSV)", "Export All Data (CSV)"), type="primary"):
        df = get_data()
        if not df.empty:
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("下載 CSV", csv, "transactions.csv", "text/csv")
        else:
            st.warning(t("沒有資料可匯出", "No data to export"))
    
    if st.button(t("⚠️ 清空所有資料", "⚠️ Clear All Data"), type="secondary"):
        if st.checkbox(t("我確定要清空所有資料，此操作不可逆！", "I confirm I want to delete ALL data permanently!")):
            delete_all_data()
            st.success(t("資料已清空", "All data cleared!"))
            st.rerun()

st.caption("Made with ❤️ for 鹏")