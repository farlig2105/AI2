import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
import os
import hashlib

# ----------------------------------------------------
# 1. CẤU HÌNH TRANG & DANH MỤC BIỂU TƯỢNG
# ----------------------------------------------------
st.set_page_config(
    page_title="FinFlow - Quản Lý Tài Chính Cá Nhân",
    layout="wide",
    page_icon="💎",
    initial_sidebar_state="collapsed"
)

CAT_ICONS = {
    "Tiền nhà": "🏠",
    "Thực phẩm": "🍲",
    "Điện nước & Mạng": "⚡",
    "Giải trí": "🎮",
    "Đi lại": "🚗",
    "Khác": "📦"
}

USERS_FILE = "users.json"

# ----------------------------------------------------
# 2. XỬ LÝ XÁC THỰC NGƯỜI DÙNG & MÃ HÓA MẬT KHẨU
# ----------------------------------------------------
def hash_password(password: str) -> str:
    """Mã hóa mật khẩu bằng SHA-256 để đảm bảo bảo mật."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def load_users() -> dict:
    """Tải danh sách tài khoản đã đăng ký."""
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_users(users: dict):
    """Lưu danh sách tài khoản mới."""
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

def get_user_data_file() -> str:
    """Trả về đường dẫn file dữ liệu riêng của người dùng hiện tại."""
    current_user = st.session_state.get("current_user", "default")
    return f"finflow_data_{current_user}.json"

def logout_user():
    """Xóa bộ nhớ đệm session state và đăng xuất."""
    keys_to_clear = [
        "authenticated", "current_user", "data_loaded_from_disk", 
        "configured", "income", "fixed_expenses", "savings_goal", "emergency_fund",
        "daily_logs", "monthly_history", "chat_history", "modal_step",
        "inp_income", "inp_rent", "inp_food", "inp_util", "inp_ent", 
        "inp_trans", "inp_other", "inp_log_amt", "inp_log_note", "inp_goal", "inp_emergency",
        "multiselect_delete_logs", "daily_logs_table_grid", "current_options_dict",
        "show_confirm_dialog", "pending_expense", "expense_added_msg", "expense_error_msg"
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

# ----------------------------------------------------
# 3. XỬ LÝ LƯU & TẢI DỮ LIỆU TỰ ĐỘNG
# ----------------------------------------------------
def load_user_data():
    """Tải dữ liệu đã lưu từ tệp JSON riêng của người dùng."""
    user_file = get_user_data_file()
    if os.path.exists(user_file):
        try:
            with open(user_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None

def save_user_data():
    """Lưu toàn bộ dữ liệu hiện tại vào tệp JSON riêng của người dùng."""
    if not st.session_state.get("authenticated", False):
        return

    daily_logs_list = []
    if "daily_logs" in st.session_state and isinstance(st.session_state.daily_logs, pd.DataFrame):
        daily_logs_list = st.session_state.daily_logs.to_dict(orient="records")

    data_to_save = {
        "configured": st.session_state.get("configured", False),
        "income": st.session_state.get("income", 15000000.0),
        "fixed_expenses": st.session_state.get("fixed_expenses", {}),
        "emergency_fund": st.session_state.get("emergency_fund", 5000000.0),
        "savings_goal": st.session_state.get("savings_goal", 0.0),
        "daily_logs": daily_logs_list,
        "monthly_history": st.session_state.get("monthly_history", {})
    }
    try:
        user_file = get_user_data_file()
        with open(user_file, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

def sync_data():
    """Đồng bộ dữ liệu xuống tệp lưu trữ."""
    save_user_data()

# ----------------------------------------------------
# 4. BỘ HÀM XỬ LÝ DÙNG CHUNG & CALLBACKS
# ----------------------------------------------------
def parse_amount(val) -> float:
    if isinstance(val, (int, float)):
        return float(val)
    cleaned = "".join(c for c in str(val) if c.isdigit())
    return float(cleaned) if cleaned else 0.0

def format_money_callback(key_name):
    raw_val = st.session_state.get(key_name, "")
    digits = "".join(c for c in str(raw_val) if c.isdigit())
    if digits:
        st.session_state[key_name] = f"{int(digits):,}"
    else:
        st.session_state[key_name] = "0"

def num2vi_words(val) -> str:
    n = int(parse_amount(val))
    if n <= 0:
        return "0 VNĐ"
    if n >= 1_000_000_000:
        ty = n // 1_000_000_000
        trieu = (n % 1_000_000_000) // 1_000_000
        return f"{ty:,} tỷ {trieu} triệu VNĐ" if trieu > 0 else f"{ty:,} tỷ VNĐ"
    elif n >= 1_000_000:
        trieu = n // 1_000_000
        nghin = (n % 1_000_000) // 1_000
        return f"{trieu} triệu {nghin} nghìn VNĐ" if nghin > 0 else f"{trieu} triệu VNĐ"
    elif n >= 1_000:
        nghin = n // 1_000
        dong = n % 1_000
        return f"{nghin} nghìn {dong} VNĐ" if dong > 0 else f"{nghin} nghìn VNĐ"
    else:
        return f"{n} VNĐ"

def add_expense_action(log_date, log_cat, amt, log_note):
    """Hàm ghi nhận thực tế khoản chi vào DataFrame."""
    new_row = pd.DataFrame([{
        "Ngày": str(log_date), 
        "Danh mục": log_cat, 
        "Số tiền": amt, 
        "Ghi chú": log_note
    }])
    st.session_state.daily_logs = pd.concat([st.session_state.daily_logs, new_row], ignore_index=True)
    st.session_state.inp_log_amt = "0"
    st.session_state.inp_log_note = ""
    sync_data()

def confirm_emergency_action():
    """Callback xác nhận chi: Thêm vào bảng, reset dữ liệu và làm mới trang."""
    pending = st.session_state.get("pending_expense", {})
    if pending:
        add_expense_action(
            pending["log_date"],
            pending["log_cat"],
            pending["amt"],
            pending["log_note"]
        )
        st.session_state.show_confirm_dialog = False
        st.session_state.pending_expense = None
        st.session_state.expense_added_msg = True
        st.rerun()

def cancel_emergency_action():
    """Callback hủy bỏ: Đóng hộp thoại và GIỮ NGUYÊN toàn bộ thông tin đã nhập."""
    st.session_state.show_confirm_dialog = False
    st.session_state.pending_expense = None
    st.rerun()

def handle_add_expense_click():
    """Callback kiểm tra và xử lý khi bấm nút Thêm khoản chi."""
    log_amt = parse_amount(st.session_state.get("inp_log_amt", "0"))
    if log_amt <= 0:
        st.session_state.expense_error_msg = "Vui lòng nhập số tiền hợp lệ lớn hơn 0."
        return

    st.session_state.expense_error_msg = None
    log_date = st.session_state.get("inp_log_date", datetime.now().date())
    log_cat = st.session_state.get("inp_log_cat", list(st.session_state.fixed_expenses.keys())[0])
    log_note = st.session_state.get("inp_log_note", "")

    fixed_exp_total = sum(st.session_state.fixed_expenses.values())
    logged_exp_total = st.session_state.daily_logs["Số tiền"].sum() if not st.session_state.daily_logs.empty else 0.0
    grand_total_exp = fixed_exp_total + logged_exp_total
    remaining_balance = st.session_state.income - grand_total_exp

    future_bal = remaining_balance - log_amt
    em_fund = st.session_state.get("emergency_fund", 5000000.0)

    if future_bal <= em_fund:
        st.session_state.show_confirm_dialog = True
        st.session_state.pending_expense = {
            "amt": log_amt,
            "log_date": log_date,
            "log_cat": log_cat,
            "log_note": log_note,
            "future_bal": future_bal,
            "em_fund": em_fund
        }
    else:
        add_expense_action(log_date, log_cat, log_amt, log_note)
        st.session_state.expense_added_msg = True

@st.dialog("⚠️ Xác nhận Tiêu dùng Số dư Khẩn cấp")
def confirm_emergency_expense_modal(amt, log_date, log_cat, log_note, future_bal, em_fund):
    """Dialog hỏi xác nhận người dùng khi khoản chi động tới Quỹ khẩn cấp."""
    st.warning("🚨 **CẢNH BÁO NGUY CƠ TÀI CHÍNH!**")
    st.write(
        f"Khoản chi **{amt:,.0f} VNĐ** cho mục **{log_cat}** sẽ khiến số dư còn lại của bạn "
        f"giảm xuống **{future_bal:,.0f} VNĐ**, chạm hoặc rơi xuống dưới mức **Quỹ Khẩn Cấp ({em_fund:,.0f} VNĐ)**."
    )
    st.info("💡 *Số tiền khẩn cấp này được quy định là không dùng tới trừ trường hợp bất khả kháng. Bạn có chắc chắn muốn duyệt khoản chi này không?*")
    
    col_confirm, col_cancel = st.columns(2)
    with col_confirm:
        st.button("Xác nhận chi dùng ⚠️", type="primary", use_container_width=True, on_click=confirm_emergency_action)
    with col_cancel:
        st.button("Hủy bỏ giao dịch ❌", use_container_width=True, on_click=cancel_emergency_action)

def open_config_callback():
    """Callback mở lại bảng Cấu hình."""
    st.session_state.configured = False
    st.session_state.modal_step = 1
    st.session_state.inp_income = f"{int(st.session_state.income):,}"
    st.session_state.inp_rent = f"{int(st.session_state.fixed_expenses.get('Tiền nhà', 0)):,}"
    st.session_state.inp_food = f"{int(st.session_state.fixed_expenses.get('Thực phẩm', 0)):,}"
    st.session_state.inp_util = f"{int(st.session_state.fixed_expenses.get('Điện nước & Mạng', 0)):,}"
    st.session_state.inp_ent = f"{int(st.session_state.fixed_expenses.get('Giải trí', 0)):,}"
    st.session_state.inp_trans = f"{int(st.session_state.fixed_expenses.get('Đi lại', 0)):,}"
    st.session_state.inp_other = f"{int(st.session_state.fixed_expenses.get('Khác', 0)):,}"
    st.session_state.inp_emergency = f"{int(st.session_state.get('emergency_fund', 5000000.0)):,}"
    sync_data()

def delete_grid_callback():
    """Callback xử lý xóa dòng chọn trên bảng"""
    grid_data = st.session_state.get("daily_logs_table_grid", {})
    if isinstance(grid_data, dict):
        selected_rows = grid_data.get("selection", {}).get("rows", [])
        if selected_rows:
            st.session_state.daily_logs = st.session_state.daily_logs.drop(
                st.session_state.daily_logs.index[selected_rows]
            ).reset_index(drop=True)
            sync_data()

def delete_multiselect_callback():
    """Callback xử lý xóa dòng chọn từ dropdown list"""
    selected_items = st.session_state.get("multiselect_delete_logs", [])
    options_dict = st.session_state.get("current_options_dict", {})
    if selected_items and options_dict:
        indices_to_drop = [options_dict[item] for item in selected_items if item in options_dict]
        if indices_to_drop:
            st.session_state.daily_logs = st.session_state.daily_logs.drop(indices_to_drop).reset_index(drop=True)
            sync_data()
    st.session_state.multiselect_delete_logs = []

# ----------------------------------------------------
# 5. TIÊM CSS TÙY BIẾN
# ----------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    :root {
        --bg-gradient: linear-gradient(135deg, #F8FAFC 0%, #EEF2FF 50%, #E2E8F0 100%);
        --text-primary: #0F172A;
        --text-secondary: #475569;
        --card-bg: rgba(255, 255, 255, 0.9);
        --card-hover-bg: #FFFFFF;
        --card-border: rgba(203, 213, 225, 0.8);
        --card-shadow: 0 10px 25px -5px rgba(148, 163, 184, 0.2);
        --input-bg: #FFFFFF;
        --input-border: #CBD5E1;
        --input-text: #0F172A;
        --tab-bg: #E2E8F0;
        --tab-text: #475569;
        --table-bg: #FFFFFF;
        --table-text: #0F172A;
        --table-border: #E2E8F0;
        --table-header-bg: #F1F5F9;
        --table-header-text: #0F172A;
        --table-row-hover: rgba(99, 102, 241, 0.08);
        --dialog-bg: #FFFFFF;

        --badge-red-bg: #FEE2E2;
        --badge-red-text: #DC2626;
        --badge-red-border: #FCA5A5;

        --badge-green-bg: #D1FAE5;
        --badge-green-text: #059669;
        --badge-green-border: #6EE7B7;

        --badge-gray-bg: #F1F5F9;
        --badge-gray-text: #475569;
        --badge-gray-border: #CBD5E1;
    }

    @media (prefers-color-scheme: dark) {
        :root {
            --bg-gradient: radial-gradient(circle at 50% 0%, #1E1B4B 0%, #0F172A 50%, #020617 100%);
            --text-primary: #F8FAFC;
            --text-secondary: #CBD5E1;
            --card-bg: rgba(30, 41, 59, 0.6);
            --card-hover-bg: rgba(30, 41, 59, 0.85);
            --card-border: rgba(255, 255, 255, 0.12);
            --card-shadow: 0 20px 30px -10px rgba(0, 0, 0, 0.5);
            --input-bg: rgba(15, 23, 42, 0.85);
            --input-border: rgba(255, 255, 255, 0.2);
            --input-text: #FFFFFF;
            --tab-bg: rgba(15, 23, 42, 0.6);
            --tab-text: #CBD5E1;
            --table-bg: #0F172A;
            --table-text: #F8FAFC;
            --table-border: rgba(255, 255, 255, 0.15);
            --table-header-bg: #1E293B;
            --table-header-text: #E2E8F0;
            --table-row-hover: rgba(99, 102, 241, 0.2);
            --dialog-bg: rgba(15, 23, 42, 0.95);

            --badge-red-bg: rgba(239, 68, 68, 0.2);
            --badge-red-text: #FCA5A5;
            --badge-red-border: rgba(239, 68, 68, 0.4);

            --badge-green-bg: rgba(16, 185, 129, 0.2);
            --badge-green-text: #6EE7B7;
            --badge-green-border: rgba(16, 185, 129, 0.4);

            --badge-gray-bg: rgba(100, 116, 139, 0.2);
            --badge-gray-text: #CBD5E1;
            --badge-gray-border: rgba(100, 116, 139, 0.4);
        }
    }

    .stApp {
        background: var(--bg-gradient) !important;
        color: var(--text-primary) !important;
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    h1, h2, h3, h4, h5, h6, .stMarkdown, .stMarkdown p, .stMarkdown span {
        color: var(--text-primary) !important;
    }

    .stCaption, [data-testid="stCaptionContainer"] {
        color: var(--text-secondary) !important;
    }

    div[data-testid="stDataFrame"], [data-testid="stTable"] {
        background-color: var(--table-bg) !important;
        color: var(--table-text) !important;
        border: 1px solid var(--table-border) !important;
        border-radius: 16px !important;
        padding: 6px !important;
        box-shadow: var(--card-shadow) !important;
    }

    div[data-testid="stDataFrame"] * {
        color: var(--table-text) !important;
    }

    .auth-title {
        background: linear-gradient(135deg, #6366F1 0%, #A855F7 50%, #10B981 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 3.4rem !important;
        letter-spacing: -0.5px;
        margin-bottom: 8px;
    }

    .auth-sub {
        color: var(--text-secondary) !important;
        font-size: 1.2rem;
        font-weight: 600;
        margin-bottom: 20px;
    }

    div[data-testid="stTextInput"] label, 
    div[data-testid="stSelectbox"] label, 
    div[data-testid="stDateInput"] label,
    div[data-testid="stNumberInput"] label {
        font-size: 1.05rem !important;
        font-weight: 700 !important;
        color: var(--text-primary) !important;
        margin-bottom: 6px !important;
    }

    div[data-baseweb="input"] input, 
    div[data-baseweb="select"] input,
    div[data-baseweb="select"] div {
        font-size: 1.05rem !important;
        color: var(--input-text) !important;
    }

    div[data-baseweb="input"], 
    div[data-baseweb="select"] > div {
        border-radius: 12px !important;
        background-color: var(--input-bg) !important;
        border: 1px solid var(--input-border) !important;
        transition: all 0.25s ease !important;
    }

    ul[data-baseweb="menu"] {
        background-color: var(--dialog-bg) !important;
        border: 1px solid var(--card-border) !important;
    }
    ul[data-baseweb="menu"] li {
        color: var(--text-primary) !important;
    }

    div[data-baseweb="tab-list"] {
        background: var(--tab-bg) !important;
        backdrop-filter: blur(12px) !important;
        padding: 6px !important;
        border-radius: 16px !important;
        border: 1px solid var(--card-border) !important;
        gap: 8px !important;
        display: flex !important;
        width: 100% !important;
    }

    button[data-baseweb="tab"] {
        flex: 1 !important;
        height: 52px !important;
        border-radius: 12px !important;
        border: none !important;
        background: transparent !important;
        color: var(--tab-text) !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
        transition: all 0.25s ease !important;
    }

    button[data-baseweb="tab"]:hover {
        color: var(--text-primary) !important;
        background: rgba(99, 102, 241, 0.1) !important;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #6366F1 0%, #4F46E5 100%) !important;
        color: #FFFFFF !important;
        box-shadow: 0 6px 18px -4px rgba(99, 102, 241, 0.4) !important;
    }

    div[data-baseweb="tab-highlight"], div[data-baseweb="tab-border"] {
        display: none !important;
    }

    .stButton > button {
        border-radius: 12px !important;
        background: linear-gradient(135deg, #6366F1 0%, #4F46E5 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
        padding: 0.75rem 1.4rem !important;
        transition: all 0.25s ease !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(99, 102, 241, 0.35) !important;
    }

    div[role="dialog"] {
        border-radius: 24px !important;
        background: var(--dialog-bg) !important;
        border: 1px solid var(--card-border) !important;
        box-shadow: var(--card-shadow) !important;
        color: var(--text-primary) !important;
    }

    .dash-header {
        background: linear-gradient(135deg, #6366F1 0%, #A855F7 50%, #10B981 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.6rem;
        letter-spacing: -0.5px;
    }

    .metric-card {
        background: var(--card-bg);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid var(--card-border);
        border-radius: 20px;
        padding: 22px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: var(--card-shadow);
    }
    .metric-card:hover {
        transform: translateY(-3px);
        background: var(--card-hover-bg);
        border-color: rgba(99, 102, 241, 0.4);
    }
    .metric-title {
        color: var(--text-secondary);
        font-size: 0.88rem;
        font-weight: 700;
        letter-spacing: 0.8px;
        text-transform: uppercase;
        margin-bottom: 8px;
    }
    .metric-value {
        color: var(--text-primary);
        font-size: 2rem;
        font-weight: 800;
        letter-spacing: -0.5px;
    }
    .metric-sub {
        font-size: 0.9rem;
        margin-top: 8px;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .sub-green { color: #10B981 !important; }
    .sub-red { color: #EF4444 !important; }

    .custom-table-container {
        border-radius: 18px;
        overflow: hidden;
        border: 1px solid var(--table-border);
        background: var(--table-bg);
        backdrop-filter: blur(16px);
        box-shadow: var(--card-shadow);
        margin-top: 10px;
    }
    .custom-table {
        width: 100%;
        border-collapse: collapse;
        text-align: left;
        color: var(--table-text);
    }
    .custom-table thead tr {
        background: var(--table-header-bg);
        border-bottom: 1px solid var(--table-border);
    }
    .custom-table th {
        padding: 16px 20px;
        font-size: 0.92rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: var(--table-header-text);
    }
    .custom-table td {
        padding: 16px 20px;
        font-size: 1.02rem;
        border-bottom: 1px solid var(--table-border);
        vertical-align: middle;
        color: var(--table-text);
    }
    .custom-table tbody tr {
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .custom-table tbody tr:hover {
        background: var(--table-row-hover);
    }
    
    .badge-pill {
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.88rem;
        font-weight: 700;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    .badge-red {
        background: var(--badge-red-bg);
        color: var(--badge-red-text);
        border: 1px solid var(--badge-red-border);
    }
    .badge-green {
        background: var(--badge-green-bg);
        color: var(--badge-green-text);
        border: 1px solid var(--badge-green-border);
    }
    .badge-gray {
        background: var(--badge-gray-bg);
        color: var(--badge-gray-text);
        border: 1px solid var(--badge-gray-border);
    }
    .cat-title {
        display: flex;
        align-items: center;
        gap: 12px;
        font-weight: 700;
        font-size: 1.02rem;
        color: var(--table-text);
    }
    .cat-icon {
        width: 36px;
        height: 36px;
        border-radius: 10px;
        background: rgba(99, 102, 241, 0.15);
        border: 1px solid rgba(99, 102, 241, 0.3);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.15rem;
    }
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------
# 6. MÀN HÌNH ĐĂNG NHẬP / ĐĂNG KÝ
# ----------------------------------------------------
if not st.session_state.get("authenticated", False):
    st.write("")
    st.write("")
    col_l1, col_l2, col_l3 = st.columns([1, 1.8, 1])
    with col_l2:
        st.markdown('<div style="text-align: center; margin-bottom: 25px;"><div class="auth-title">💎 FinFlow</div><p class="auth-sub">Hệ thống Quản lý Tài chính Cá nhân Thông minh</p></div>', unsafe_allow_html=True)
        
        tab_login, tab_register = st.tabs(["🔑 Đăng nhập", "📝 Đăng ký"])
        users = load_users()

        with tab_login:
            st.write("")
            login_username = st.text_input("Tên đăng nhập / Email", key="login_usr").strip().lower()
            login_password = st.text_input("Mật khẩu", type="password", key="login_pwd")
            st.write("")
            if st.button("Đăng nhập vào hệ thống 🚀", use_container_width=True):
                if not login_username or not login_password:
                    st.error("Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu.")
                elif login_username in users and users[login_username] == hash_password(login_password):
                    st.session_state.authenticated = True
                    st.session_state.current_user = login_username
                    st.success(f"Đăng nhập thành công! Chào mừng {login_username}.")
                    st.rerun()
                else:
                    st.error("Tên đăng nhập hoặc mật khẩu không chính xác.")

        with tab_register:
            st.write("")
            reg_username = st.text_input("Tên đăng nhập mới", key="reg_usr").strip().lower()
            reg_password = st.text_input("Mật khẩu", type="password", key="reg_pwd")
            reg_confirm = st.text_input("Xác nhận mật khẩu", type="password", key="reg_conf")
            st.write("")
            if st.button("Tạo tài khoản mới ✨", use_container_width=True):
                if not reg_username or not reg_password:
                    st.error("Vui lòng điền đầy đủ thông tin đăng ký.")
                elif len(reg_username) < 3:
                    st.error("Tên đăng nhập phải có ít nhất 3 ký tự.")
                elif reg_password != reg_confirm:
                    st.error("Mật khẩu xác nhận không khớp.")
                elif reg_username in users:
                    st.error("Tên đăng nhập này đã tồn tại trên hệ thống. Vui lòng chọn tên khác.")
                else:
                    users[reg_username] = hash_password(reg_password)
                    save_users(users)
                    st.success("Tạo tài khoản thành công! Bạn có thể chuyển sang tab Đăng nhập ngay bây giờ.")

    st.stop()

# ----------------------------------------------------
# 7. KHỞI TẠO SESSION STATE & TẢI DỮ LIỆU ĐÃ LƯU CỦA USER
# ----------------------------------------------------
if "data_loaded_from_disk" not in st.session_state:
    saved_data = load_user_data()
    if saved_data:
        st.session_state.configured = saved_data.get("configured", False)
        st.session_state.income = float(saved_data.get("income", 15000000.0))
        st.session_state.fixed_expenses = saved_data.get("fixed_expenses", {
            "Tiền nhà": 3500000.0, "Thực phẩm": 4000000.0, "Điện nước & Mạng": 1000000.0,
            "Giải trí": 1500000.0, "Đi lại": 800000.0, "Khác": 500000.0
        })
        st.session_state.emergency_fund = float(saved_data.get("emergency_fund", 5000000.0))
        st.session_state.savings_goal = float(saved_data.get("savings_goal", 2960000.0))
        
        logs_raw = saved_data.get("daily_logs", [])
        if logs_raw:
            df_logs = pd.DataFrame(logs_raw)
            for col in ["Ngày", "Danh mục", "Số tiền", "Ghi chú"]:
                if col not in df_logs.columns:
                    df_logs[col] = ""
            st.session_state.daily_logs = df_logs
        else:
            st.session_state.daily_logs = pd.DataFrame(columns=["Ngày", "Danh mục", "Số tiền", "Ghi chú"])
            
        st.session_state.monthly_history = saved_data.get("monthly_history", {})
    st.session_state.data_loaded_from_disk = True

if "configured" not in st.session_state:
    st.session_state.configured = False
if "modal_step" not in st.session_state:
    st.session_state.modal_step = 1
if "income" not in st.session_state:
    st.session_state.income = 15000000.0
if "fixed_expenses" not in st.session_state:
    st.session_state.fixed_expenses = {
        "Tiền nhà": 3500000.0, "Thực phẩm": 4000000.0, "Điện nước & Mạng": 1000000.0,
        "Giải trí": 1500000.0, "Đi lại": 800000.0, "Khác": 500000.0
    }
if "emergency_fund" not in st.session_state:
    st.session_state.emergency_fund = 5000000.0
if "savings_goal" not in st.session_state:
    st.session_state.savings_goal = 2960000.0
if "daily_logs" not in st.session_state:
    st.session_state.daily_logs = pd.DataFrame(columns=["Ngày", "Danh mục", "Số tiền", "Ghi chú"])

current_month_str = datetime.now().strftime("%Y-%m")
if "monthly_history" not in st.session_state or not st.session_state.monthly_history:
    st.session_state.monthly_history = {
        "2026-06": {
            "income": 15000000.0,
            "expenses": {
                "Tiền nhà": 3500000.0, "Thực phẩm": 3800000.0, "Điện nước & Mạng": 950000.0,
                "Giải trí": 2000000.0, "Đi lại": 750000.0, "Khác": 600000.0
            },
            "savings_goal": 3000000.0
        }
    }

if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"role": "assistant", "content": "👋 **Xin chào! Tôi là FinBot AI** - Trợ lý tài chính thông minh của bạn.\n\nHãy bấm vào các gợi ý nhanh bên dưới hoặc đặt câu hỏi để tôi phân tích dòng tiền giúp bạn nhé!"}
    ]

if "inp_income" not in st.session_state:
    st.session_state.inp_income = f"{int(st.session_state.income):,}"
if "inp_rent" not in st.session_state:
    st.session_state.inp_rent = f"{int(st.session_state.fixed_expenses.get('Tiền nhà', 0)):,}"
if "inp_food" not in st.session_state:
    st.session_state.inp_food = f"{int(st.session_state.fixed_expenses.get('Thực phẩm', 0)):,}"
if "inp_util" not in st.session_state:
    st.session_state.inp_util = f"{int(st.session_state.fixed_expenses.get('Điện nước & Mạng', 0)):,}"
if "inp_ent" not in st.session_state:
    st.session_state.inp_ent = f"{int(st.session_state.fixed_expenses.get('Giải trí', 0)):,}"
if "inp_trans" not in st.session_state:
    st.session_state.inp_trans = f"{int(st.session_state.fixed_expenses.get('Đi lại', 0)):,}"
if "inp_other" not in st.session_state:
    st.session_state.inp_other = f"{int(st.session_state.fixed_expenses.get('Khác', 0)):,}"

if "inp_log_amt" not in st.session_state:
    st.session_state.inp_log_amt = "0"
if "inp_log_note" not in st.session_state:
    st.session_state.inp_log_note = ""

# ----------------------------------------------------
# 8. POP-UP MODAL THIẾT LẬP KHI KHỞI CHẠY (3 BƯỚC)
# ----------------------------------------------------
@st.dialog("⚙️ Thiết Lập Khai Báo Tài Chính", width="large")
def show_setup_modal():
    if st.session_state.modal_step == 1:
        st.caption("Bước 1/3: Khai báo Thu nhập & Các khoản chi phí cố định ước tính")
        
        st.text_input(
            "💵 Thu nhập cố định hàng tháng (VNĐ):", 
            key="inp_income",
            on_change=format_money_callback,
            args=("inp_income",)
        )
        inc_val = parse_amount(st.session_state.inp_income)
        st.caption(f"➔ Số tiền: **{inc_val:,.0f} VNĐ** *({num2vi_words(inc_val)})*")
        
        st.write("---")
        st.markdown("**📌 Chi tiêu dự kiến hàng tháng:**")
        col_a, col_b = st.columns(2)
        with col_a:
            st.text_input("Tiền nhà / Thuê phòng:", key="inp_rent", on_change=format_money_callback, args=("inp_rent",))
            rent_val = parse_amount(st.session_state.inp_rent)
            st.caption(f"➔ Số tiền: **{rent_val:,.0f} VNĐ** *({num2vi_words(rent_val)})*")

            st.text_input("Thực phẩm / Ăn uống:", key="inp_food", on_change=format_money_callback, args=("inp_food",))
            food_val = parse_amount(st.session_state.inp_food)
            st.caption(f"➔ Số tiền: **{food_val:,.0f} VNĐ** *({num2vi_words(food_val)})*")

            st.text_input("Điện, nước, Internet:", key="inp_util", on_change=format_money_callback, args=("inp_util",))
            util_val = parse_amount(st.session_state.inp_util)
            st.caption(f"➔ Số tiền: **{util_val:,.0f} VNĐ** *({num2vi_words(util_val)})*")

        with col_b:
            st.text_input("Giải trí / Giao lưu:", key="inp_ent", on_change=format_money_callback, args=("inp_ent",))
            ent_val = parse_amount(st.session_state.inp_ent)
            st.caption(f"➔ Số tiền: **{ent_val:,.0f} VNĐ** *({num2vi_words(ent_val)})*")

            st.text_input("Đi lại / Xăng xe:", key="inp_trans", on_change=format_money_callback, args=("inp_trans",))
            trans_val = parse_amount(st.session_state.inp_trans)
            st.caption(f"➔ Số tiền: **{trans_val:,.0f} VNĐ** *({num2vi_words(trans_val)})*")

            st.text_input("Khoản khác:", key="inp_other", on_change=format_money_callback, args=("inp_other",))
            other_val = parse_amount(st.session_state.inp_other)
            st.caption(f"➔ Số tiền: **{other_val:,.0f} VNĐ** *({num2vi_words(other_val)})*")

        if st.button("Tiếp theo: Thiết lập Quỹ Khẩn Cấp ➡️", use_container_width=True):
            st.session_state.income = inc_val
            st.session_state.fixed_expenses = {
                "Tiền nhà": rent_val,
                "Thực phẩm": food_val,
                "Điện nước & Mạng": util_val,
                "Giải trí": ent_val,
                "Đi lại": trans_val,
                "Khác": other_val
            }
            if "inp_emergency" not in st.session_state:
                st.session_state.inp_emergency = f"{int(st.session_state.get('emergency_fund', 5000000.0)):,}"
            st.session_state.modal_step = 2
            st.rerun()

    elif st.session_state.modal_step == 2:
        st.caption("Bước 2/3: Khai báo Quỹ Khẩn Cấp dự phòng")
        st.info("💡 **Quỹ Khẩn Cấp:** Là số tiền dự phòng không được dùng tới (trừ trường hợp khẩn cấp). Hệ thống sẽ dùng số này làm mốc tham chiếu và hiển thị cảnh báo khi số dư chạm/xuống dưới mức này.")

        st.text_input(
            "🚨 Hạn mức Quỹ Khẩn Cấp dự phòng (VNĐ):", 
            key="inp_emergency",
            on_change=format_money_callback,
            args=("inp_emergency",)
        )
        em_val = parse_amount(st.session_state.inp_emergency)
        st.caption(f"➔ Mức bảo vệ: **{em_val:,.0f} VNĐ** *({num2vi_words(em_val)})*")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ Quay lại", use_container_width=True):
                st.session_state.modal_step = 1
                st.rerun()
        with col2:
            if st.button("Tiếp theo: Đặt mục tiêu tiết kiệm ➡️", use_container_width=True):
                st.session_state.emergency_fund = em_val
                total_exp = sum(st.session_state.fixed_expenses.values())
                max_possible = max(0.0, st.session_state.income - total_exp)
                st.session_state.inp_goal = f"{int(max_possible * 0.8):,}"
                st.session_state.modal_step = 3
                st.rerun()

    elif st.session_state.modal_step == 3:
        st.caption("Bước 3/3: Đặt mục tiêu tích lũy tháng")
        total_exp = sum(st.session_state.fixed_expenses.values())
        max_possible = max(0.0, st.session_state.income - total_exp)

        st.info(f"💡 Dựa trên thu nhập ({st.session_state.income:,.0f} VNĐ) và tổng chi cố định ({total_exp:,.0f} VNĐ), khả năng tiết kiệm tối đa của bạn là **{max_possible:,.0f} VNĐ**.")

        if "inp_goal" not in st.session_state:
            st.session_state.inp_goal = f"{int(max_possible * 0.8):,}"

        st.text_input(
            "🎯 Mục tiêu tiết kiệm tháng này (VNĐ):", 
            key="inp_goal",
            on_change=format_money_callback,
            args=("inp_goal",)
        )
        goal_val = parse_amount(st.session_state.inp_goal)
        st.caption(f"➔ Số tiền: **{goal_val:,.0f} VNĐ** *({num2vi_words(goal_val)})*")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ Quay lại", use_container_width=True):
                st.session_state.modal_step = 2
                st.rerun()
        with col2:
            if st.button("Hoàn thành & Vào Dashboard 🚀", use_container_width=True):
                st.session_state.savings_goal = goal_val
                st.session_state.configured = True
                st.session_state.modal_step = 1
                sync_data()
                st.rerun()

if not st.session_state.configured:
    show_setup_modal()

# HIỂN THỊ DIALOG XÁC NHẬN NẾU CÓ CẢNH BÁO KHẨN CẤP
if st.session_state.get("show_confirm_dialog", False):
    pending = st.session_state.get("pending_expense", {})
    if pending:
        confirm_emergency_expense_modal(
            pending["amt"],
            pending["log_date"],
            pending["log_cat"],
            pending["log_note"],
            pending["future_bal"],
            pending["em_fund"]
        )

cur_exp_combined = st.session_state.fixed_expenses.copy()
if not st.session_state.daily_logs.empty:
    for _, row in st.session_state.daily_logs.iterrows():
        cat = row["Danh mục"]
        cur_exp_combined[cat] = cur_exp_combined.get(cat, 0.0) + row["Số tiền"]

st.session_state.monthly_history[current_month_str] = {
    "income": st.session_state.income,
    "expenses": cur_exp_combined,
    "savings_goal": st.session_state.savings_goal
}

# ----------------------------------------------------
# 9. HEADER & TOP METRICS CARDS
# ----------------------------------------------------
head_col1, head_col2 = st.columns([2.5, 1.5])
with head_col1:
    st.markdown('<div class="dash-header">💎 FinFlow Dashboard</div>', unsafe_allow_html=True)
    st.caption(f"Tài khoản: **{st.session_state.current_user.upper()}** | Hệ thống quản lý tài chính cá nhân")
with head_col2:
    btn_c1, btn_c2 = st.columns(2)
    with btn_c1:
        st.button("⚙️ Cấu hình", use_container_width=True, on_click=open_config_callback)
    with btn_c2:
        if st.button("🚪 Đăng xuất", use_container_width=True):
            logout_user()

st.write("")

fixed_exp_total = sum(st.session_state.fixed_expenses.values())
logged_exp_total = st.session_state.daily_logs["Số tiền"].sum() if not st.session_state.daily_logs.empty else 0.0
grand_total_exp = fixed_exp_total + logged_exp_total
remaining_balance = st.session_state.income - grand_total_exp
diff_goal = remaining_balance - st.session_state.savings_goal
emergency_fund_val = st.session_state.get("emergency_fund", 5000000.0)

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">TỔNG THU NHẬP</div>
        <div class="metric-value">{st.session_state.income:,.0f} <span style="font-size:1.1rem; color:var(--text-secondary);">đ</span></div>
        <div class="metric-sub sub-green">⚡ Cố định hàng tháng</div>
    </div>
    """, unsafe_allow_html=True)

