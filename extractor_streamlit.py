import streamlit as st
import openai
import json
import base64
import PyPDF2
import io
import docx2txt

def call_gpt4_api(content):
    print("Processing content")
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": """다음 글에서 중요한 정보를 뽑아 JSON 형식으로 정리해주세요. 그리고 주요 내용과 중요한 정보들 사이의 관계를 간단하게 요약해주세요. 모든 내용은 중학생이 이해할 수 있는 쉬운 한국어로 작성해주세요.
             다음 형식을 사용해주세요:
             {
                "schema": {
                    "key": "value",
                    ... return as many as necessary
                },
                "summary": "중학생이 이해할 수 있는 쉬운 한국어로 작성해주세요."
             }"""},
            {"role": "user", "content": f"Content: {content}"}
        ],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

def moderate_content(text):
    response = openai.moderations.create(input=text)
    return response.results[0].flagged

def auto_detect_changes(text):
    if 'schema' not in st.session_state:
        st.session_state.schema = {}
    if 'summary' not in st.session_state:
        st.session_state.summary = ""

    if text:
        with st.spinner('Processing text...'):
            if moderate_content(text):
                st.error("The input text violates our content policy. Please revise and try again.")
                return st.session_state.schema, st.session_state.summary
            
            result = call_gpt4_api(text)
            st.session_state.schema = result['schema']
            st.session_state.summary = result['summary']

    return st.session_state.schema, st.session_state.summary

def get_download_link(content, filename, text):
    b64 = base64.b64encode(content.encode()).decode()
    return f'<a href="data:file/txt;base64,{b64}" download="{filename}">{text}</a>'

def read_pdf(file):
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def read_docx(file):
    return docx2txt.process(file)

def initialize_api_key():
    if 'openai_api_key' not in st.session_state:
        st.session_state.openai_api_key = ''

    api_key = st.sidebar.text_input("Enter your OpenAI API key:", value=st.session_state.openai_api_key, type="password")
    if api_key:
        st.session_state.openai_api_key = api_key
        openai.api_key = api_key
        return True
    return False

# Streamlit app
def main():
    st.set_page_config(layout="wide")
    st.title("Real-time Text Analysis")

    if not initialize_api_key():
        st.warning("Please enter your OpenAI API key to use this app.")
        return

    # Create two columns
    col1, col2 = st.columns(2)

    # Text input and file upload in the left column
    with col1:
        text_input = st.text_area("Enter your text here:", height=200, key="text_input")
        uploaded_file = st.file_uploader("Or upload a PDF or DOCX file", type=["pdf", "docx"])

    # Process text, PDF, or DOCX
    if uploaded_file is not None:
        if uploaded_file.type == "application/pdf":
            text_input = read_pdf(uploaded_file)
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            text_input = read_docx(uploaded_file)

    # Auto-detect changes and update schema/summary
    try:
        schema, summary = auto_detect_changes(text_input)

        # Display summary in the right column
        with col2:
            st.subheader("Summary:")
            st.write(summary)
            st.markdown(get_download_link(summary, "summary.txt", "Download Summary"), unsafe_allow_html=True)

        # Display schema at the bottom
        st.subheader("Extracted Information:")
        st.json(schema)
        st.markdown(get_download_link(json.dumps(schema, indent=2), "schema.json", "Download Schema"), unsafe_allow_html=True)

    except json.JSONDecodeError as e:
        st.error(f"Error processing JSON: {str(e)}")
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()