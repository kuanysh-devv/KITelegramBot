### COMMANDS TO LAUNCH API
## NEED TO CHANGE IP, PORT

# AT LOCALHOST

uvicorn app.main:app --host localhost --port 8001

# TO LAUNCH TELEGRAM BOT

python .\telegram_bot\bot.py

# IN DOCKER

docker build -t fastapi-chatgpt .

docker run -d --name fastapi-chatgpt --env-file .env -p 8000:8000 fastapi-chatgpt

