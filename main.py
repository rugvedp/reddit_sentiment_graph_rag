import streamlit as st
from core.config import Config
from core.database import Neo4jManager
from modules.pipeline import BrandPipeline
from modules.chatbot import BrandChatbot
from sentence_transformers import SentenceTransformer
from groq import Groq
import json

# --- 1. Page Setup ---
st.set_page_config(
    page_title="Sentiment Intelligence Chat",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---- Minimal Dark Styling ----
st.markdown("""
<style>
.stApp { background-color: #0E1117; }
section[data-testid="stSidebar"] { background-color: #161B22; }
div[data-testid="stChatMessage"] {
    background-color: #1E242D;
    border-radius: 10px;
    padding: 10px;
}
</style>
""", unsafe_allow_html=True)

# --- Resources ---
@st.cache_resource
def init_resources():
    Config.init_environment()
    db = Neo4jManager()
    groq = Groq(api_key=Config.GROQ_API_KEY)
    model = SentenceTransformer(Config.EMBED_MODEL, device=Config.DEVICE)
    return db, groq, model

db, groq, embed_model = init_resources()
pipeline = BrandPipeline(db.driver, groq)
bot = BrandChatbot(db.driver, groq, embed_model)

# --- Sidebar ---
st.sidebar.title("Settings")
existing_brands = pipeline.get_all_brands()
selected_brand = st.sidebar.selectbox(
    "Active Brand",
    existing_brands if existing_brands else ["No Data Found"]
)

if st.sidebar.button("Clear Chat"):
    st.session_state.messages = []
    st.rerun()

# --- Main Chat Interface ---
if selected_brand and selected_brand != "No Data Found":

    st.title(f"Intelligence Chat: {selected_brand}")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat Input
    if prompt := st.chat_input("Ask about sentiment, clusters, or request links..."):

        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.spinner("Analyzing data..."):
            cypher = bot.generate_cypher(prompt, selected_brand)

            # Execution logic
            context_data = []

            with db.driver.session() as s:
                try:
                    # Run query for the Chat Context
                    raw_result = s.run(cypher)
                    records = [record.data() for record in raw_result]

                    for r in records:
                        # Clean data for LLM context (strip large vectors)
                        clean_row = {
                            str(k): (v if not isinstance(v, list) else v[:5])
                            for k, v in r.items()
                        }
                        context_data.append(clean_row)

                except Exception as e:
                    context_data = [{"error": "Query logic error", "details": str(e)}]

            # Fallback to vector search if Cypher returned nothing
            if not context_data or (len(context_data) == 1 and "error" in context_data[0]):
                context_data = bot.vector_search(prompt)

            # --- GENERATE LLM RESPONSE ---
            answer_prompt = (
                f"User Question: {prompt}\n"
                f"Relevant Data: {json.dumps(context_data[:15])}\n"
                "System: Provide a specific answer based on the data. If URLs exist, list them."
            )
            
            try:
                response = groq.chat.completions.create(
                    model=Config.CHAT_MODEL,
                    messages=[{"role": "user", "content": answer_prompt}]
                )
                answer = response.choices[0].message.content
            except:
                answer = "I found relevant data but encountered an error generating the summary."

            st.session_state.messages.append({"role": "assistant", "content": answer})
            with st.chat_message("assistant"):
                st.markdown(answer)

else:
    st.warning("Please run ingestion script first.")