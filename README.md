# RAGRetrival2

Deployed Demo: https://askus-ai.duckdns.org/ 

python3.11 -m venv venv
pip install --upgrade pip
pip install -r requirements.txt


commands : 
tree -I "venv|__pycache__|.git|node_modules|uploads|vectorstore|DATA"

uvicorn app.main:app --reload
