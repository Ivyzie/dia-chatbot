# dia-chatbot

Setup & Installation

1. Clone the repository

git clone https://github.com/Ivyzie/dia-chatbot

2. Start Weaviate

cd weaviate/
docker-compose up -d

Ensure Docker is running and port 8080 is available.

3. Create & activate a Python virtual environment

cd ..
python3 -m venv venv
source venv/bin/activate   # macOS/Linux
venv\Scripts\activate      # Windows PowerShell

4. Install Python dependencies

pip install --upgrade pip
pip install -r requirements.txt

5. Ingest your knowledge base

python crawl_and_ingest.py

When prompted, paste one or more URLs (e.g., https://www.carlist.my/faq).Alternatively, pre-populate input/links.txt with each URL on its own line.

6. Launch the Flask backend

python src/app.py

Running the Chatbot

Open your browser and visit:

http://localhost:5000/

Type a message (e.g., “What’s the price of the Bezza 1.3 Premium?”) and press Enter or click Send.