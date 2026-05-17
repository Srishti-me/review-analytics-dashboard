# AI Review Analytics Dashboard

An AI-powered review analytics dashboard built with Python and Streamlit. This application processes CSV files of user reviews, using local NLP for clustering and batching to minimize external LLM API costs. It features intelligent issue categorization, topic extraction, and data visualization within a modern, sleek interface.

## Features
- **CSV Data Processing**: Upload and process review data seamlessly.
- **Local NLP Clustering**: Groups similar reviews locally to optimize LLM API usage.
- **AI-Powered Insights**: Integrates with Grok API (and optionally OpenAI) for intelligent categorization and sentiment analysis.
- **Interactive Dashboards**: Premium data visualization built entirely with Streamlit.

## Setup and Installation

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd <repository-folder>
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv .venv
   # On Windows
   .venv\Scripts\activate
   # On macOS/Linux
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r review_analytics/requirements.txt
   ```

4. **Environment Variables**:
   Create a `.env` file in the root directory and add your API keys:
   ```env
   GROK_API_KEY=your_grok_api_key_here
   # OPENAI_API_KEY=your_openai_api_key_here
   ```

5. **Run the Application**:
   ```bash
   cd review_analytics
   streamlit run app.py
   ```

## Project Structure
- `review_analytics/app.py`: Main Streamlit application entry point.
- `review_analytics/pages/`: Additional Streamlit pages.
- `review_analytics/utils/`: Utility functions and LLM pipeline integrations.
- `review_analytics/requirements.txt`: Python dependencies.

## License
MIT
