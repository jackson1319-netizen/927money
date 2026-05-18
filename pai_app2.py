import streamlit as st
import pandas as pd
import numpy as np

# --- 1. 頁面基礎設定 ---
st.set_page_config(
    page_title="IAT2 策略全能計算機",
    page_icon="📊",
    layout="wide"
)

# --- 1.5 密碼驗證模組 ---
def check_password():
    ACTUAL_PASSWORD = "Fubon"
    if "password_correct" not in st.session_state:
        st.text_input("🔒 請輸入訪問密碼", type="password", on_change=lambda: st.session_state.update({"password_correct": st.session_state["password"] == ACTUAL_PASSWORD}), key="password")
        return False
    return st.session_state["password_correct"]

if not check_password():
    st.stop()

# --- 2. CSS 樣式注入 ---
st.markdown("""
    <style>
    :root {
        --brand-color: #003a8c;
        --brand-bg: #f0f5ff;
        --text-main: #262626;
        --pay-text: #389e0d;
        --receive-text: #c41d7f;
        --debt-color: #cf1322;
        --asset-text: #096dd9;
    }
    h1, h2, h3 { color: var(--brand-color) !important; font-family: -apple-system, sans-serif; }
    .verify-box {
        background-color: #262626;
        color: white;
        padding: 24px;
        border-radius: 10px;
        margin-top: 24px;
        font-family: monospace;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .verify-title { color: #faad14; font-weight: bold; margin-bottom: 15px; border-bottom: 1px solid #434343; padding-bottom: 10px; font-size: 16px; }
    .verify-row { display: flex; justify-content: space-between; margin-bottom: 8px; align-items: center; }
    .verify-total { font-size: 20px; font-weight: bold; color: #52c41a; margin-top: 15px; border-top: 1px solid #555; padding-top: 15px; display: flex; justify-content: space-between; }
    .verify-note { font-size: 13px; color: #8c8c8c; margin-top: 15px; border-top: 1px dashed #434343; padding-top: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- 3. 核心數據：IAT2 (37歲女，年繳 120,918) [cite: 1, 10] ---
IAT2_BASE_PREMIUM = 120918 
IAT2_CV_DATA = [0, 57241, 161215, 280011, 414148, 563983, 722004, 745788, 762729, 780050, 797711, 815762, 834207, 853051, 872256, 892170, 912497, 933250, 954474, 976139, 998284, 1020880, 1043933, 1067496, 1091523, 1116366, 1141780, 1167738, 1194193, 1221201, 1248731, 1276880, 1305516, 1334739, 1364433, 1395712, 1427683, 1460369, 1493739, 1527863, 1562718, 1598291, 1634634, 1671738, 1709575, 1748178, 1787558, 1827752, 1868643, 1910310, 1952764, 1995964, 2039829, 2084438, 2129682, 2175900, 2222877, 2270575, 2319052, 2368279, 2418279, 2468979, 2520481, 2572804, 2625837, 2679680, 2734352, 2789925, 2846357, 2903802, 2962153, 3021701, 3082687, 3146580, 3200603]
IAT2_DEATH_DATA = [0, 126468, 321248, 525515, 734419, 829592, 1020884, 1042505, 1064500, 1087000, 1109882, 1133237, 1157070, 1181428, 1206147, 1061997, 1085248, 1108966, 1133198, 1157911, 1183148, 1208876, 1235103, 1261924, 1289210, 1216901, 1244068, 1271740, 1299990, 1328795, 1358120, 1388107, 1418622, 1449725, 1481299, 1419520, 1451866, 1484970, 1518800, 1553341, 1588614, 1624646, 1661449, 1699012, 1737309, 1776371, 1816211, 1856864, 1898257, 1940424, 1983338, 2027039, 2071405, 2116516, 2162260, 2192816, 2239250, 2286321, 2334047, 2382480, 2431561, 2481342, 2531842, 2583120, 2635109, 2687867, 2741411, 2795815, 2850993, 2907018, 2963907, 3021743, 3082687, 3146580, 3200603]

def get_loan_limit_rate(year):
    if year >= 4: return 0.90 #
    if year == 3: return 0.85
    if year == 2: return 0.80
    if year == 1: return 0.75
    return 0

def format_money(val, is_receive_column=False):
    if val == 0: return "-"
    abs_val = abs(val)
    money_str = f"${abs_val:,.0f}"
    return f"領 {money_str}" if is_receive_column and val < 0 else (f"-{money_str}" if val < 0 else money_str)

# --- 4. 側邊欄與參數 ---
with st.sidebar:
    st.header("⚙️ 策略參數")
    start_age = st.number_input("🧑‍💼 投保年齡", value=37)
    monthly_deposit = st.number_input("💵 月存金額", value=10076)
    st.divider()
    is_monthly_view = st.toggle("📅 切換為「月繳」顯示", value=False)
    mode = st.radio("🔄 策略模式", ["🛡️ 以息養險 (折抵保費)", "🚀 階梯槓桿 (複利滾存)"])
    st.info("⚡ 借款邏輯修正：\n1. 首次借款需滿 30 萬。\n2. 啟動後每 3 年增貸投入。")

# --- 5. 核心計算邏輯 ---
st.title("📊 IAT2 策略全能計算機 (門檻修正版)")

annual_pay = monthly_deposit * 12
data_rows, highlights = [], []
# 變數初始化
current_loan, current_fund, accum_cash_out, accum_net_wealth, accum_real_cost, last_borrow_year = 0, 0, 0, 0, 0, 0
has_started_borrowing = False
v65 = {}

for age in range(start_age + 1, start_age + 51):
    policy_year = age - start_age
    cv = IAT2_CV_DATA[policy_year] * (annual_pay / 120918)
    limit_rate = get_loan_limit_rate(policy_year)
    max_available_loan = cv * limit_rate
    
    is_borrowing_year = False
    if age <= 75: 
        # --- 修正後的借款邏輯 ---
        if not has_started_borrowing:
            # 首次借款：必須滿 30 萬
            if max_available_loan >= 300000:
                new_borrow = max_available_loan
                current_loan = max_available_loan
                current_fund += new_borrow * 0.95 # 扣除手續費
                last_borrow_year = policy_year
                has_started_borrowing = True
                is_borrowing_year = True
        else:
            # 後續增貸：每三年一次
            if (policy_year - last_borrow_year) >= 3:
                new_borrow = max_available_loan - current_loan
                if new_borrow > 0:
                    current_loan = max_available_loan
                    current_fund += new_borrow * 0.95
                    last_borrow_year = policy_year
                    is_borrowing_year = True

    highlights.append(is_borrowing_year)
    net_income = current_fund * 0.07
    nominal_premium = annual_pay if policy_year <= 6 else 0
    death_base = IAT2_DEATH_DATA[policy_year] * (annual_pay / 120918)
    
    row = {"保單年度": policy_year, "年齡": f"{age} {'⚡' if is_borrowing_year else ''}"}
    divisor = 12 if is_monthly_view else 1
    col_suffix = "(月)" if is_monthly_view else ""

    if "以息養險" in mode:
        actual_pay = nominal_premium - net_income
        if actual_pay > 0: accum_real_cost += actual_pay
        else: accum_cash_out += abs(actual_pay)
        total_nw = cv + current_fund + accum_cash_out - current_loan
        total_db = death_base + current_fund - current_loan
        row.update({
            f"①年繳保費{col_suffix}": format_money(nominal_premium / divisor),
            f"②配息抵扣{col_suffix}": format_money(net_income / divisor),
            f"③實繳金額{col_suffix}": format_money(actual_pay / divisor, True),
            "④累積實繳": format_money(accum_real_cost),
            "⑤IAT2解約金": format_money(cv),
            "⑥保單借款": f"{format_money(-current_loan)} ({int(limit_rate*100)}%)",
            "⑦基金本金": format_money(current_fund),
            "⑧總淨資產": format_money(total_nw),
            "⑨身故金": format_money(total_db)
        })
    else:
        accum_net_wealth = (accum_net_wealth * 1.07) + net_income
        total_nw = cv + current_fund + accum_net_wealth - current_loan
        total_db = death_base + current_fund + accum_net_wealth - current_loan
        row.update({
            f"①當年存入{col_suffix}": format_money(nominal_premium / divisor),
            "②累積本金": format_money(annual_pay * min(policy_year, 6)),
            "③IAT2解約金": format_money(cv),
            "④保單借款": f"{format_money(-current_loan)} ({int(limit_rate*100)}%)",
            "⑤基金本金": format_money(current_fund),
            f"⑥年度淨配息{col_suffix}": format_money(net_income / divisor),
            "⑦累積配息": format_money(accum_net_wealth),
            "⑧總淨資產": format_money(total_nw),
            "⑨身故金": format_money(total_db)
        })
    data_rows.append(row)
    if age == 65:
        v65 = {"cv": cv, "fund": current_fund, "loan": current_loan, "extra": accum_cash_out if "以息養險" in mode else accum_net_wealth, "total": total_nw}

# --- 6. 表格輸出 ---
df = pd.DataFrame(data_rows)
st.dataframe(df.style.apply(lambda s: ['background-color: #fffbe6;' if highlights[i] else '' for i in range(len(s))], axis=0), use_container_width=True, height=500, hide_index=True)

# --- 7. 65 歲結算看板 ---
if v65:
    extra_label = "累積已領回現金" if "以息養險" in mode else "累積配息滾存(複利)"
    st.markdown(f"""
    <div class="verify-box">
        <div class="verify-title">🎯 65 歲退休資產結算 (Age 65 Summary)</div>
        <div class="verify-row"><span>[+] IAT2 保單現金價值</span> <span>{format_money(v65['cv'])}</span></div>
        <div class="verify-row"><span>[+] 基金投資本金</span> <span>{format_money(v65['fund'])}</span></div>
        <div class="verify-row"><span>[+] {extra_label}</span> <span>{format_money(v65['extra'])}</span></div>
        <div class="verify-row" style="color: #cf1322;"><span>[-] 扣除保單借款負債</span> <span>{format_money(-v65['loan'])}</span></div>
        <div class="verify-total">
            <span>[=] 總淨資產 (Total Net Worth)</span> <span>{format_money(v65['total'])}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
