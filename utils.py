import pandas as pd
import json

def load_policy_data(csv_path="PDATA.csv"):
    """
    解析富邦 PDATA.csv 轉換為 Streamlit 可用的字典格式
    """
    # 讀取 CSV，不帶 Header，因為格式混亂
    df = pd.read_csv(csv_path, header=None)
    
    data = {
        "premium_rate": {},  # { "gender_age": rate }
        "death_benefit": {}, # { "gender_age": [year1, year2...] }
        "cash_value": {}     # { "gender_age": [year1, year2...] }
    }
    
    # --------------------------
    # 1. 解析保費 (Premium)
    # --------------------------
    # 假設保費表在最上方，直到遇到 'DIE' 標記
    # 欄位索引: 性別=5, 年齡=7, 保費=10 (根據您的檔案結構)
    try:
        die_start_idx = df[df[129] == 'DIE'].index[0]
    except IndexError:
        die_start_idx = 444 # Fallback
        
    premium_df = df.iloc[1:die_start_idx]
    for _, row in premium_df.iterrows():
        try:
            sex = int(row[5]) # 1=男, 2=女
            age = int(row[7])
            rate = float(row[10])
            key = f"{sex}_{age}"
            data["premium_rate"][key] = rate
        except:
            continue

    # --------------------------
    # 2. 解析身故金 (DIE)
    # --------------------------
    # DIE 表格從 die_start_idx + 2 開始 (跳過 Header)
    # 欄位索引: 性別=131, 年齡=132, 數值從 134 開始
    # 我們需要找到下一個區塊的開始 (PV0 或 PV) 來停止
    try:
        pv_start_idx = df[df[129] == 'PV0'].index[0] # 或 'PV'
    except IndexError:
        pv_start_idx = 867 # Fallback
        
    die_df = df.iloc[die_start_idx+2 : pv_start_idx]
    for _, row in die_df.iterrows():
        try:
            sex = int(row[131])
            age = int(row[132])
            # 抓取第1年到第100年 (假設 col 134 開始是第1年)
            values = row[134:].dropna().tolist()
            # 轉換為 float
            values = [float(str(v).replace(',', '')) for v in values]
            key = f"{sex}_{age}"
            data["death_benefit"][key] = values
        except:
            continue

    # --------------------------
    # 3. 解析解約金/保價金 (PV)
    # --------------------------
    # 搜尋 PV 標籤
    try:
        real_pv_start = df[df[129] == 'PV'].index[0]
    except IndexError:
        real_pv_start = 1737 # Fallback
    
    pv_df = df.iloc[real_pv_start+2 :]
    for _, row in pv_df.iterrows():
        try:
            sex = int(row[131])
            age = int(row[132])
            values = row[134:].dropna().tolist()
            values = [float(str(v).replace(',', '')) for v in values]
            key = f"{sex}_{age}"
            data["cash_value"][key] = values
        except:
            continue
            
    return data

# --- Streamlit 計算邏輯 ---
def calculate_policy(age, gender, amount, data):
    """
    age: 投保年齡
    gender: 1 (男) or 2 (女)
    amount: 投保保額 (例如 100萬)
    data: 上面 load_policy_data 產出的字典
    """
    unit_base = 10000 # 假設費率是每萬元
    key = f"{gender}_{age}"
    
    # 1. 算保費
    rate = data["premium_rate"].get(key, 0)
    premium = (amount / unit_base) * rate
    
    # 2. 算歷年數值
    db_table = data["death_benefit"].get(key, [])
    cv_table = data["cash_value"].get(key, [])
    
    results = []
    years = min(len(db_table), len(cv_table))
    
    for t in range(years):
        policy_year = t + 1
        
        # 查表值 * (保額/單位)
        guaranteed_db = (amount / unit_base) * db_table[t]
        guaranteed_cv = (amount / unit_base) * cv_table[t]
        
        results.append({
            "保單年度": policy_year,
            "年齡": age + policy_year,
            "累積保費": premium * min(policy_year, 6), # 假設6年期
            "身故保險金": guaranteed_db,
            "解約金(保價)": guaranteed_cv
        })
        
    return premium, pd.DataFrame(results)
