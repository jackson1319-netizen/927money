import pandas as pd
import numpy as np

def calculate_ul_projection(
    age, 
    gender, 
    target_premium, 
    basic_sum_assured, 
    payment_term=20, 
    interest_rate=0.08, 
    rate_table_path='U系列加強版.xlsx - 費率表.csv'
):
    """
    計算萬能壽險的利益試算表 (仿照 U系列加強版 邏輯)
    
    Parameters:
    -----------
    age : int
        投保年齡
    gender : str
        '男性' or '女性'
    target_premium : float
        目標保險費 (年繳)
    basic_sum_assured : float
        基本保額 (元)
    payment_term : int
        繳費年期
    interest_rate : float
        假設宣告利率 (如 0.08)
    rate_table_path : str
        費率表 CSV 檔案路徑
        
    Returns:
    --------
    pd.DataFrame
        包含年度、年齡、保費、費用、成本、帳戶價值的試算表
    """
    
    # 1. 載入費率表 📋
    try:
        rates_df = pd.read_csv(rate_table_path)
    except FileNotFoundError:
        return "❌ 找不到費率表檔案，請確認路徑。"

    # 設定費用率 (前五年)
    expense_rates = [0.58, 0.33, 0.23, 0.13, 0.13]
    
    # 初始化變數
    results = []
    account_value = 0
    current_age = age
    
    # 費率表欄位對應
    gender_col = '男性' if gender == '男性' else '女性'
    
    # 模擬 100 歲或更長
    max_simulation_years = 100 - age + 1
    
    for year in range(1, max_simulation_years + 1):
        # 2. 決定當年度保費 💰
        gross_premium = target_premium if year <= payment_term else 0
        
        # 3. 計算保費費用 (Premium Expense) 📉
        if year <= 5:
            exp_rate = expense_rates[year-1]
            premium_expense = gross_premium * exp_rate
        else:
            premium_expense = 0
            
        # 4. 保單管理費 (Admin Fee) - 假設固定 100/月 = 1200/年 🛠️
        # 若保單失效或帳戶價值不足，邏輯可能需調整，此處簡化為固定扣除
        admin_fee = 1200
        
        # 5. 取得危險費率 (COI Rate) ⚠️
        # 從費率表查找對應年齡的費率
        try:
            rate_row = rates_df[rates_df['年齡'] == current_age]
            if not rate_row.empty:
                raw_rate = rate_row[gender_col].values[0]
            else:
                # 若超過費率表年齡，假設費率隨年齡增長或維持最高
                raw_rate = rates_df[gender_col].max() 
        except KeyError:
            return f"❌ 費率表中找不到 '{gender_col}' 欄位"

        # 6. 計算危險成本 (Insurance Cost) 💸
        # 邏輯推導：COI = (淨危險保額) * (費率/1000) * 調整係數(約1.2)
        # 淨危險保額 (NAR) = 保額 - 帳戶價值 (但在Excel中似乎是基於期初或未扣除前的數字)
        # 這裡採用簡化的年度計算
        
        coi_loading = 1.2 # 根據數據反推的調整係數
        
        # 確保 NAR 不為負
        net_amount_at_risk = max(0, basic_sum_assured - account_value)
        
        insurance_cost = net_amount_at_risk * (raw_rate / 1000) * coi_loading
        
        # 7. 計算帳戶價值 (Account Value) 📈
        # 公式：(期初AV + 淨保費 - 管理費 - 危險成本) * (1 + 利率)
        # 淨保費 = 總保費 - 保費費用
        
        net_premium = gross_premium - premium_expense
        
        balance_before_interest = account_value + net_premium - admin_fee - insurance_cost
        
        # 簡單處理：若餘額不足扣除成本，保單可能停效
        if balance_before_interest < 0:
            balance_before_interest = 0 # 或處理停效邏輯
            
        account_value_end = balance_before_interest * (1 + interest_rate)
        
        # 身故金 = Max(保額, 帳戶價值)
        death_benefit = max(basic_sum_assured, account_value_end)
        
        # 儲存結果
        results.append({
            '年度': year,
            '年齡': current_age,
            '目標保險費': gross_premium,
            '保費費用': premium_expense,
            '保單管理費': admin_fee,
            '保險成本': round(insurance_cost, 2),
            '保單帳戶價值': round(account_value_end, 2),
            '身故金': round(death_benefit, 2)
        })
        
        # 更新下一年變數
        account_value = account_value_end
        current_age += 1
        
        # 若帳戶價值歸零，停止模擬 (視商品條款而定)
        if account_value <= 0 and year > payment_term:
            break

    return pd.DataFrame(results)

# --- 使用範例 ---
# 假設要跑一個 31歲男性的試算
# 請確保目錄下有 'U系列加強版.xlsx - 費率表.csv'
# df_result = calculate_ul_projection(
#     age=31, 
#     gender='男性', 
#     target_premium=120000, 
#     basic_sum_assured=12000000, # 1200萬
#     payment_term=20,
#     interest_rate=0.08
# )

# print(df_result.head(10))
# df_result.to_csv('Python_UL_Projection.csv', index=False, encoding='utf-8-sig')
