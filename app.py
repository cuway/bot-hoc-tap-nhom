import os
import shutil
import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import docx

# ----------------- CẤU HÌNH TRANG WEB -----------------
st.set_page_config(
    page_title="Góc Học Tập - Trợ Lý AI Nhóm",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Thư mục lưu trữ tài liệu
DATA_DIR = os.path.join(os.path.dirname(__file__), "uploaded_docs")
os.makedirs(DATA_DIR, exist_ok=True)

# ----------------- TIỆN ÍCH ĐỌC VĂN BẢN -----------------
def extract_text_from_file(file_path, file_name):
    """Trích xuất nội dung văn bản kèm thông tin trang."""
    results = []
    ext = os.path.splitext(file_name)[1].lower()

    try:
        if ext == ".pdf":
            reader = PdfReader(file_path)
            for page_idx, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                if text.strip():
                    results.append(f"--- [Tài liệu: {file_name} | Trang {page_idx + 1}] ---\n{text.strip()}")
        elif ext in [".docx", ".doc"]:
            doc = docx.Document(file_path)
            full_text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
            if full_text.strip():
                results.append(f"--- [Tài liệu: {file_name}] ---\n{full_text.strip()}")
        elif ext in [".txt", ".md"]:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
                if text.strip():
                    results.append(f"--- [Tài liệu: {file_name}] ---\n{text.strip()}")
    except Exception as e:
        st.warning(f"Không thể đọc file {file_name}: {str(e)}")

    return "\n\n".join(results)

def get_all_knowledge_text():
    """Đọc toàn bộ văn bản của tất cả tài liệu hiện có trong kho."""
    files = os.listdir(DATA_DIR)
    combined = []
    for f in files:
        path = os.path.join(DATA_DIR, f)
        if os.path.isfile(path):
            text = extract_text_from_file(path, f)
            if text:
                combined.append(text)
    return "\n\n".join(combined)

def find_working_model(api_key):
    """Tự động phát hiện model Gemini khả dụng trên tài khoản của bạn."""
    try:
        genai.configure(api_key=api_key)
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # Danh sách ưu tiên theo thứ tự
        preferences = [
            "gemini-1.5-flash",
            "gemini-1.5-flash-latest",
            "gemini-2.0-flash",
            "gemini-1.5-flash-001",
            "gemini-1.5-flash-002",
            "gemini-1.5-pro",
            "gemini-pro"
        ]
        
        for pref in preferences:
            for m in models:
                if pref in m:
                    return m
        if models:
            return models[0]
    except Exception:
        pass
    return "gemini-1.5-flash-latest"

# ----------------- THANH BÊN (SIDEBAR): KHO TÀI LIỆU NHÓM -----------------
with st.sidebar:
    st.header("📂 Kho Tài Liệu Nhóm")

    # 1. Quản lý Gemini API Key
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]

    if api_key:
        st.success("✅ Đã kết nối Gemini API")
    else:
        api_key = st.text_input(
            "🔑 Nhập Google Gemini API Key:",
            type="password",
            placeholder="AIzaSy...",
            help="Lấy miễn phí tại: https://aistudio.google.com/"
        )

    st.markdown("---")

    # 2. Upload tài liệu vào kho chung
    st.subheader("📤 Thêm tài liệu mới")
    uploaded_files = st.file_uploader(
        "Kéo thả sách, slide, bài tập vào đây:",
        type=["pdf", "docx", "txt", "md"],
        accept_multiple_files=True
    )

    if st.button("➕ Nạp vào Kho Dữ Liệu", type="primary", use_container_width=True):
        if not uploaded_files:
            st.warning("Vui lòng chọn ít nhất một tệp tài liệu.")
        else:
            with st.spinner("Đang lưu trữ tài liệu vào kho..."):
                count = 0
                for up_file in uploaded_files:
                    save_path = os.path.join(DATA_DIR, up_file.name)
                    with open(save_path, "wb") as f:
                        f.write(up_file.getbuffer())
                    count += 1
                st.success(f"🎉 Đã thêm thành công {count} tài liệu vào kho!")
                st.rerun()

    st.markdown("---")

    # 3. Danh sách tài liệu trong kho
    st.subheader("📑 Tài liệu hiện có trong kho:")
    existing_files = [f for f in os.listdir(DATA_DIR) if os.path.isfile(os.path.join(DATA_DIR, f))]
    if existing_files:
        for f in existing_files:
            st.markdown(f"- 📄 **{f}**")

        st.markdown("")
        if st.button("🗑️ Xóa toàn bộ kho tài liệu", help="Làm trống kho tài liệu khi bắt đầu môn học mới"):
            shutil.rmtree(DATA_DIR, ignore_errors=True)
            os.makedirs(DATA_DIR, exist_ok=True)
            st.warning("Đã làm trống kho tài liệu.")
            st.rerun()
    else:
        st.info("Chưa có tài liệu nào. Hãy tải tài liệu ở trên!")

