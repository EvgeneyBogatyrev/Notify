import os
import json
import config
import logging
import asyncio
from datetime import datetime

from aiogram import Bot, Dispatcher, executor, types


# log level
logging.basicConfig(level=logging.INFO)

# bot init
bot = Bot(token=config.TOKEN)
dp = Dispatcher(bot)


class Mode:
    NORMAL = 0
    GET_INPUT = 1
    EDIT_TASKS = 2
    CHANGE = 3

mode = Mode.NORMAL
last_call = datetime.now()

OFFSET = 30 * 60

def load_offset():
    if not os.path.isfile(config.stats_file):
        offset = 30 * 60
        data = {"offset" : offset}
        with open(config.stats_file, "w") as f:
            json.dump(data, f)
        return offset
    with open(config.stats_file, "r") as f:
        data = json.load(f)
    return data["offset"]


def change_offset(new_offset):
    with open(config.stats_file, "r") as f:
        data = json.load(f)
    data["offset"] = new_offset
    with open(config.stats_file, "w") as f:
        json.dump(data, f)


def init_database():
    data = {}
    with open(config.PATH, "w") as f:
        json.dump(data, f)


def save_database(data):
    with open(config.PATH, "w") as f:
        json.dump(data, f)


def read_database():
    with open(config.PATH, "r") as f:
        data = json.load(f)
    return data


def set_task():
    global mode
    mode = Mode.GET_INPUT
    return "Enter the task name:"


def add_task(task):
    if ',' in task:
        words = list(task.split(","))
        task_name = words[0]
        priority = words[1]
    else:
        task_name = task
        priority = "1"

    data = read_database()
    length = len(data.keys())

    for key in data.keys():
        if data[key]["name"] == task_name:
            return "Task is already set"

    data[str(length)] = {}
    data[str(length)]["name"] = task_name
    data[str(length)]["priority"] = priority
    save_database(data)
    return "Task set succesfully"


def get_tasks(numbers=False):
    data = read_database()
    line = "TASKS:\n"
    prior_last = -1
    for idx in sorted(data.keys(), key=lambda x: data[x]["priority"], reverse=True):
        priority = data[idx]["priority"]
        if priority != prior_last:
            line += ("----------------\n")
            prior_last = priority
        if numbers:
            line += f"{int(idx) + 1}) {data[idx]['name']}\n"
        else:
            line += f"* {data[idx]['name']}\n"
    return line


def delete_tasks():
    global mode
    line = "Enter the number of task to delete:\n"
    line += get_tasks(numbers=True)
    mode = Mode.EDIT_TASKS
    return line


def delete_task(number):
    numb = int(number)
    if numb == 0:
        return "Enter a valid number or q to quit"

    data = read_database()
    keys = data.keys()

    if len(keys) < numb:
        return "Enter a valid number or q to quit"

    del data[str(numb - 1)]

    new_data = {}
    for i, key in enumerate(sorted(data.keys(), key=lambda x: int(x))):
        new_data[str(i)] = data[key]

    save_database(new_data)

    return "Success!\n" + get_tasks()


def change_priority():
    global mode
    mode = Mode.CHANGE
    line = "Enter the task name and new priority:\n"
    line += get_tasks(numbers=True)
    return line


def edit_priority(text):
    if " " not in text:
        return "Enter a valid combination: <number> <new priority> or q to quit"

    words = list(text.split(" "))
    number = int(words[0])
    prior = words[1]

    data = read_database()
    keys = data.keys()

    if number > len(keys):
        return "Enter a valid number or q to quit"

    data[str(number - 1)]["priority"] = prior
    save_database(data)

    return "Success!\n" + get_tasks()


def process_message(text):
    global mode

    if text == 'q' and mode != Mode.NORMAL:
        mode = Mode.NORMAL
        return "Canceled"

    if mode == Mode.GET_INPUT:
        mode = Mode.NORMAL
        return add_task(text)
    if mode == Mode.EDIT_TASKS:
        for c in text:
            if c not in "0123456789":
                return get_tasks(numbers=True) + "\nEnter a number or q to quit"
        responce = delete_task(text)
        if responce.startswith("Enter"):
            return get_tasks(numbers=True) + "\n" + responce
        mode = Mode.NORMAL
        return responce
    if mode == Mode.CHANGE:
        for c in text:
            if c not in " 0123456789":
                return get_tasks(numbers=True) + "\nEnter a number or q to quit"
        responce = edit_priority(text)
        if responce.startswith("Enter"):
            return get_tasks(numbers=True) + "\n" + responce
        mode = Mode.NORMAL
        return responce

    if text in ["/tasks", "/ls"]:
        return get_tasks()
    if text in ["/set_task", "/add"]:
        return set_task()
    if text in ["/delete", "/del"]:
        return delete_tasks()
    if text == "/clear":
        return clear_tasks()
    if text.startswith("/offset"):
        return set_offset(text)
    if text in ["/change_priority", "/chp"]:
        return change_priority()
    if text == "/id":
        return f"Your id is {config.MY_ID}"
    return text


def clear_tasks():
    data = {}
    save_database(data)
    return "All tasks erased"

def set_offset(text):
    text = text[len("/offset"):]
    text = text.strip()
    offset = 60 * int(text)
    change_offset(offset)
    return "Done!"


# echo
@dp.message_handler()
async def echo(message: types.Message):
    await message.answer(process_message(message.text))


async def scheduled():
    global last_call
    await asyncio.sleep(5)
    await bot.send_message(config.MY_ID, "Remember your tasks?\n" + get_tasks())
    while True:
        wait_for = OFFSET#load_offset()
        if wait_for == 0:
            continue
        await asyncio.sleep(wait_for)

        now = datetime.now()
        if int((now - last_call).total_seconds()) > OFFSET:
            last_call = now
            await bot.send_message(config.MY_ID, "Remember your tasks?\n" + get_tasks())

async def hello():
    await bot.send_message(config.MY_ID, "NotifyBot started!")

# run long-polling
if __name__ == "__main__":
    if not os.path.isfile(config.PATH):
        init_database()

    loop = asyncio.get_event_loop()
    loop.create_task(hello())
    loop.create_task(scheduled())
    executor.start_polling(dp, skip_updates=True)
