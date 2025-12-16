import streamlit as st
import pandas as pd
import numpy as np

# --- 設定網頁標題 ---
st.set_page_config(page_title="富邦 U系列試算工具", page_icon="📊")
st.title("📊 U系列加強版 - 利益試算工具")
st.markdown("### 專為團隊設計的快速試算系統")

# --- 內建費率表資料 (免上傳) ---
DATA_DICT = {
    '年齡': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110], 
    '男性': [0.27, 0.16, 0.14, 0.12, 0.1, 0.1, 0.09, 0.09, 0.1, 0.1, 0.1, 0.11, 0.13, 0.15, 0.19, 0.25, 0.28, 0.32, 0.34, 0.36, 0.36, 0.37, 0.38, 0.39, 0.39, 0.41, 0.42, 0.43, 0.45, 0.47, 0.55, 0.58, 0.62, 0.67, 0.73, 0.81, 0.87, 0.97, 1.06, 1.16, 1.27, 1.39, 1.51, 1.64, 1.78, 2.01, 2.17, 2.34, 2.52, 2.71, 2.89, 3.1, 3.32, 3.56, 3.82, 4.22, 4.51, 4.84, 5.19, 5.57, 6.22, 6.67, 7.18, 7.74, 8.37, 9.39, 10.19, 11.12, 12.18, 13.36, 15.42, 16.86, 18.43, 20.14, 22.02, 23.9, 26.17, 28.66, 31.41, 34.4, 37.65, 41.15, 44.93, 49.04, 53.53, 58.46, 63.9, 69.89, 76.25, 82.96, 90.68, 99.6, 108.45, 118.1, 128.61, 140.07, 152.57, 166.19, 181.04, 197.23, 214.87, 233.56, 252.82, 273.28, 294.95, 317.8, 352.52, 390.26, 427.12, 465.49, 833.33], 
    '女性': [0.21, 0.12, 0.1, 0.09, 0.08, 0.07, 0.07, 0.07, 0.06, 0.06, 0.06, 0.06, 0.06, 0.07, 0.08, 0.11, 0.12, 0.13, 0.14, 0.15, 0.15, 0.16, 0.16, 0.17, 0.17, 0.2, 0.21, 0.22, 0.23, 0.24, 0.26, 0.28, 0.3, 0.32, 0.34, 0.37, 0.4, 0.43, 0.46, 0.5, 0.55, 0.59, 0.64, 0.69, 0.74, 0.85, 0.91, 0.98, 1.05, 1.13, 1.19, 1.27, 1.37, 1.46, 1.56, 1.8, 1.92, 2.06, 2.22, 2.41, 2.77, 3.0, 3.27, 3.57, 3.91, 4.67, 5.12, 5.66, 6.27, 6.97, 8.1, 9.0, 10.04, 11.21, 12.54, 13.61, 15.26, 17.12, 19.18, 21.47, 23.99, 26.76, 29.82, 33.22, 37.01, 41.28, 46.09, 51.51, 57.6, 64.4, 71.99, 80.42, 89.76, 100.11, 111.53, 124.14, 138.04, 153.31, 170.05, 188.36, 208.32, 229.99, 253.43, 278.66, 305.67, 334.39, 374.03, 415.61, 463.77, 516.22, 833.33]
}
df_rates = pd.DataFrame(DATA_DICT)

# --- 側邊欄：輸入參數 ---
st.sidebar.header("📝 投保條件設定")

# 參數輸入
age = st.sidebar.number_input("投保年齡", min_value=0, max_value=80, value=30)
gender = st.sidebar.selectbox("性別", ["男性", "女性"])
target_premium = st.sidebar.number_input("目標保險費 (年繳)", value=120000, step=1000)
basic_sum_assured = st.sidebar.number_input("基本保額 (元)", value=12000000, step=100000)
payment_term = st.sidebar.slider("繳費年期", 6, 30, 20)
interest_rate = st.sidebar.number_input("假設宣告利率 (%)", value=8.0, step=0.1) / 100

# --- 核心計算邏輯 ---
def calculate_projection(rates_df, age, gender, target_premium, basic_sum_assured, payment_term, interest_rate):
    expense_rates = [0.58, 0.33, 0.23, 0.13, 0.13]
    results = []
    account_value = 0
    current_age = age
    gender_col = '男性' if gender == '男性' else '女性'
    max_years = 110 - age + 1  # 試算至110歲
    
    for year in range(1, max_years + 1):
        gross_premium = target_premium if year <= payment_term else 0
        
        # 保費費用
        if year <= 5:
            premium_expense = gross_premium * expense_rates[year-1]
        else:
            premium_expense = 0
        
        # 管理費
        admin_fee = 1200
        
        # 危險成本
        try:
            rate_row = rates_df[rates_df['年齡'] == current_age]
            if not rate_row.empty:
                raw_rate = rate_row[gender_col].values[0]
            else:
                raw_rate = rates_df[gender_col].max()
        except KeyError:
            return None

        coi_loading = 1.2
        net_amount_at_risk = max(0, basic_sum_assured - account_value)
        insurance_cost = net_amount_at_risk * (raw_rate / 1000) * coi_loading
        
        # 帳戶價值計算
        net_premium = gross_premium - premium_expense
        balance_before_interest = account_value + net_premium - admin_fee - insurance_cost
        if balance_before_interest < 0: balance_before_interest = 0
        
        account_value_end = balance_before_interest * (1 + interest_rate)
        death_benefit = max(basic_sum_assured, account_value_end)
        
        results.append({
            '年度': year,
            '年齡': current_age,
            '實繳保費': gross_premium,
            '保費費用': int(premium_expense),
            '危險成本': int(insurance_cost),
            '帳戶價值': int(account_value_end),
            '身故保險金': int(death_benefit)
        })
        
        account_value = account_value_end
        current_age += 1
        
        # 只有在繳費期滿後且帳戶價值歸零才停止
        if account_value <= 0 and year > payment_term:
            break
    
    return pd.DataFrame(results)

# --- 執行計算與顯示 ---
if st.sidebar.button("🚀 開始試算"):
    df_result = calculate_projection(df_rates, age, gender, target_premium, basic_sum_assured, payment_term, interest_rate)
    
    if df_result is not None:
        st.subheader(f"📋 試算結果 ({age}歲 {gender})")
        
        # 顯示重要指標 (Metrics)
        col1, col2, col3 = st.columns(3)
        total_paid = df_result['實繳保費'].sum()
        
        # 找出第20年的資料，若無則取最後一年
        if len(df_result) >= 20:
            val_20th = df_result.iloc[19]['帳戶價值']
        else:
            val_20th = 0
            
        col1.metric("總繳保費", f"{total_paid:,.0f}")
        col2.metric("第20年帳戶價值", f"{val_20th:,.0f}")
        col3.metric("保額維持至", f"{df_result.iloc[-1]['年齡']} 歲")

        # 顯示表格
        st.dataframe(df_result, use_container_width=True)
        
        # 畫圖
        st.line_chart(df_result, x='年齡', y=['帳戶價值', '身故保險金'])
    else:
        st.error("❌ 計算錯誤")
else:
    st.info("👈 請在左側輸入條件並點擊「開始試算」")