with m2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">TỔNG CHI TIÊU</div>
        <div class="metric-value">{grand_total_exp:,.0f} <span style="font-size:1.1rem; color:var(--text-secondary);">đ</span></div>
        <div class="metric-sub sub-red">📌 Cố định: {fixed_exp_total:,.0f} đ | Phát sinh: {logged_exp_total:,.0f} đ</div>
    </div>
    """, unsafe_allow_html=True)

with m3:
    is_danger = remaining_balance <= emergency_fund_val
    sub_color = "sub-red" if is_danger else "sub-green"
    sub_text = f"🚨 Chạm ngưỡng khẩn cấp ({emergency_fund_val:,.0f} đ)" if is_danger else f"🛡️ An toàn (> {emergency_fund_val:,.0f} đ)"
    
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">SỐ DƯ CÒN LẠI</div>
        <div class="metric-value">{remaining_balance:,.0f} <span style="font-size:1.1rem; color:var(--text-secondary);">đ</span></div>
        <div class="metric-sub {sub_color}">{sub_text}</div>
    </div>
    """, unsafe_allow_html=True)

with m4:
    diff_text = f"+{diff_goal:,.0f} đ so với mục tiêu" if diff_goal >= 0 else f"{diff_goal:,.0f} đ so với mục tiêu"
    diff_class = "sub-green" if diff_goal >= 0 else "sub-red"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">MỤC TIÊU TIẾT KIỆM</div>
        <div class="metric-value">{st.session_state.savings_goal:,.0f} <span style="font-size:1.1rem; color:var(--text-secondary);">đ</span></div>
        <div class="metric-sub {diff_class}">🎯 {diff_text}</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# THÔNG BÁO CẢNH BÁO KHI SỐ DƯ CHẠM NGUỠNG KHẨN CẤP
