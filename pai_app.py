import streamlit as st
import pandas as pd
import numpy as np

# --- 1. 頁面基礎設定 ---
st.set_page_config(
    page_title="PAI 策略全能計算機",
    page_icon="📊",
    layout="wide"
)

# --- 2. CSS 樣式注入 (為了達到富邦 Teal 色系與精美表格) ---
st.markdown("""
    <style>
    /* 全局字體與色系 */
    :root {
        --brand-color: #006d75;
        --brand-bg: #e6fffb;
        --text-main: #262626;
        --pay-text: #389e0d;
        --receive-text: #c41d7f;
    }
    
    /* 標題樣式 */
    h1, h2, h3 { color: var(--brand-color) !important; font-family: -apple-system, sans-serif; }
    
    /* 表格樣式優化 */
    .stDataFrame { font-size: 14px; }
    
    /* 驗證區塊樣式 */
    .verify-box {
        background-color: #262626;
        color: white;
        padding: 20px;
        border-radius: 10px;
        margin-top: 20px;
        font-family: monospace;
    }
    .verify-row { display: flex; justify-content: space-between; margin-bottom: 8px; border-bottom: 1px dashed #444; padding-bottom: 4px; }
    .verify-total { font-size: 20px; font-weight: bold; color: #52c41a; margin-top: 10px; border-top: 1px solid #666; padding-top: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- 3. 核心資料與參數 ---
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

# --- 4. 側邊欄輸入區 ---
with st.sidebar:
    st.header("⚙️ 參數設定")
    start_age = st.number_input("🧑‍💼 目前年齡", value=25, min_value=0, max_value=80)
    monthly_deposit = st.number_input("💵 月存金額", value=10000, step=1000)
    
    st.divider()
    
    # 模式切換
    mode = st.radio("🔄 選擇策略模式", ["🛡️ 以息養險 (折抵保費)", "🚀 階梯槓桿 (複利滾存)"])
    
    st.info("💡 說明：\n\n**以息養險**：配息優先折抵保費，多餘領現。\n\n**階梯槓桿**：配息全數再投入，追求資產最大化。")

# --- 5. 主畫面邏輯 ---
st.title("📊 PAI 策略全能計算機")

# 圖片顯示區 (請在此替換網址)
IMG_OFFSET = "https://i.postimg.cc/9Mwkq4c1/Gemini-Generated-Image-57o51457o51457o5.png"
IMG_COMPOUND = "https://i.postimg.cc/SxKDMXr6/Gemini-Generated-Image-p41a4fp41a4fp41a.png"

if "以息養險" in mode:
    st.image(IMG_OFFSET, use_container_width=True)
    current_mode_key = "offset"
else:
    st.image(IMG_COMPOUND, use_container_width=True)
    current_mode_key = "compound"

# --- 6. 計算邏輯 ---
annual_deposit = monthly_deposit * 12
deposit_years = 20
fee_rate = 0.05

data_rows = []
current_loan = 0
current_fund = 0
accum_cash_out = 0  # for offset
accum_net_wealth = 0 # for compound
accum_real_cost = 0 # for offset

# 65歲驗證數據
verify_data = {}

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

    # 配息與資金流向邏輯
    net_income = current_fund * 0.07
    nominal_premium = annual_deposit if policy_year <= deposit_years else 0
    
    row = {
        "年齡": f"{age}{loan_tag}",
        "PAI解約金": cv,
        "保單借款": -current_loan,
        "基金本金": current_fund,
        "總淨資產": 0
    }

    if current_mode_key == "offset":
        # Mode A: 以息養險
        actual_pay = nominal_premium - net_income
        
        if actual_pay > 0:
            accum_real_cost += actual_pay
            display_pay = actual_pay # 實繳
        else:
            accum_cash_out += abs(actual_pay)
            display_pay = actual_pay # 負數代表領回
            
        row["應繳保費"] = nominal_premium
        row["配息抵扣"] = net_income
        row["實繳/領回"] = display_pay
        row["累積實繳"] = accum_real_cost
        row["總淨資產"] = cv + current_fund + accum_cash_out - current_loan
        
        # 整理欄位順序
        ordered_row = {k: row[k] for k in ["年齡", "應繳保費", "配息抵扣", "實繳/領回", "累積實繳", "PAI解約金", "保單借款", "基金本金", "總淨資產"]}
        
    else:
        # Mode B: 複利滾存
        actual_deposit = nominal_premium
        acc_deposit = annual_deposit * policy_year if policy_year <= deposit_years else annual_deposit * deposit_years
        
        accum_net_wealth = (accum_net_wealth * 1.07) + net_income
        
        row["當年存入"] = actual_deposit
        row["累積本金"] = acc_deposit
        row["年度淨配息"] = net_income
        row["累積配息(複利)"] = accum_net_wealth
        row["總淨資產"] = cv + current_fund + accum_net_wealth - current_loan
        
        # 整理欄位順序
        ordered_row = {k: row[k] for k in ["年齡", "當年存入", "累積本金", "PAI解約金", "保單借款", "基金本金", "年度淨配息", "累積配息(複利)", "總淨資產"]}

    data_rows.append(ordered_row)
    
    if age == 65:
        verify_data = {
            "cv": cv,
            "loan": current_loan,
            "fund": current_fund,
            "cash_out": accum_cash_out, # only for offset
            "accum_wealth": accum_net_wealth, # only for compound
            "total": row["總淨資產"]
        }

df = pd.DataFrame(data_rows)

# --- 7. 表格顯示與樣式 ---
# 使用 Pandas Styler 進行條件格式化 (模仿 HTML 顏色)
def highlight_rows(row):
    # 借款年高亮
    if "⚡" in str(row["年齡"]):
        return ['background-color: #fffbe6'] * len(row)
    return [''] * len(row)

def color_negative_red(val):
    if isinstance(val, (int, float)) and val < 0:
        return 'color: #c41d7f; font-weight: bold;' # 負數(領回)顯示桃紅
    return ''

# 格式化數字
format_dict = {col: "${:,.0f}" for col in df.columns if col != "年齡"}

styler = df.style.format(format_dict)\
    .apply(highlight_rows, axis=1)\
    .map(color_negative_red)

# 針對特定欄位上色 (Header color 需在 Streamlit theme 設定，這裡主要設定文字)
# Streamlit 的 dataframe 對於單元格樣式支援有限，這裡主要靠文字顏色區分

st.dataframe(
    styler,
    use_container_width=True,
    height=600,
    hide_index=True
)

# --- 8. 驗證區 ---
st.markdown("### 🔍 65 歲資產結算驗證")

v_cv_fmt = f"${verify_data['cv']:,.0f}"
v_loan_fmt = f"-${verify_data['loan']:,.0f}"
v_fund_fmt = f"${verify_data['fund']:,.0f}"
v_total_fmt = f"${verify_data['total']:,.0f}"

if current_mode_key == "offset":
    v_cash_fmt = f"${verify_data['cash_out']:,.0f}"
    st.markdown(f"""
    <div class="verify-box">
        <div class="verify-row"><span>[+] PAI 保單現金價值</span> <span>{v_cv_fmt}</span></div>
        <div class="verify-row"><span>[+] 基金本金</span> <span>{v_fund_fmt}</span></div>
        <div class="verify-row" style="color: #c41d7f;"><span>[+] 累積已領回現金 (Cash Out)</span> <span>{v_cash_fmt}</span></div>
        <div class="verify-row" style="color: #cf1322;"><span>[-] 扣除保單借款</span> <span>{v_loan_fmt}</span></div>
        <div class="verify-total"><span>[=] 總淨資產 (Net Worth)</span> <span>{v_total_fmt}</span></div>
    </div>
    """, unsafe_allow_html=True)
else:
    v_accum_fmt = f"${verify_data['accum_wealth']:,.0f}"
    st.markdown(f"""
    <div class="verify-box">
        <div class="verify-row"><span>[+] PAI 保單現金價值</span> <span>{v_cv_fmt}</span></div>
        <div class="verify-row"><span>[+] 基金本金</span> <span>{v_fund_fmt}</span></div>
        <div class="verify-row" style="color: #722ed1;"><span>[+] 累積配息滾存 (複利)</span> <span>{v_accum_fmt}</span></div>
        <div class="verify-row" style="color: #cf1322;"><span>[-] 扣除保單借款</span> <span>{v_loan_fmt}</span></div>
        <div class="verify-total"><span>[=] 總淨資產 (Net Worth)</span> <span>{v_total_fmt}</span></div>
    </div>
    """, unsafe_allow_html=True)
