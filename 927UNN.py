import streamlit as st
import pandas as pd
import numpy as np

# --- 設定網頁標題 ---
st.set_page_config(page_title="富邦 U系列試算工具", page_icon="📊")
st.title("📊 U系列加強版 - 利益試算工具")
st.markdown("### 專為團隊設計的快速試算系統")

# --- 側邊欄：輸入參數 ---
st.sidebar.header("📝 投保條件設定")

uploaded_file = st.sidebar.file_uploader("請上傳 '費率表.csv'", type=['csv'])

if uploaded_file is not None:
    try:
        # 嘗試讀取上傳的檔案
        df_rates = pd.read_csv(uploaded_file)
        st.sidebar.success("✅ 費率表讀取成功！")
        
        # 參數輸入
        age = st.sidebar.number_input("投保年齡", min_value=0, max_value=80, value=30)
        gender = st.sidebar.selectbox("性別", ["男性", "女性"])
        target_premium = st.sidebar.number_input("目標保險費 (年繳)", value=120000, step=1000)
        basic_sum_assured = st.sidebar.number_input("基本保額 (元)", value=12000000, step=100000)
        payment_term = st.sidebar.slider("繳費年期", 6, 30, 20)
        interest_rate = st.sidebar.number_input("假設宣告利率 (%)", value=8.0, step=0.1) / 100

        # --- 核心計算邏輯 (與之前相同) ---
        def calculate_projection(rates_df, age, gender, target_premium, basic_sum_assured, payment_term, interest_rate):
            expense_rates = [0.58, 0.33, 0.23, 0.13, 0.13]
            results = []
            account_value = 0
            current_age = age
            gender_col = '男性' if gender == '男性' else '女性'
            max_years = 100 - age + 1
            
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
                    return None # 錯誤處理

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
                final_av = df_result.iloc[-1]['帳戶價值']
                
                col1.metric("總繳保費", f"{total_paid:,.0f}")
                col2.metric("第20年帳戶價值", f"{df_result.iloc[19]['帳戶價值']:,.0f}" if len(df_result) >= 20 else "N/A")
                col3.metric("保額維持至", f"{df_result.iloc[-1]['年齡']} 歲")

                # 顯示表格
                st.dataframe(df_result, use_container_width=True)
                
                # 畫圖 (選用)
                st.line_chart(df_result, x='年齡', y=['帳戶價值', '身故保險金'])
            else:
                st.error("❌ 計算錯誤：費率表格式可能不符，請確認欄位包含 '年齡', '男性', '女性'")

    except Exception as e:
        st.error(f"❌ 檔案讀取失敗: {e}")
else:
    st.info("👈 請從左側側邊欄上傳 '費率表.csv' 檔案以開始使用")
    st.warning("注意：這是雲端版本，請確保 CSV 檔案格式正確。")
