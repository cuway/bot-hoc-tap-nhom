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

# ----------------- TIỆN ÍCH ĐỌC VĂN BẢN (CÓ BỘ NHỚ ĐỆM TỐC ĐỘ CAO) -----------------
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

@st.cache_data(show_spinner=False)
def get_all_knowledge_text():
    """Đọc toàn bộ văn bản (được lưu trong RAM để không phải đọc lại ổ cứng mỗi lần hỏi)."""
    files = os.listdir(DATA_DIR)
    combined = []
    for f in files:
        path = os.path.join(DATA_DIR, f)
        if os.path.isfile(path):
            text = extract_text_from_file(path, f)
            if text:
                combined.append(text)
    return "\n\n".join(combined)

@st.cache_data(show_spinner=False, ttl=3600)
def get_live_models(api_key):
    """Lấy danh sách các model khả dụng từ Google (lưu đệm để không phải gọi lại liên tục)."""
    try:
        genai.configure(api_key=api_key)
        live_list = []
        for m in genai.list_models():
            if "generateContent" in m.supported_generation_methods:
                name = m.name.replace("models/", "")
                live_list.append(name)
        if live_list:
            live_list.sort(key=lambda x: (0 if "3.6-flash" in x else (1 if "flash" in x else 2), x))
            return live_list
    except Exception:
        pass
    return ["gemini-3.6-flash", "gemini-1.5-flash", "gemini-2.0-flash"]

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

    # 2. Danh sách Model lấy trực tiếp từ Google
    available_models = get_live_models(api_key) if api_key else ["gemini-3.6-flash"]
    model_choice = st.selectbox(
        "🤖 Chọn mô hình AI:",
        options=available_models,
        index=0
    )

    # 3. Chế độ trả lời
    chat_mode = st.radio(
        "🎯 Chế độ trả lời:",
        options=[
            "🌐 Linh hoạt (Ưu tiên tài liệu + Cho phép hỏi ngoài lề)",
            "📚 Nghiêm ngặt (Chỉ trả lời trong tài liệu)"
        ],
        index=0
    )

    st.markdown("---")

    # 4. Upload tài liệu vào kho chung
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
                get_all_knowledge_text.clear()  # Xóa bộ nhớ đệm cũ để nạp tài liệu mới
                st.success(f"🎉 Đã thêm thành công {count} tài liệu vào kho!")
                st.rerun()

    st.markdown("---")

    # 5. Danh sách tài liệu trong kho
    st.subheader("📑 Tài liệu hiện có trong kho:")
    existing_files = [f for f in os.listdir(DATA_DIR) if os.path.isfile(os.path.join(DATA_DIR, f))]
    if existing_files:
        for f in existing_files:
            st.markdown(f"- 📄 **{f}**")

        st.markdown("")
        if st.button("🗑️ Xóa toàn bộ kho tài liệu", help="Làm trống kho tài liệu khi bắt đầu môn học mới"):
            shutil.rmtree(DATA_DIR, ignore_errors=True)
            os.makedirs(DATA_DIR, exist_ok=True)
            get_all_knowledge_text.clear()
            st.warning("Đã làm trống kho tài liệu.")
            st.rerun()
    else:
        st.info("Chưa có tài liệu nào. Hãy tải tài liệu ở trên!")

# ----------------- KHU VỰC CHAT CHÍNH -----------------
st.title("🎓 Trợ Lý Học Tập AI - Nhóm Học Tập")
st.caption(f"Đang sử dụng mô hình: **{model_choice}** | Chế độ: **{chat_mode.split('(')[0].strip()}**")

# Khởi tạo lịch sử chat
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Chào bạn! Mình là trợ lý AI của nhóm. Bạn có thể hỏi bất kỳ nội dung nào trong tài liệu hoặc kiến thức mở rộng bên ngoài nhé! ✨"}
    ]

# Hiển thị lịch sử chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Nhận câu hỏi từ sinh viên
user_query = st.chat_input("Hỏi AI về tài liệu hoặc bất kỳ kiến thức ngoài lề nào...")

if user_query:
    if not api_key:
        st.warning("⚠️ Chưa có Gemini API Key. Vui lòng cấu hình ở cột bên trái.")
    else:
        # Hiển thị câu hỏi của học sinh
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        # Trả lời với hiệu ứng gõ chữ trực tiếp (Streaming - siêu nhanh)
        with st.chat_message("assistant"):
            try:
                genai.configure(api_key=api_key)
                
                # Lấy tài liệu từ bộ nhớ RAM siêu tốc
                knowledge_base_text = get_all_knowledge_text()

                if "Linh hoạt" in chat_mode:
                    system_instruction = (
                        "Bạn là một gia sư/trợ lý học tập thông minh, thân thiện cho một nhóm học sinh/sinh viên.\n\n"
                        "Dưới đây là KHO TÀI LIỆU HỌC TẬP của nhóm (nếu có):\n"
                        "=======================\n"
                        f"{knowledge_base_text}\n"
                        "=======================\n\n"
                        "NGUYÊN TẮC TRẢ LỜI (CHẾ ĐỘ LINH HOẠT):\n"
                        "1. NẾU CÂU HỎI LIÊN QUAN ĐẾN TÀI LIỆU:\n"
                        "   - Hãy ưu tiên giải thích dựa trên tài liệu được cung cấp.\n"
                        "   - BẮT BUỘC trích dẫn nguồn ở cuối (ví dụ: '📌 Nguồn: GT Lập trình căn bản.pdf - Trang 15').\n\n"
                        "2. NẾU CÂU HỎI HỎI NGOÀI LỀ, MỞ RỘNG HOẶC TÀI LIỆU CHƯA CÓ:\n"
                        "   - Hãy dùng vốn kiến thức của bạn để giải thích chi tiết, ngắn gọn, dễ hiểu.\n"
                        "   - Ghi chú nhẹ ở cuối: '(💡 Thông tin mở rộng ngoài giáo trình nhóm)'."
                    )
                else:
                    system_instruction = (
                        "Bạn là trợ lý học tập cho sinh viên. Chỉ trả lời dựa trên kho tài liệu dưới đây:\n"
                        f"{knowledge_base_text}\n\n"
                        "Nguyên tắc: Nếu tài liệu không có thông tin, hãy thông báo tài liệu chưa đề cập, không tự trả lời."
                    )

                model = genai.GenerativeModel(
                    model_name=model_choice,
                    system_instruction=system_instruction
                )

                # Sinh câu trả lời theo thời gian thực (Streaming)
                response = model.generate_content(user_query, stream=True)
                
                def stream_chunks():
                    for chunk in response:
                        if chunk.text:
                            yield chunk.text

                # Chữ chạy ra màn hình ngay lập tức như ChatGPT
                answer_text = st.write_stream(stream_chunks)
                st.session_state.messages.append({"role": "assistant", "content": answer_text})

            except Exception as e:
                st.error(f"Đã xảy ra lỗi: {str(e)}")