if remaining_balance <= emergency_fund_val:
    st.error(
        f"🚨 **CẢNH BÁO TÀI CHÍNH NGUY HIỂM:** Số dư hiện tại của bạn (**{remaining_balance:,.0f} VNĐ**) "
        f"đã chạm/xuống dưới **Quỹ Khẩn Cấp ({emergency_fund_val:,.0f} VNĐ)**! "
        f"Vui lòng hạn chế tối đa các khoản chi không cấp thiết."
    )

if st.session_state.savings_goal > 0:
    progress_ratio = min(max(remaining_balance / st.session_state.savings_goal, 0.0), 1.0)
    st.progress(progress_ratio)
    if remaining_balance >= st.session_state.savings_goal:
        st.success(f"🎉 Rất tốt! Số dư hiện tại ({remaining_balance:,.0f} VNĐ) đã đạt mục tiêu tích lũy tháng này.")
    else:
        st.warning(f"⚠️ Cần chú ý: Số dư còn lại ({remaining_balance:,.0f} VNĐ) chưa đạt mục tiêu tiết kiệm ({st.session_state.savings_goal:,.0f} VNĐ).")

st.write("")

# ----------------------------------------------------
# 10. THANH DI CHUYỂN TABS CHÍNH
# ----------------------------------------------------
tab_stats, tab_history, tab_ai = st.tabs([
    "📊  Thống kê & Quản lý Chi tiêu", 
    "📅  Lịch sử & So sánh các tháng", 
    "🤖  Trợ lý Tài chính AI (FinBot)"
])

