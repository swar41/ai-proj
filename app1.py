import streamlit as st
import fitz  # PyMuPDF
import os
from pydantic import BaseModel

# Define BaseCache as required by ChatGroq
class BaseCache(BaseModel):
    pass
class Callbacks(BaseModel):
    pass

from langchain_groq import ChatGroq

# Rebuild ChatGroq model to include BaseCache
ChatGroq.model_rebuild()

from langchain.memory import ConversationBufferMemory
from langchain.agents import initialize_agent, Tool
from langchain.schema import AIMessage, HumanMessage
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import re
import json

# Page Configuration
st.set_page_config(
    page_title="🏦 Financial Report Analyzer AI",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    
    .analysis-box {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #2a5298;
        margin: 1rem 0;
    }
    
    .sidebar-info {
        background: #154c79;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .stButton > button {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        color: white;
        border: none;
        border-radius: 5px;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }
    
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    
    .user-message {
        background: black;
        border-left: 4px solid #2196f3;
    }
    
    .ai-message {
        background: black;
        border-left: 4px solid #9c27b0;
    }
</style>
""", unsafe_allow_html=True)

class FinancialAnalyzer:
    def __init__(self):
        self.chat_model = None
        self.memory = None
        self.agent = None
        self.pdf_text = ""
        
    def initialize_model(self, api_key):
        """Initialize the ChatGroq model and memory"""
        try:
            os.environ["GROQ_API_KEY"] = api_key
            self.chat_model = ChatGroq(temperature=0, model_name="llama3-70b-8192")
            self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
            
            # Initialize chat history
            self.memory.chat_memory.add_user_message("Start analyzing financial data")
            self.memory.chat_memory.add_ai_message("I am ready to analyze. Please provide the data.")
            
            return True
        except Exception as e:
            st.error(f"Error initializing model: {str(e)}")
            return False
    
    def extract_text_from_pdf(self, pdf_file):
        """Extract text from uploaded PDF file"""
        try:
            doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
            text = "\n".join([page.get_text("text") for page in doc])
            doc.close()
            self.pdf_text = text
            return text
        except Exception as e:
            st.error(f"Error extracting text from PDF: {str(e)}")
            return None
    
    def analyze_financial_report(self, query=""):
        """Analyze financial data from the report"""
        if not self.pdf_text:
            return "No PDF data available. Please upload a financial report first."
        
        prompt = f"""
        You are an expert financial analyst. Analyze the following financial report text and provide comprehensive insights.
        
        Query: {query if query else "Provide a comprehensive analysis"}
        
        Financial Report Data:
        {self.pdf_text[:6000]}  # Limit to 6000 characters
        
        Please provide:
        1. Key financial metrics and their trends
        2. Revenue analysis
        3. Profitability indicators
        4. Areas of concern or strength
        5. Future outlook based on the data
        
        Format your response in a clear, structured manner.
        """
        
        try:
            response = self.chat_model.invoke(prompt)
            return response.content
        except Exception as e:
            return f"Error analyzing report: {str(e)}"
    
    def extract_financial_metrics(self):
        """Extract key financial metrics from the PDF text"""
        metrics = {}
        
        if not self.pdf_text:
            return metrics
        
        # Common financial terms to look for
        patterns = {
            'revenue': r'revenue[:\s]*\$?\s*([\d,\.]+)\s*(?:million|billion)?',
            'net_income': r'net income[:\s]*\$?\s*([\d,\.]+)\s*(?:million|billion)?',
            'operating_margin': r'operating margin[:\s]*([\d\.]+)%?',
            'eps': r'(?:earnings per share|eps)[:\s]*\$?\s*([\d\.]+)',
            'total_expenses': r'(?:total expenses|costs and expenses)[:\s]*\$?\s*([\d,\.]+)\s*(?:million|billion)?'
        }
        
        text_lower = self.pdf_text.lower()
        
        for metric, pattern in patterns.items():
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                try:
                    # Take the first match and convert to float
                    value = matches[0].replace(',', '')
                    metrics[metric] = float(value)
                except:
                    metrics[metric] = matches[0]
        
        return metrics
    
    def setup_agent(self):
        """Setup the conversational agent with tools"""
        if not self.chat_model:
            return False
        
        pdf_tool = Tool(
            name="Financial Report Analysis",
            func=lambda query: self.analyze_financial_report(query),
            description="Analyzes financial data from uploaded reports and provides insights based on user queries."
        )
        
        try:
            self.agent = initialize_agent(
                agent="chat-conversational-react-description",
                tools=[pdf_tool],
                llm=self.chat_model,
                memory=self.memory,
                verbose=True
            )
            return True
        except Exception as e:
            st.error(f"Error setting up agent: {str(e)}")
            return False

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🏦 Financial Report Analyzer AI</h1>
        <p>Upload your financial reports and get AI-powered insights instantly</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    if 'analyzer' not in st.session_state:
        st.session_state.analyzer = FinancialAnalyzer()
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'api_key_set' not in st.session_state:
        st.session_state.api_key_set = False
    
    # Sidebar
    with st.sidebar:
        st.markdown("### 🔧 Configuration")
        
        # API Key Input
        st.markdown('<div class="sidebar-info"><h4>🔑 API Configuration</h4></div>', unsafe_allow_html=True)
        api_key = st.text_input("Enter your Groq API Key:", type="password", help="Get your API key from https://groq.com")
        
        if api_key and not st.session_state.api_key_set:
            if st.button("🚀 Initialize AI Model"):
                with st.spinner("Initializing AI model..."):
                    if st.session_state.analyzer.initialize_model(api_key):
                        st.session_state.api_key_set = True
                        st.success("✅ AI Model initialized successfully!")
                        st.rerun()
        
        if st.session_state.api_key_set:
            st.success("✅ AI Model Ready")
        
        # File Upload
        st.markdown('<div class="sidebar-info"><h4>📄 Upload Financial Report</h4></div>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
        
        if uploaded_file and st.session_state.api_key_set:
            if st.button("📊 Process PDF"):
                with st.spinner("Extracting text from PDF..."):
                    extracted_text = st.session_state.analyzer.extract_text_from_pdf(uploaded_file)
                    if extracted_text:
                        st.success("✅ PDF processed successfully!")
                        
                        # Setup agent
                        if st.session_state.analyzer.setup_agent():
                            st.success("✅ AI Agent ready!")
                        
                        st.rerun()
        
        # Clear Chat
        if st.button("🗑️ Clear Chat History"):
            st.session_state.chat_history = []
            st.rerun()
        
        # Instructions
        st.markdown("""
        <div class="sidebar-info">
        <h4>📋 How to Use:</h4>
        <ol>
        <li>Enter your Groq API key</li>
        <li>Upload a financial PDF report</li>
        <li>Ask questions about the report</li>
        <li>Get AI-powered insights!</li>
        </ol>
        </div>
        """, unsafe_allow_html=True)
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 💬 Chat with Your Financial Report")
        
        # Display chat history
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                st.markdown(f'<div class="chat-message user-message"><strong>You:</strong> {message["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-message ai-message"><strong>AI Analyst:</strong> {message["content"]}</div>', unsafe_allow_html=True)
        
        # Chat input
        if st.session_state.api_key_set and st.session_state.analyzer.pdf_text:
            user_query = st.text_input("Ask about the financial report:", placeholder="e.g., What are the revenue trends?", key="user_input")
            
            col_send, col_examples = st.columns([1, 3])
            
            with col_send:
                if st.button("📤 Send") and user_query:
                    # Add user message to chat history
                    st.session_state.chat_history.append({"role": "user", "content": user_query})
                    
                    # Get AI response
                    with st.spinner("AI is analyzing..."):
                        try:
                            response = st.session_state.analyzer.agent.run(user_query)
                            st.session_state.chat_history.append({"role": "ai", "content": response})
                        except Exception as e:
                            error_msg = f"Error getting response: {str(e)}"
                            st.session_state.chat_history.append({"role": "ai", "content": error_msg})
                    
                    st.rerun()
            
            with col_examples:
                st.markdown("**Example questions:**")
                example_questions = [
                    "Summarize the revenue trends",
                    "What are the key financial highlights?",
                    "Analyze the profitability metrics",
                    "What are the main areas of concern?",
                    "Compare current vs previous period performance"
                ]
                
                for question in example_questions:
                    if st.button(f"💡 {question}", key=f"example_{question}"):
                        st.session_state.chat_history.append({"role": "user", "content": question})
                        
                        with st.spinner("AI is analyzing..."):
                            try:
                                response = st.session_state.analyzer.agent.run(question)
                                st.session_state.chat_history.append({"role": "ai", "content": response})
                            except Exception as e:
                                error_msg = f"Error getting response: {str(e)}"
                                st.session_state.chat_history.append({"role": "ai", "content": error_msg})
                        
                        st.rerun()
        else:
            st.info("👆 Please set up your API key and upload a PDF to start chatting!")
    
    with col2:
        st.markdown("### 📈 Quick Metrics")
        
        if st.session_state.analyzer.pdf_text:
            # Extract and display key metrics
            metrics = st.session_state.analyzer.extract_financial_metrics()
            
            if metrics:
                for metric, value in metrics.items():
                    metric_name = metric.replace('_', ' ').title()
                    if isinstance(value, (int, float)):
                        if metric in ['revenue', 'net_income', 'total_expenses']:
                            display_value = f"${value:,.0f}M" if value < 1000 else f"${value/1000:.1f}B"
                        elif metric == 'operating_margin':
                            display_value = f"{value}%"
                        elif metric == 'eps':
                            display_value = f"${value:.2f}"
                        else:
                            display_value = f"{value:,.2f}"
                    else:
                        display_value = str(value)
                    
                    st.markdown(f'''
                    <div class="metric-card">
                        <h4>{metric_name}</h4>
                        <h2>{display_value}</h2>
                    </div>
                    ''', unsafe_allow_html=True)
            else:
                st.info("📊 Upload a financial report to see key metrics")
        
        # PDF Preview
        if st.session_state.analyzer.pdf_text:
            st.markdown("### 📄 Document Preview")
            with st.expander("View extracted text"):
                st.text_area("PDF Content", st.session_state.analyzer.pdf_text[:1000] + "...", height=200, disabled=True)

if __name__ == "__main__":
    main()