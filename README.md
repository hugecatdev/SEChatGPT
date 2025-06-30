# SMS Explorer ChatGPT

Web application for SMS Explorer browser that provides ChatGPT access through SMS interface.

## Requirements

- Python 3.10+
- SMS Explorer browser
- OpenAI API key

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd SEChatGPT
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create environment file:

```bash
echo "OPENAI_API_KEY=your_openai_api_key_here" > .env
```

4. Create templates directory:

```bash
mkdir templates
```

## Usage

1. Run the application:

```bash
python run.py
```

2. Open in SMS Explorer browser:

```
http://your-server:8796
```

## Project Structure

```
├── main.py              # Main application
├── run.py              # Application runner
├── chat_history.db      # SQLite database
├── templates/           # HTML templates
│   └── chat.html
├── requirements.txt     # Python dependencies
├── .env                # Environment variables
└── README.md           # Documentation
```

## API Endpoints

- `GET /` - Chat page
- `POST /send` - Send message
- `POST /clear` - Clear chat history