# ================= TAB 1: THỐNG KÊ & PHÂN BỔ =================
with tab_stats:
    st.write("")
    col_chart1, col_chart2, col_form = st.columns([1, 1, 0.95])

    with col_chart1:
        st.markdown("##### 📊 Phân bổ ngân sách cố định")
        df_fixed = pd.DataFrame(list(st.session_state.fixed_expenses.items()), columns=["Danh mục", "Số tiền"])
        
        fig1 = px.pie(
            df_fixed, 
            values="Số tiền", 
            names="Danh mục", 
            hole=0.68,
            color_discrete_sequence=['#6366F1', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4']
        )
        
        fig1.update_traces(
            textposition='inside',
            textinfo='percent',
            insidetextfont=dict(size=13, color='#FFFFFF', family="Plus Jakarta Sans"),
            hovertemplate="<b>%{label}</b><br>💵 Số tiền: <b>%{value:,.0f} VNĐ</b><br>📈 Tỷ lệ: <b>%{percent}</b><extra></extra>",
            marker=dict(line=dict(color='rgba(128,128,128,0.2)', width=2))
        )

        fig1.add_annotation(
            text=f"<span style='font-size:12px; font-weight:700;'>TỔNG CỐ ĐỊNH</span><br><b style='font-size:18px;'>{fixed_exp_total:,.0f} đ</b>",
            x=0.5, y=0.5,
            showarrow=False,
            align="center"
        )

        fig1.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Plus Jakarta Sans", size=13),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.35,
                xanchor="center",
                x=0.5,
                font=dict(size=13)
            ),
            margin=dict(t=20, b=60, l=10, r=10),
            height=380
        )
        st.plotly_chart(fig1, use_container_width=True, theme="streamlit")

    with col_chart2:
        st.markdown("##### 📈 Chi tiêu thực tế & Số dư còn lại")
        
        chart2_list = []
        for cat, amt in st.session_state.fixed_expenses.items():
            if amt > 0:
                chart2_list.append({"Danh mục": cat, "Số tiền": amt})
                
        if logged_exp_total > 0:
            chart2_list.append({"Danh mục": "Chi phát sinh thực tế", "Số tiền": logged_exp_total})
            
        if remaining_balance > 0:
            chart2_list.append({"Danh mục": "Số dư còn lại", "Số tiền": remaining_balance})

        df_chart2 = pd.DataFrame(chart2_list)

        color_map = {
            "Số dư còn lại": "#10B981" if remaining_balance > emergency_fund_val else "#EF4444",
            "Chi phát sinh thực tế": "#FB7185",
        }

        fig2 = px.pie(
            df_chart2, 
            values="Số tiền", 
            names="Danh mục", 
            hole=0.68,
            color="Danh mục",
            color_discrete_map=color_map,
            color_discrete_sequence=['#6366F1', '#8B5CF6', '#F59E0B', '#38BDF8', '#10B981', '#EC4899', '#F97316']
        )

        bal_color = "#10B981" if remaining_balance > emergency_fund_val else "#EF4444"
        bal_label = "SỐ DƯ CÒN LẠI" if remaining_balance >= 0 else "THÂM HỤT"

        fig2.update_traces(
            textposition='inside',
            textinfo='percent',
            insidetextfont=dict(size=13, color='#FFFFFF', family="Plus Jakarta Sans"),
            hovertemplate="<b>%{label}</b><br>💵 Số tiền: <b>%{value:,.0f} VNĐ</b><br>📈 Tỷ lệ: <b>%{percent}</b><extra></extra>",
            marker=dict(line=dict(color='rgba(128,128,128,0.2)', width=2))
        )

        fig2.add_annotation(
            text=f"<span style='font-size:12px; font-weight:700;'>{bal_label}</span><br><b style='font-size:18px; color:{bal_color};'>{remaining_balance:,.0f} đ</b>",
            x=0.5, y=0.5,
            showarrow=False,
            align="center"
        )

        fig2.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Plus Jakarta Sans", size=13),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.35,
                xanchor="center",
                x=0.5,
                font=dict(size=13)
            ),
            margin=dict(t=20, b=60, l=10, r=10),
            height=380
        )
        st.plotly_chart(fig2, use_container_width=True, theme="streamlit")

    with col_form:
        st.markdown("##### ✍️ Ghi nhận khoản chi thực tế")
        log_date = st.date_input("Ngày giao dịch", key="inp_log_date")
        log_cat = st.selectbox("Danh mục", list(st.session_state.fixed_expenses.keys()), key="inp_log_cat")
        
        st.text_input(
            "Số tiền (VNĐ)",
            key="inp_log_amt",
            on_change=format_money_callback,
            args=("inp_log_amt",)
        )
        log_amt = parse_amount(st.session_state.inp_log_amt)
        st.caption(f"➔ Số tiền: **{log_amt:,.0f} VNĐ** *({num2vi_words(log_amt)})*")
        
        log_note = st.text_input("Ghi chú khoản chi", key="inp_log_note", placeholder="VD: Mua thực phẩm siêu thị")
        
        st.button("➕ Thêm khoản chi", use_container_width=True, on_click=handle_add_expense_click)

        if st.session_state.get("expense_error_msg"):
            st.error(st.session_state.expense_error_msg)
            st.session_state.expense_error_msg = None

        if st.session_state.get("expense_added_msg"):
            st.success("Đã ghi nhận khoản chi thành công!")
            st.session_state.expense_added_msg = False

    st.divider()

    log_count = len(st.session_state.daily_logs)
    head_log_a, head_log_b = st.columns([2, 1])
    with head_log_a:
        st.markdown(f"##### 📋 Nhật ký chi tiêu thực tế trong tháng ({log_count} giao dịch)")
    with head_log_b:
        if log_count > 0:
            st.markdown(f"<div style='text-align: right; color: #10B981; font-weight: 700; font-size: 1.05rem;'>💰 Tổng chi phát sinh: {logged_exp_total:,.0f} VNĐ</div>", unsafe_allow_html=True)

    if not st.session_state.daily_logs.empty:
        df_display = st.session_state.daily_logs.copy()
        df_display.reset_index(inplace=True)
        df_display.rename(columns={"index": "STT"}, inplace=True)
        df_display["STT"] = df_display["STT"] + 1
        
        df_display["Danh mục hiển thị"] = df_display["Danh mục"].apply(lambda c: f"{CAT_ICONS.get(c, '📌')} {c}")
        df_display["Số tiền hiển thị"] = df_display["Số tiền"].apply(lambda x: f"{int(x):,} VNĐ")

        df_show = df_display[["STT", "Ngày", "Danh mục hiển thị", "Số tiền hiển thị", "Ghi chú"]].copy()
        df_show.columns = ["STT", "📅 Ngày", "🏷️ Danh mục", "💵 Số tiền", "📝 Ghi chú"]

        selected_rows = []
        try:
            event = st.dataframe(
                df_show,
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="multi-row",
                key="daily_logs_table_grid"
            )
            if hasattr(event, "selection") and event.selection:
                selected_rows = event.selection.get("rows", [])
        except Exception:
            selected_rows = []

        st.caption("💡 *Mẹo: Tích chọn một hoặc nhiều dòng trực tiếp trên bảng hoặc chọn từ danh sách thả xuống dưới đây để xóa.*")

        st.write("")
        col_del_action, col_del_select = st.columns([1, 1.3])
        
        with col_del_action:
            if selected_rows:
                st.warning(f"📌 Bạn đang chọn **{len(selected_rows)}** khoản chi trên bảng.")
                st.button(
                    "🗑️ Xóa các mục đã chọn trên bảng", 
                    type="primary", 
                    use_container_width=True, 
                    on_click=delete_grid_callback
                )

        with col_del_select:
            options_dict = {
                f"Mục #{idx+1} | {row['Ngày']} | {row['Danh mục']} | {row['Số tiền']:,.0f} VNĐ ({row['Ghi chú'] or 'Không ghi chú'})": idx
                for idx, row in st.session_state.daily_logs.iterrows()
            }
            st.session_state["current_options_dict"] = options_dict

            selected_dropdown_items = st.multiselect(
                "🎯 Hoặc chọn khoản chi muốn xóa theo danh sách:",
                options=list(options_dict.keys()),
                placeholder="Chọn một hoặc nhiều giao dịch nhập nhầm...",
                key="multiselect_delete_logs"
            )
            
            if selected_dropdown_items:
                st.button(
                    "🗑️ Xóa các mục đã chọn trong danh sách", 
                    use_container_width=True, 
                    on_click=delete_multiselect_callback
                )
    else:
        st.info("Chưa có phát sinh chi tiêu nào được ghi nhận trong tháng này.")