# ----------------- KHU VỰC CHAT CHÍNH -----------------
st.title("🎓 Trợ Lý Học Tập AI - Nhóm Học Tập")
st.caption("Tra cứu giáo trình, giải đáp bài tập và tóm tắt bài giảng dựa trên kho dữ liệu của nhóm.")

# Khởi tạo lịch sử chat
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Chào bạn! Mình là trợ lý AI của nhóm. Bạn cần hỏi phần nào trong tài liệu cứ nhắn mình nhé! ✨"}
    ]

# Hiển thị lịch sử chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Nhận câu hỏi từ sinh viên
user_query = st.chat_input("Hỏi AI về bất kỳ nội dung nào trong tài liệu học tập...")

if user_query:
    if not api_key:
        st.warning("⚠️ Chưa có Gemini API Key. Vui lòng cấu hình ở cột bên trái.")
    elif not existing_files:
        st.warning("⚠️ Kho tài liệu đang trống. Bạn hãy tải tài liệu lên ở cột bên trái trước nhé!")
    else:
        # Hiển thị câu hỏi của học sinh
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        # Trả lời
        with st.chat_message("assistant"):
            with st.spinner("AI đang tra cứu tài liệu và suy nghĩ câu trả lời..."):
                try:
                    genai.configure(api_key=api_key)
                    
                    # Tự động chọn model khả dụng tốt nhất
                    chosen_model = find_working_model(api_key)
                    
                    # Lấy toàn bộ tài liệu trong kho
                    knowledge_base_text = get_all_knowledge_text()

                    system_instruction = (
                        "Bạn là một gia sư/trợ lý học tập thông minh và tận tâm cho một nhóm sinh viên.\n"
                        "Dưới đây là toàn bộ KHO TÀI LIỆU HỌC TẬP của nhóm:\n"
                        "=======================\n"
                        f"{knowledge_base_text}\n"
                        "=======================\n\n"
                        "NGUYÊN TẮC TRẢ LỜI:\n"
                        "1. Chỉ trả lời dựa trên thông tin trong kho tài liệu trên. Trả lời bằng tiếng Việt rõ ràng, dễ hiểu, logic.\n"
                        "2. Nếu tài liệu không có thông tin, hãy thành thật trả lời: 'Tài liệu hiện tại của nhóm chưa đề cập đến phần này.' Tuyệt đối không tự bịa đặt.\n"
                        "3. BẮT BUỘC TRÍCH DẪN NGUỒN: Cuối câu trả lời, hãy ghi rõ trích dẫn từ tài liệu nào và trang số mấy (ví dụ: '📌 Nguồn: GT Lập trình căn bản.pdf - Trang 12')."
                    )

                    model = genai.GenerativeModel(
                        model_name=chosen_model,
                        system_instruction=system_instruction
                    )

                    # Gửi câu hỏi và sinh câu trả lời
                    response = model.generate_content(user_query)
                    answer_text = response.text

                    st.markdown(answer_text)
                    st.session_state.messages.append({"role": "assistant", "content": answer_text})

                except Exception as e:
                    st.error(f"Đã xảy ra lỗi: {str(e)}")
