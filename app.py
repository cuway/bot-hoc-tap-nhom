import os
import shutil
import tempfile
import streamlit as st
from pypdf import PdfReader
import docx

# Các thư viện xử lý RAG & Vector Database
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document

# ----------------- CẤU HÌNH TRANG WEB -----------------
st.set_page_config(
    page_title="Góc Học Tập - Trợ Lý AI Nhóm",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Thư mục lưu trữ cố định kho tài liệu
DATA_DIR = os.path.join(os.path.dirname(__file__), "uploaded_docs")
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CHROMA_DIR, exist_ok=True)

# ----------------- HÀM TIỆN ÍCH ĐỌC FILE -----------------
def extract_text_from_file(file_path, file_name):
    """Đọc nội dung văn bản từ các định dạng PDF, DOCX, TXT kèm thông tin trang/vị trí."""
    docs = []
    ext = os.path.splitext(file_name)[1].lower()

    if ext == ".pdf":
        reader = PdfReader(file_path)
        for page_idx, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                docs.append(Document(
                    page_content=text,
                    metadata={"source": file_name, "page": page_idx + 1}
                ))
    elif ext in [".docx", ".doc"]:
        doc = docx.Document(file_path)
        full_text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        if full_text.strip():
            docs.append(Document(
                page_content=full_text,
                metadata={"source": file_name, "page": 1}
            ))
    elif ext in [".txt", ".md"]:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
            if text.strip():
                docs.append(Document(
                    page_content=text,
                    metadata={"source": file_name, "page": 1}
                ))
    return docs

def get_vectorstore(api_key):
    """Khởi tạo hoặc tải kho vector ChromaDB đã có sẵn trên máy."""
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004",
        google_api_key=api_key
    )
    return Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embeddings
    )

# ----------------- THANH BÊN (SIDEBAR): KHO TÀI LIỆU NHÓM -----------------
with st.sidebar:
    st.header("📂 Kho Tài Liệu Của Nhóm")
    
    # 1. Quản lý Gemini API Key
    # Tự động đọc từ biến môi trường nếu có, nếu chưa thì cho phép nhập
    env_api_key = os.environ.get("GEMINI_API_KEY", "")
    if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
        env_api_key = st.secrets["GEMINI_API_KEY"]
        
    if env_api_key:
        api_key = env_api_key
        st.success("✅ Đã kết nối Gemini API")
    else:
        api_key = st.text_input(
            "🔑 Nhập Google Gemini API Key:",
            type="password",
            placeholder="AIzaSy...",
            help="Lấy khóa miễn phí tại: https://aistudio.google.com/"
        )

    st.markdown("---")
    
    # 2. Upload tài liệu vào kho chung
    st.subheader("📤 Thêm tài liệu mới")
    uploaded_files = st.file_uploader(
        "Kéo thả tài liệu học tập vào đây:",
        type=["pdf", "docx", "txt", "md"],
        accept_multiple_files=True,
        help="Hỗ trợ sách giáo trình, slide bài giảng dạng PDF, Word hoặc Text."
    )

    if st.button("➕ Nạp vào Kho Dữ Liệu", type="primary", use_container_width=True):
        if not api_key:
            st.error("⚠️ Vui lòng nhập Gemini API Key trước khi nạp tài liệu!")
        elif not uploaded_files:
            st.warning("Vui lòng chọn ít nhất một tệp tài liệu.")
        else:
            with st.spinner("Đang xử lý và ghi nhớ tài liệu vào kho..."):
                all_docs = []
                for up_file in uploaded_files:
                    save_path = os.path.join(DATA_DIR, up_file.name)
                    with open(save_path, "wb") as f:
                        f.write(up_file.getbuffer())

                    docs = extract_text_from_file(save_path, up_file.name)
                    all_docs.extend(docs)

                if all_docs:
                    # Chia nhỏ văn bản để AI dễ tra cứu
                    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
                    chunks = splitter.split_documents(all_docs)

                    vectorstore = get_vectorstore(api_key)
                    vectorstore.add_documents(chunks)
                    vectorstore.persist()
                    st.success(f"🎉 Đã thêm thành công {len(uploaded_files)} tài liệu vào kho!")
                    st.rerun()
                else:
                    st.warning("Không tìm thấy nội dung văn bản hợp lệ trong các file vừa chọn.")

    st.markdown("---")

    # 3. Hiển thị danh sách tài liệu hiện có trong kho
    st.subheader("📑 Tài liệu hiện có trong kho:")
    existing_files = os.listdir(DATA_DIR)
    if existing_files:
        for f in existing_files:
            st.markdown(f"- 📄 **{f}**")
        
        st.markdown("")
        # Nút dọn dẹp kho dữ liệu nếu nhóm muốn bắt đầu môn học mới
        if st.button("🗑️ Xóa toàn bộ kho tài liệu", help="Xóa tất cả tài liệu hiện tại để bắt đầu môn mới"):
            shutil.rmtree(DATA_DIR, ignore_errors=True)
            shutil.rmtree(CHROMA_DIR, ignore_errors=True)
            os.makedirs(DATA_DIR, exist_ok=True)
            os.makedirs(CHROMA_DIR, exist_ok=True)
            st.warning("Đã làm trống kho tài liệu.")
            st.rerun()
    else:
        st.info("Chưa có tài liệu nào trong kho. Hãy tải file lên ở phía trên!")

