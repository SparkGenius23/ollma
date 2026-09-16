
source venv/bin/activate
pip install -r requirements.txt
deactivate

sudo systemctl restart fastapi.service