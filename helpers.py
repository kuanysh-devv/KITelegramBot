from __future__ import annotations

import asyncio
import json
from datetime import datetime

from aiogram.enums import ChatAction
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv
from openai import OpenAI
import time
import os

load_dotenv()

# Store thread IDs for each user
user_threads = {}
user_selected_assistants = {}

# Initialize OpenAI client
client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY'),
    project=os.getenv('PROJECT_ID')
)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ASSISTANTS_FILE = 'assistants.json'


# Function to log the interaction
def log_interaction(username, question, answer):
    # Prepare the log entry
    log_entry = {
        "username": username,
        "question": question,
        "answer": answer,
        "datetime": datetime.now().isoformat()  # Get current datetime in ISO 8601 format
    }

    # Read existing logs from the file
    try:
        with open('logs.json', 'r', encoding='utf-8') as file:
            logs = json.load(file)  # Load existing logs
    except (FileNotFoundError, json.JSONDecodeError):
        logs = []  # If file doesn't exist or is empty, initialize an empty list

    # Append the new log entry
    logs.append(log_entry)

    # Write the updated logs back to the file
    with open('logs.json', 'w', encoding='utf-8') as file:
        json.dump(logs, file, indent=4, ensure_ascii=False)  # Write with pretty formattin


# Load assistants data
def load_assistants():
    with open(ASSISTANTS_FILE, 'r', encoding='utf-8') as file:
        return json.load(file)


# Load assistants globally
ASSISTANTS = load_assistants()


async def send_assistant_menu(event: Message | CallbackQuery):
    """
    Sends a menu for choosing an assistant to the user.
    """
    # Build the inline keyboard dynamically based on ASSISTANTS
    keyboard = InlineKeyboardBuilder()
    for assistant in ASSISTANTS:
        keyboard.button(text=assistant["name"], callback_data=assistant["id"])
    keyboard.adjust(1)  # Arrange buttons in a single column

    if isinstance(event, CallbackQuery):
        # If triggered by a callback query, edit the message
        await event.message.edit_text(
            "Выберите ассистента для начала работы:",
            reply_markup=keyboard.as_markup()
        )
    elif isinstance(event, Message):
        # If triggered by a new message, send a new one
        await event.answer(
            "Выберите ассистента для начала работы:",
            reply_markup=keyboard.as_markup()
        )


async def ask_assistant_bot(question: str, user_id: int, username: str, message: Message):
    """
    Processes the user's question by sending it to the assistant in their dedicated thread.
    """
    selected_assistant_id = user_selected_assistants.get(user_id)
    if not selected_assistant_id:
        await send_assistant_menu(message)
        return

    # Get or create the user's thread
    if user_id not in user_threads:
        thread = client.beta.threads.create()  # Create new thread if not exists
        user_threads[user_id] = thread.id
    else:
        thread = client.beta.threads.retrieve(user_threads[user_id])  # Retrieve the existing thread

    # Create the initial user message
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=question
    )
    print(question, username)
    # Check if there are any active runs in the thread and wait for completion if necessary
    while True:
        runs = client.beta.threads.runs.list(thread_id=thread.id)
        active_run = next((run for run in runs.data if run.status == "active"), None)

        if active_run:
            print("here is active run")
            await message.answer_chat_action(action=ChatAction.TYPING)
            time.sleep(2)
        else:
            break

    # Now we can safely create and start the new run
    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread.id,
        assistant_id=selected_assistant_id,
        instructions="You are an AI assistant for 'KAZAKH INVEST', "
                     "an investment company in Kazakhstan. Answer on client's language."
                     "Your role is to help users find answers "
                     "strictly from the uploaded documents stored in your vector database. "
                     "You must not search the internet or generate answers—all responses must come "
                     "directly from the uploaded text data. Answer only related questions about "
                     "investments from documents. Any other irrelevant questions restricted."
                     "Data Source: Use only the uploaded documents. Do not generate data or search the internet."
                     "Language: Respond in the language of the user's query."
                     "Unknown Answers: If you cannot find the answer in the uploaded documents, respond with:"
                     "К сожалению я не знаю ответа на Ваш вопрос, но Вы можете обратиться на электронную почту "
                     "info@invest.gov.kz, по номеру телефона +7 7172 620 620 или направить запрос на нашем сайте "
                     "https://invest.gov.kz/ru/cabinet/send-request/ и сотрудники АО НК 'KAZAKH INVEST' "
                     "обязательно ответят"
                     "Annotations: When providing answers, include clear annotations or references to the "
                     "document source if applicable."
                     "Data Format: You are optimized to work with text-only data."
                     "Your task is to provide relevant, accurate information based solely on the uploaded documents, "
                     "ensuring multilingual support and avoiding external sources. Answer only to relevant "
                     "questions from database."
    )

    retries = 0
    max_retries = 3
    while retries < max_retries:
        try:
            if run.status == 'completed':
                messages_page = client.beta.threads.messages.list(thread_id=thread.id)
                assistant_responses = [
                    message for message in messages_page.data if message.role == "assistant"
                ]

                if assistant_responses:
                    last_response = assistant_responses[0]
                    message_content = last_response.content[0].text
                    annotations = message_content.annotations
                    citations = {}

                    # Group annotations by their text and track their indices
                    for index, annotation in enumerate(annotations):
                        annotation_text = annotation.text
                        print(annotation_text)
                        # Group indices of repeated annotations
                        if annotation_text not in citations:
                            citations[annotation_text] = []
                        citations[annotation_text].append(index + 1)

                        # Replace annotation text with placeholder for later citation
                        message_content.value = message_content.value.replace(annotation_text, f' [{index + 1}]')

                    print(message_content.value)
                    # Prepare citation format for repeated annotations
                    formatted_citations = []
                    for annotation_text, indices in citations.items():
                        indices_str = ''.join([f'[{i}]' for i in indices])
                        formatted_citations.append(f'{indices_str} {annotation_text}')
                    print(formatted_citations)
                    # Combine message content with citations
                    message_with_citations = message_content.value + '\n\n' + '\n'.join(formatted_citations)
                    log_interaction(username, question, message_with_citations)
                    yield message_with_citations
                    return  # Exit the function after successful execution
            else:
                raise Exception("Произошла ошибка. Попробуйте еще раз.")
        except Exception as e:
            retries += 1
            print(f"Retry {retries}/{max_retries} due to error: {e}")
            if retries < max_retries:
                await asyncio.sleep(2 ** retries)  # Exponential backoff
            else:
                raise Exception("Maximum retry attempts reached. Please try again later.") from e


def process_annotations(annotations_list):
    """
    Process annotations to group them by text and prepare citations.
    Returns a tuple of the updated message content and formatted citations.
    """
    citations = {}
    message_content_value = annotations_list[0].message.content.value

    for index, annotation in enumerate(annotations_list):
        annotation_text = annotation.text
        if annotation_text not in citations:
            citations[annotation_text] = []
        citations[annotation_text].append(index + 1)

        # Replace annotation text with placeholder for later citation
        message_content_value = message_content_value.replace(annotation_text, f' [{index + 1}]')

    # Prepare citation format for repeated annotations
    formatted_citations = [
        f"{''.join([f'[{i}]' for i in indices])} {text}" for text, indices in citations.items()
    ]

    return message_content_value, formatted_citations