# ----------------- KHU VỰC CHAT CHÍNH -----------------
st.title("🎓 Trợ Lý Học Tập AI - Nhóm Học Sinh / Sinh Viên")
st.caption("Tra cứu giáo trình, tóm tắt bài giảng, giải đáp thắc mắc bài tập dựa trên kho tài liệu của nhóm.")

# Khởi tạo lịch sử chat
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"role": "assistant", "content": "Chào bạn! Mình là trợ lý học tập của nhóm. Bạn cần tra cứu hoặc thắc mắc phần nào trong tài liệu cứ hỏi mình nhé! ✨"}
    ]

# Hiển thị các tin nhắn đã trò chuyện
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Xử lý khi thành viên gửi câu hỏi
user_input = st.chat_input("Hỏi AI về bất kỳ nội dung nào trong tài liệu...")

if user_input:
    # 1. Kiểm tra API Key & Kho dữ liệu
    if not api_key:
        st.warning("⚠️ Vui lòng nhập Gemini API Key ở cột bên trái để bắt đầu chat.")
    elif not existing_files:
        st.warning("⚠️ Kho tài liệu của nhóm đang trống! Hãy tải tài liệu học tập lên ở cột bên trái trước.")
    else:
        # 2. Hiển thị câu hỏi của sinh viên
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # 3. AI tìm kiếm tài liệu và trả lời
        with st.chat_message("assistant"):
            with st.spinner("Đang tra cứu kho tài liệu nhóm..."):
                try:
                    vectorstore = get_vectorstore(api_key)
                    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
                    
                    llm = ChatGoogleGenerativeAI(
                        model="gemini-1.5-flash",
                        google_api_key=api_key,
                        temperature=0.2
                    )

                    system_prompt = (
                        "Bạn là trợ lý học tập thân thiện và am hiểu cho một nhóm sinh viên.\n"
                        "Nhiệm vụ của bạn là giải đáp câu hỏi của các bạn dựa trên các đoạn tài liệu được cung cấp dưới đây.\n\n"
                        "Nguyên tắc trả lời:\n"
                        "1. Trả lời bằng tiếng Việt rõ ràng, dễ hiểu, logic, dùng các gạch đầu dòng nếu cần diễn giải.\n"
                        "2. Chỉ trả lời dựa trên thông tin có trong tài liệu. Nếu tài liệu không nhắc đến, hãy trả lời thật lòng rằng: 'Tài liệu nhóm hiện tại chưa đề cập đến nội dung này.' Không tự ý bịa đặt thông tin.\n"
                        "3. Luôn chỉ rõ kiến thức lấy từ tài liệu nào và trang nào.\n\n"
                        "Tài liệu tham khảo:\n{context}"
                    )

                    prompt = ChatPromptTemplate.from_messages([
                        ("system", system_prompt),
                        ("human", "{input}")
                    ])

                    question_answer_chain = create_stuff_documents_chain(llm, prompt)
                    rag_chain = create_retrieval_chain(retriever, question_answer_chain)

                    response = rag_chain.invoke({"input": user_input})
                    answer = response["answer"]

                    # Thu thập trích dẫn nguồn
                    sources = []
                    for doc in response.get("context", []):
                        src = doc.metadata.get("source", "Tài liệu")
                        page = doc.metadata.get("page", 1)
                        ref = f"📄 **{src}** (Trang {page})"
                        if ref not in sources:
                            sources.append(ref)

                    if sources:
                        answer += "\n\n---\n**📌 Nguồn tài liệu tham khảo:**\n" + "\n".join([f"- {s}" for s in sources])

                    st.markdown(answer)
                    st.session_state.chat_history.append({"role": "assistant", "content": answer})

                except Exception as e:
                    st.error(f"Đã xảy ra lỗi khi tra cứu: {str(e)}")