# ================= TAB 2: LỊCH SỬ & SO SÁNH CÁC THÁNG =================
with tab_history:
    st.write("")
    st.markdown("##### 📅 Quản lý Lịch sử & Đối chiếu Chi tiêu các tháng")
    
    all_months = sorted(list(st.session_state.monthly_history.keys()), reverse=True)
    comp_months_options = [m for m in all_months if m != current_month_str] or all_months

    if "comp_month_selected" not in st.session_state or st.session_state.comp_month_selected not in comp_months_options:
        st.session_state.comp_month_selected = comp_months_options[0]

    def on_change_comp_top():
        st.session_state.comp_month_selected = st.session_state.comp_month_top

    def on_change_comp_bottom():
        st.session_state.comp_month_selected = st.session_state.comp_month_bottom

    h_col1, h_col2 = st.columns([1, 1.2])
    
    with h_col1:
        st.markdown("###### 📝 Nhập / Chỉnh sửa dữ liệu tháng cũ")
        
        now_dt = datetime.now()
        year_options = list(range(now_dt.year - 3, now_dt.year + 4))
        
        m_col1, m_col2 = st.columns(2)
        with m_col1:
            sel_year = st.selectbox(
                "Chọn năm:", 
                year_options, 
                index=year_options.index(now_dt.year),
                key="sel_hist_year"
            )
        with m_col2:
            sel_month = st.selectbox(
                "Chọn tháng:", 
                [f"{i:02d}" for i in range(1, 13)], 
                index=now_dt.month - 1,
                key="sel_hist_month"
            )
            
        hist_month = f"{sel_year}-{sel_month}"
        
        existing_data = st.session_state.monthly_history.get(hist_month, {
            "income": 15000000.0,
            "expenses": st.session_state.fixed_expenses.copy(),
            "savings_goal": 3000000.0
        })

        if f"h_inc_str_{hist_month}" not in st.session_state:
            st.session_state[f"h_inc_str_{hist_month}"] = f"{int(existing_data['income']):,}"

        st.text_input(
            f"Thu nhập tháng {hist_month} (VNĐ):",
            key=f"h_inc_str_{hist_month}",
            on_change=format_money_callback,
            args=(f"h_inc_str_{hist_month}",)
        )
        h_inc = parse_amount(st.session_state[f"h_inc_str_{hist_month}"])
        st.caption(f"➔ Số tiền: **{h_inc:,.0f} VNĐ** *({num2vi_words(h_inc)})*")
        
        st.markdown("**Chi tiêu theo từng danh mục:**")
        h_exps = {}
        h_exp_cols = st.columns(2)
        idx = 0
        for cat in st.session_state.fixed_expenses.keys():
            col_target = h_exp_cols[idx % 2]
            prev_val = float(existing_data["expenses"].get(cat, 0.0))
            
            key_cat = f"hist_{hist_month}_{cat}"
            if key_cat not in st.session_state:
                st.session_state[key_cat] = f"{int(prev_val):,}"

            with col_target:
                st.text_input(
                    f"{cat}:",
                    key=key_cat,
                    on_change=format_money_callback,
                    args=(key_cat,)
                )
                cat_val = parse_amount(st.session_state[key_cat])
                h_exps[cat] = cat_val
                st.caption(f"➔ **{cat_val:,.0f} VNĐ**")
            idx += 1
            
        if st.button(f"💾 Lưu dữ liệu tháng {hist_month}", use_container_width=True):
            st.session_state.monthly_history[hist_month] = {
                "income": h_inc,
                "expenses": h_exps,
                "savings_goal": existing_data.get("savings_goal", 0.0)
            }
            sync_data()
            st.success(f"✅ Đã lưu thành công dữ liệu cho tháng {hist_month}!")
            st.rerun()

    with h_col2:
        st.markdown("###### 🔍 So sánh chi tiết tháng này với tháng đối chiếu")
        
        idx_top = comp_months_options.index(st.session_state.comp_month_selected) if st.session_state.comp_month_selected in comp_months_options else 0
        comp_month = st.selectbox(
            "Chọn tháng để đối chiếu với Tháng này:", 
            comp_months_options,
            index=idx_top,
            key="comp_month_top",
            on_change=on_change_comp_top
        )
        
        cur_data = st.session_state.monthly_history[current_month_str]
        prev_data = st.session_state.monthly_history.get(comp_month, cur_data)
        
        bar_records = []
        for cat in st.session_state.fixed_expenses.keys():
            bar_records.append({"Danh mục": cat, "Kỳ": f"Tháng trước ({comp_month})", "Số tiền": prev_data["expenses"].get(cat, 0.0)})
            bar_records.append({"Danh mục": cat, "Kỳ": f"Tháng này ({current_month_str})", "Số tiền": cur_data["expenses"].get(cat, 0.0)})
        
        df_bar = pd.DataFrame(bar_records)
        
        fig_bar = px.bar(
            df_bar, 
            x="Danh mục", 
            y="Số tiền", 
            color="Kỳ", 
            barmode="group",
            color_discrete_map={
                f"Tháng trước ({comp_month})": "#6366F1",
                f"Tháng này ({current_month_str})": "#10B981"
            }
        )
        
        fig_bar.update_traces(
            hovertemplate="<b>%{x}</b><br>📅 %{fullData.name}<br>💵 Số tiền: <b>%{y:,.0f} VNĐ</b><extra></extra>",
            marker=dict(line=dict(color='rgba(128,128,128,0.2)', width=1))
        )
        
        fig_bar.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Plus Jakarta Sans", size=13),
            xaxis=dict(gridcolor='rgba(128,128,128,0.15)', title="", tickfont=dict(size=13)),
            yaxis=dict(gridcolor='rgba(128,128,128,0.15)', title="VNĐ", tickfont=dict(size=13)),
            legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="right", x=1, font=dict(size=13)),
            height=390,
            margin=dict(t=30, b=20, l=10, r=10)
        )
        st.plotly_chart(fig_bar, use_container_width=True, theme="streamlit")

    st.divider()
    
    st.markdown("##### 📈 Biến động Thu nhập - Chi tiêu - Số dư qua thời gian")
    
    history_list = []
    for m in sorted(st.session_state.monthly_history.keys()):
        m_inc = st.session_state.monthly_history[m]["income"]
        m_exp = sum(st.session_state.monthly_history[m]["expenses"].values())
        m_bal = m_inc - m_exp
        
        parts = m.split("-")
        m_label = f"Tháng {parts[1]}/{parts[0]}" if len(parts) == 2 else m
        
        history_list.append({"Tháng": m_label, "Thu nhập": m_inc, "Tổng chi tiêu": m_exp, "Số dư": m_bal})
        
    df_trend = pd.DataFrame(history_list)
    
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(x=df_trend["Tháng"], y=df_trend["Thu nhập"], mode='lines+markers', name='Thu nhập', line=dict(color='#6366F1', width=4, shape='spline'), marker=dict(size=11)))
    fig_trend.add_trace(go.Scatter(x=df_trend["Tháng"], y=df_trend["Tổng chi tiêu"], mode='lines+markers', name='Tổng chi tiêu', line=dict(color='#F43F5E', width=4, shape='spline'), marker=dict(size=11)))
    fig_trend.add_trace(go.Scatter(x=df_trend["Tháng"], y=df_trend["Số dư"], mode='lines+markers', name='Số dư tích lũy', line=dict(color='#10B981', width=4, shape='spline'), marker=dict(size=11)))
    
    fig_trend.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Plus Jakarta Sans", size=13),
        hovermode="x unified",
        xaxis=dict(gridcolor='rgba(128,128,128,0.15)', type='category'),
        yaxis=dict(gridcolor='rgba(128,128,128,0.15)', title="VNĐ"),
        legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="right", x=1),
        height=400,
        margin=dict(t=30, b=30, l=10, r=10)
    )
    st.plotly_chart(fig_trend, use_container_width=True, theme="streamlit")

    st.divider()

    col_tbl_title, col_tbl_select = st.columns([2, 1])
    with col_tbl_title:
        st.markdown(f"##### 📊 Bảng so sánh chi tiêu chi tiết ({current_month_str} vs {st.session_state.comp_month_selected})")
    with col_tbl_select:
        idx_bot = comp_months_options.index(st.session_state.comp_month_selected) if st.session_state.comp_month_selected in comp_months_options else 0
        st.selectbox(
            "Chọn tháng đối chiếu:",
            comp_months_options,
            index=idx_bot,
            key="comp_month_bottom",
            on_change=on_change_comp_bottom
        )

    tbl_comp_month = st.session_state.comp_month_selected
    if tbl_comp_month:
        cur_data = st.session_state.monthly_history[current_month_str]
        prev_data = st.session_state.monthly_history.get(tbl_comp_month, cur_data)

        html_table = f"""<div class="custom-table-container">
<table class="custom-table">
<thead>
<tr>
<th>Danh mục chi tiêu</th>
<th style="text-align: right;">Tháng trước ({tbl_comp_month})</th>
<th style="text-align: right;">Tháng này ({current_month_str})</th>
<th style="text-align: right;">Chênh lệch (VNĐ)</th>
<th style="text-align: center;">Phần trăm</th>
<th style="text-align: center;">Đánh giá</th>
</tr>
</thead>
<tbody>"""

        for cat in st.session_state.fixed_expenses.keys():
            val_cur = cur_data["expenses"].get(cat, 0.0)
            val_prev = prev_data["expenses"].get(cat, 0.0)
            diff = val_cur - val_prev
            pct = ((diff / val_prev) * 100) if val_prev > 0 else (100.0 if diff > 0 else 0.0)
            icon = CAT_ICONS.get(cat, "📌")

            if diff > 0:
                diff_str = f"+{diff:,.0f} đ"
                pct_str = f"+{pct:.1f}%"
                badge_class = "badge-red"
                status_str = "⚠️ Tăng chi tiêu"
            elif diff < 0:
                diff_str = f"{diff:,.0f} đ"
                pct_str = f"{pct:.1f}%"
                badge_class = "badge-green"
                status_str = "✅ Tiết kiệm"
            else:
                diff_str = "0 đ"
                pct_str = "0.0%"
                badge_class = "badge-gray"
                status_str = "⚪ Ổn định"

            html_table += f"""<tr>
<td>
<div class="cat-title">
<div class="cat-icon">{icon}</div>
<span>{cat}</span>
</div>
</td>
<td style="text-align: right; font-weight: 600;">{val_prev:,.0f} VNĐ</td>
<td style="text-align: right; font-weight: 700;">{val_cur:,.0f} VNĐ</td>
<td style="text-align: right;"><span class="badge-pill {badge_class}">{diff_str}</span></td>
<td style="text-align: center;"><span class="badge-pill {badge_class}">{pct_str}</span></td>
<td style="text-align: center; font-weight: 600; font-size: 0.95rem;">{status_str}</td>
</tr>"""

        html_table += """</tbody>
</table>
</div>"""

        st.markdown(html_table, unsafe_allow_html=True)


