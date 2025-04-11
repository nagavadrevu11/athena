# AI Income Service API

This service analyzes borrower income documents using AI to assist mortgage underwriters in calculating qualifying income.

## Setup

### Prerequisites
- Python 3.8+
- OpenAI API key

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/ai-income-service-api.git
cd ai-income-service-api
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:

For local development, create a `.env` file in the root directory:
```
OPENAI_API_KEY=your_openai_key_here
```

Or set it in your shell:
```bash
export OPENAI_API_KEY=your_openai_key_here
```

### Streamlit Deployment

For Streamlit deployment, set up secrets:

1. Copy the example secrets template:
```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

2. Edit `.streamlit/secrets.toml` and add your API keys:
```toml
[openai]
api_key = "your_openai_api_key_here"
```

## Usage

### Running the Streamlit Web App

```bash
streamlit run scripts/streamlit_app.py
```

### Analyzing a Borrower's Income

1. Place borrower documents in a subfolder under the `data` directory:
```
data/
  borrower_name/
    metadata.json
    paystub.pdf
```

2. Format the metadata.json file:
```json
{
  "name": "John Doe",
  "employer": "ACME Inc.",
  "job_title": "Software Engineer",
  "base_salary": 120000,
  "start_date": "2020-01-15",
  "income_type": "Salaried"
}
```

3. Use the web app to analyze the income documents.

## Security Note

This project uses API keys which should never be committed to the repository. Always use environment variables or secure secret management for sensitive credentials. 