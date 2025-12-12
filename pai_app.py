import streamlit as st
import pandas as pd
import numpy as np

# --- 1. 頁面基礎設定 ---
st.set_page_config(
    page_title="PAI 策略全能計算機",
    page_icon="📊",
    layout="wide"
)

# --- 2. CSS 樣式注入 (高度還原 HTML 風格) ---
st.markdown("""
    <style>
    /* 引入富邦色系變數 */
    :root {
        --brand-color: #006d75;
        --brand-bg: #e6fffb;
        --text-main: #262626;
        --pay-text: #389e0d;      /* 綠色 (實繳) */
        --receive-text: #c41d7f;  /* 桃紅 (領回) */
        --debt-color: #cf1322;    /* 紅色 (負債) */
        --asset-bg: #e6f7ff;      /* 淺藍 (資產背景) */
        --asset-text: #096dd9;    /* 深藍 (資產文字) */
    }
    
    /* 調整標題顏色 */
    h1, h2, h3 { color: var(--brand-color) !important; font-family: -apple-system, sans-serif; }
    
    /* 驗證區塊 (黑底樣式) */
    .verify-box {
        background-color: #262626;
        color: white;
        padding: 24px;
        border-radius: 10px;
        margin-top: 24px;
        font-family: monospace;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .verify-title {
        color: #faad14;
        font-weight: bold;
        margin-bottom: 15px;
        border-bottom: 1px solid #434343;
        padding-bottom: 10px;
        font-size: 16px;
    }
    .verify-row { 
        display: flex; 
        justify-content: space-between; 
        margin-bottom: 8px; 
        align-items: center;
    }
    .verify-total { 
        font-size: 20px; 
        font-weight: bold; 
        color: #52c41a; 
        margin-top: 15px; 
        border-top: 1px solid #555; 
        padding-top: 15px; 
        display: flex; 
        justify-content: space-between;
    }
    .verify-note {
        font-size: 13px;
        color: #8c8c8c;
        margin-top: 15px;
        border-top: 1px dashed #434343;
        padding-top: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. 核心資料與函式 ---
PAI_BASE_DATA = [
    0, 75568, 151906, 229013, 306899, 306899, 429482, 549969, 679495, 815609, 960677, 
    1112453, 1273472, 1441892, 1619008, 1804891, 1999194, 2170489, 2345219, 2525180, 2708683, 
    2796023, 2871780, 2949471, 3030006, 3111221, 3194976, 3280911, 3369035, 3459379, 3552969, 
    3646561, 3744237, 3843884, 3945018, 4049162, 4155962, 4264024, 4375249, 4489180, 4605868, 
    4722041, 4843080, 4964110, 5088924, 5215376, 5344037, 5473126, 5604778, 5738463, 5874202, 
    6011861, 6151926, 6292620, 6434379, 6578609, 6723359, 6870598, 7019910, 7168168, 7319472, 
    7472919, 7626897, 7781843, 7937799, 8096541, 8255893, 8418253, 8583316, 8749459, 8921196, 
    9097991, 9280402, 9471102, 9674587, 9895415, 10142999, 10414816, 10696778, 10992809, 11304075, 
    11632752, 11979388, 12355444, 12765735, 13233318, 13766422
]
BASE_PREMIUM = 120003

def get_pai_cv(year, annual_deposit):
    if year <= 0: return 0
    idx = year if year < len(PAI_BASE_DATA) else len(PAI_BASE_DATA) - 1
    base = PAI_BASE_DATA[idx]
    return base * (annual_deposit / BASE_PREMIUM)

def get_loan_limit_rate(year):
    if year >= 12: return 0.90
    if year >= 10: return 0.85
    if year >= 8: return 0.80
    if year >= 6: return 0.75
    return 0.70

def format_money(val, is_receive_column=False):
    """格式化金錢字串，如果是領回(負數)且在特定欄位，加上'領'字"""
    if val == 0: return "-"
    abs_val = abs(val)
    money_str = f"${abs_val:,.0f}"
    
    if is_receive_column and val < 0:
        return f"領 {money_str}"
    elif val < 0:
        return f"-{money_str}"
    return money_str

# --- 4. 側邊欄 ---
with st.sidebar:
    st.header("⚙️ 參數設定")
    start_age = st.number_input("🧑‍💼 目前年齡", value=25, min_value=0, max_value=80)
    monthly_deposit = st.number_input("💵 月存金額", value=10000, step=1000)
    st.divider()
    mode = st.radio("🔄 選擇策略模式", ["🛡️ 以息養險 (折抵保費)", "🚀 階梯槓桿 (複利滾存)"])
    st.info("💡 說明：\n\n**以息養險**：配息優先折抵保費，多餘領現。\n\n**階梯槓桿**：配息全數再投入，追求資產最大化。")

# --- 5. 主畫面 ---
st.title("📊 PAI 策略全能計算機")

# 圖片顯示區 (請在此替換網址)
IMG_OFFSET = "https://i.postimg.cc/9Mwkq4c1/Gemini-Generated-Image-57o51457o51457o5.png"
IMG_COMPOUND = "https://i.postimg.cc/SxKDMXr6/Gemini-Generated-Image-p41a4fp41a4fp41a.png"

if "以息養險" in mode:
    st.image(IMG_OFFSET, use_container_width=True)
    current_mode = "offset"
else:
    st.image(IMG_COMPOUND, use_container_width=True)
    current_mode = "compound"

# --- 6. 計算邏輯 ---
annual_deposit = monthly_deposit * 12
deposit_years = 20
fee_rate = 0.05

data_rows = []
raw_data_rows = [] # 用於存儲純數值以便 Styling
current_loan = 0
current_fund = 0
accum_cash_out = 0  
accum_net_wealth = 0 
accum_real_cost = 0 

# 月繳/年繳開關 (僅在 Offset 模式顯示)
is_monthly_pay = False
if current_mode == "offset":
    col_toggle, _ = st.columns([0.3, 0.7])
    with col_toggle:
        is_monthly_pay = st.toggle("切換為「月繳」顯示", value=False)

# 迴圈計算
for age in range(start_age + 1, 86):
    policy_year = age - start_age
    cv = get_pai_cv(policy_year, annual_deposit)
    limit_rate = get_loan_limit_rate(policy_year)
    is_loan_year = (policy_year % 3 == 0) and (age <= 65)
    
    # 借款邏輯
    loan_tag = ""
    if is_loan_year:
        max_loan = cv * limit_rate
        new_borrow = max_loan - current_loan
        if new_borrow > 0:
            current_loan += new_borrow
            current_fund += new_borrow * (1 - fee_rate)
            loan_tag = "⚡"

    net_income = current_fund * 0.07
    nominal_premium = annual_deposit if policy_year <= deposit_years else 0
    total_net_asset = 0

    row_display = {}
    row_raw = {} # 儲存原始數值給 Style 用

    if current_mode == "offset":
        # === 模式 A: 以息養險 ===
        actual_pay_yearly = nominal_premium - net_income
        
        # 累計邏輯
        if actual_pay_yearly > 0:
            accum_real_cost += actual_pay_yearly
        else:
            accum_cash_out += abs(actual_pay_yearly)

        total_net_asset = cv + current_fund + accum_cash_out - current_loan
        
        # 顯示邏輯 (切換年/月)
        display_val = actual_pay_yearly / 12 if is_monthly_pay else actual_pay_yearly
        
        # 建立資料列
        row_display["年齡"] = f"{age} {loan_tag}"
        row_display["①應繳年保費"] = format_money(nominal_premium)
        row_display["②配息抵扣"] = format_money(net_income)
        row_display["③實繳金額"] = format_money(display_val, is_receive_column=True)
        row_display["④累積實繳"] = format_money(accum_real_cost)
        row_display["⑤PAI解約金"] = format_money(cv)
        row_display["⑥保單借款"] = format_money(-current_loan)
        row_display["⑦基金本金"] = format_money(current_fund)
        row_display["⑧總淨資產"] = format_money(total_net_asset)

        # 儲存原始值給 Styling 判斷用
        row_raw = {
            "loan_year": is_loan_year,
            "real_pay_val": display_val,
            "net_asset": total_net_asset
        }

    else:
        # === 模式 B: 階梯槓桿 ===
        actual_deposit = nominal_premium
        acc_deposit = annual_deposit * policy_year if policy_year <= deposit_years else annual_deposit * deposit_years
        
        accum_net_wealth = (accum_net_wealth * 1.07) + net_income
        total_net_asset = cv + current_fund + accum_net_wealth - current_loan
        
        row_display["年齡"] = f"{age} {loan_tag}"
        row_display["①當年存入"] = format_money(actual_deposit)
        row_display["②累積本金"] = format_money(acc_deposit)
        row_display["③PAI解約金"] = format_money(cv)
        row_display["④保單借款"] = format_money(-current_loan)
        row_display["⑤基金本金"] = format_money(current_fund)
        row_display["⑥年度淨配息"] = format_money(net_income)
        row_display["⑦累積配息(複利)"] = format_money(accum_net_wealth)
        row_display["⑧總淨資產"] = format_money(total_net_asset)

        row_raw = {
            "loan_year": is_loan_year,
            "net_asset": total_net_asset
        }

    data_rows.append(row_display)
    raw_data_rows.append(row_raw)
    
    # 65歲驗證數據快照
    if age == 65:
        verify_snapshot = {
            "cv": cv, "loan": current_loan, "fund": current_fund,
            "cash_out": accum_cash_out, "accum_wealth": accum_net_wealth,
            "total": total_net_asset
        }

# --- 7. 表格樣式化 (Pandas Styler) ---
df = pd.DataFrame(data_rows)

def style_dataframe(df_input, raw_data):
    # 建立樣式 DataFrame，預設為空
    df_style = pd.DataFrame('', index=df_input.index, columns=df_input.columns)
    
    for i, raw in enumerate(raw_data):
        # 1. 借款年高亮 (整列黃底)
        if raw["loan_year"]:
            df_style.iloc[i, :] = 'background-color: #fffbe6;'
            
        # 2. 總淨資產 (淺藍底 + 深藍字 + 加粗)
        df_style.iloc[i, -1] += 'background-color: #e6f7ff; color: #096dd9; font-weight: bold;'
        
        # 3. 特定欄位文字顏色
        if current_mode == "offset":
            # 實繳金額：負數變桃紅，正數變綠
            val = raw["real_pay_val"]
            if val < 0:
                df_style.iloc[i, df_input.columns.get_loc("③實繳金額")] += 'color: #c41d7f; font-weight: bold;'
            elif val > 0:
                df_style.iloc[i, df_input.columns.get_loc("③實繳金額")] += 'color: #389e0d;'
                
            # 配息抵扣：桃紅色
            df_style.iloc[i, df_input.columns.get_loc("②配息抵扣")] += 'color: #c41d7f;'
            
            # 借款：紅色
            df_style.iloc[i, df_input.columns.get_loc("⑥保單借款")] += 'color: #cf1322;'
            
        else:
            # 淨配息：桃紅
            df_style.iloc[i, df_input.columns.get_loc("⑥年度淨配息")] += 'color: #c41d7f;'
            # 累積配息：紫色
            df_style.iloc[i, df_input.columns.get_loc("⑦累積配息(複利)")] += 'color: #722ed1;'
            
    return df_style

# 應用樣式
styler = df.style.apply(lambda x: style_dataframe(df, raw_data_rows), axis=None)

# 顯示表格
st.dataframe(
    styler,
    use_container_width=True,
    height=600,
    hide_index=True
)

# --- 8. 驗證區 (HTML 還原) ---
v = verify_snapshot
v_cv = f"${v['cv']:,.0f}"
v_fund = f"${v['fund']:,.0f}"
v_loan = f"-${v['loan']:,.0f}"
v_total = f"${v['total']:,.0f}"

# 根據模式決定顯示內容
if current_mode == "offset":
    v_cash = f"${v['cash_out']:,.0f}"
    
    # 組合 HTML 字串
    html_content = f"""
    <div class="verify-box">
        <div class="verify-title">🔍 65 歲資產結算驗證</div>
        <div class="verify-row"><span>[+] PAI 保單現金價值</span> <span>{v_cv}</span></div>
        <div class="verify-row"><span>[+] 基金本金</span> <span>{v_fund}</span></div>
        <div class="verify-row" style="color: #c41d7f;"><span>[+] 累積已領回現金 (Cash Out)</span> <span>{v_cash}</span></div>
        <div class="verify-row" style="color: #cf1322;"><span>[-] 扣除保單借款</span> <span>{v_loan}</span></div>
        <div class="verify-total">
            <span>[=] 總淨資產 (Net Worth)</span> <span>{v_total}</span>
        </div>
        <div class="verify-note">💡 說明：此模式配息優先抵扣保費，多餘的現金領回放口袋，適合重視現金流者。</div>
    </div>
    """
else:
    v_accum = f"${v['accum_wealth']:,.0f}"
    
    # 組合 HTML 字串
    html_content = f"""
    <div class="verify-box">
        <div class="verify-title">🔍 65 歲資產結算驗證</div>
        <div class="verify-row"><span>[+] PAI 保單現金價值</span> <span>{v_cv}</span></div>
        <div class="verify-row"><span>[+] 基金本金</span> <span>{v_fund}</span></div>
        <div class="verify-row" style="color: #722ed1;"><span>[+] 累積配息滾存 (複利)</span> <span>{v_accum}</span></div>
        <div class="verify-row" style="color: #cf1322;"><span>[-] 扣除保單借款</span> <span>{v_loan}</span></div>
        <div class="verify-total">
            <span>[=] 總淨資產 (Net Worth)</span> <span>{v_total}</span>
        </div>
        <div class="verify-note">💡 說明：此模式假設配息全部再投入 (7%複利)，適合追求資產最大化者。</div>
    </div>
    """

# 一次性渲染完整的 HTML
st.markdown(html_content, unsafe_allow_html=True)