# ================= TAB 3: AI ASSISTANT (FINBOT) =================
with tab_ai:
    st.write("")
    st.markdown("##### 🤖 FinBot AI - Cố vấn tài chính cá nhân")
    st.caption(f"AI kết nối trực tiếp với dòng tiền của tài khoản {st.session_state.current_user.upper()} để phân tích.")

    q1, q2, q3 = st.columns(3)
    user_click_prompt = None
    with q1:
        if st.button("📊 Phân tích thu chi tháng này", use_container_width=True):
            user_click_prompt = "Phân tích thu chi tháng này"
    with q2:
        if st.button("💡 Tư vấn đạt mục tiêu tiết kiệm", use_container_width=True):
            user_click_prompt = "Tư vấn đạt mục tiêu tiết kiệm"
    with q3:
        if st.button("🛒 Cân nhắc hạn mức mua sắm", use_container_width=True):
            user_click_prompt = "Cân nhắc hạn mức mua sắm"

    st.write("")

    chat_container = st.container(height=420)
    with chat_container:
        for message in st.session_state.chat_history:
            avatar_icon = "🤖" if message["role"] == "assistant" else "👤"
            with st.chat_message(message["role"], avatar=avatar_icon):
                st.markdown(message["content"])

    user_prompt = st.chat_input("Nhập câu hỏi cho AI...") or user_click_prompt

    if user_prompt:
        st.session_state.chat_history.append({"role": "user", "content": user_prompt})
        
        prompt_lower = user_prompt.lower()
        exp_ratio = (grand_total_exp / st.session_state.income * 100) if st.session_state.income > 0 else 0
        
        if "phân tích" in prompt_lower or "thu chi" in prompt_lower:
            ai_reply = f"""📊 **Báo cáo phân tích tài chính ({st.session_state.current_user}):**\n- **Tổng thu nhập:** `{st.session_state.income:,.0f} VNĐ`\n- **Tổng chi tiêu:** `{grand_total_exp:,.0f} VNĐ` (Chiếm **{exp_ratio:.1f}%** thu nhập)\n- **Số dư khả dụng:** `{remaining_balance:,.0f} VNĐ`\n- **Quỹ khẩn cấp bảo vệ:** `{emergency_fund_val:,.0f} VNĐ`\n\n💡 **Đánh giá:** {"⚠️ Tỷ lệ chi tiêu của bạn đang khá cao (>70%). Hãy kiểm soát để giữ an toàn cho Quỹ khẩn cấp!" if exp_ratio > 70 else "✅ Tỷ lệ chi tiêu của bạn rất lành mạnh và an toàn."}"""
        
        elif "tiết kiệm" in prompt_lower or "mục tiêu" in prompt_lower:
            ai_reply = f"""💡 **Chiến lược đạt mục tiêu tiết kiệm:**\n- **Mục tiêu tháng:** `{st.session_state.savings_goal:,.0f} VNĐ`\n- **Số dư hiện tại:** `{remaining_balance:,.0f} VNĐ`\n- **Tình trạng:** {'🎉 Bạn đã xuất sắc hoàn thành mục tiêu tích lũy!' if diff_goal >= 0 else f'⚠️ Còn thiếu **{abs(diff_goal):,.0f} VNĐ**. Hãy ưu tiên trích ngay 20% thu nhập đầu tháng vào quỹ tiết kiệm!'}"""

        elif "mua" in prompt_lower or "hạn mức" in prompt_lower:
            ai_reply = f"""🛒 **Tư vấn hạn mức mua sắm:**\nSố dư khả dụng của bạn là **{remaining_balance:,.0f} VNĐ** (Quỹ khẩn cấp giữ mức **{emergency_fund_val:,.0f} VNĐ**).\n- Khoản mua sắm **dưới {max(0.0, remaining_balance - emergency_fund_val) * 0.2:,.0f} VNĐ** nằm trong hạn mức an toàn.\n- Tránh mua các khoản vượt quá mức dôi dư để không vi phạm Quỹ Khẩn Cấp!"""

        else:
            ai_reply = f"""Tôi đã ghi nhận thắc mắc của bạn! Dựa trên ngân sách khả dụng **{remaining_balance:,.0f} VNĐ**, hãy thử chọn các gợi ý phía trên hoặc hỏi cụ thể hơn để tôi hỗ trợ nhé!"""

        st.session_state.chat_history.append({"role": "assistant", "content": ai_reply})
        st.rerun()
