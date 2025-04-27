# DIA Chatbot

A knowledge-driven chatbot backed by vector search that allows users to query information from ingested websites.

## Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/Ivyzie/dia-chatbot
```

### 2. Start Weaviate
```bash
cd weaviate/
docker-compose up -d
```
Ensure Docker is running and port 8080 is available.

### 3. Create & activate a Python virtual environment
```bash
cd ..
python3 -m venv venv
source venv/bin/activate   # macOS/Linux
venv\Scripts\activate      # Windows PowerShell
```

### 4. Install Python dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Download the Zephyr model
```bash
# Create models directory if it doesn't exist
mkdir -p src/models

# Download the Zephyr model
wget -O src/models/zephyr-7b-beta.Q4_K_M.gguf https://huggingface.co/TheBloke/zephyr-7B-beta-GGUF/resolve/main/zephyr-7b-beta.Q4_K_M.gguf
```
If wget is not installed, you can download the model manually from [HuggingFace](https://huggingface.co/TheBloke/zephyr-7B-beta-GGUF/resolve/main/zephyr-7b-beta.Q4_K_M.gguf) and place it in the `src/models` directory.

### 6. Ingest your knowledge base
```bash
python kb_ingest.py
```
When prompted, paste one or more URLs (e.g., https://www.carlist.my/faq).
Alternatively, pre-populate `src/input/links.txt` with each URL on its own line.

### 7. Launch the Flask backend
```bash
python src/app.py
```

## Running the Chatbot

Open your browser and visit:
```
http://localhost:5000/
```

Type a message (e.g., "What's the price of the Bezza 1.3 Premium?") and press Enter or click Send.