# Use an official Python image as a base
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the current directory (telegram_bot) contents into the container at /app
COPY . /app

# Copy the requirements.txt file from the root project folder to the container
COPY ./requirements.txt /app/

# Install dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose port (if the bot is listening to some API or service)
EXPOSE 8080

# Command to run the Telegram bot
CMD ["python", "bot.py"]
