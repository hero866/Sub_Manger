# -*- coding: utf-8 -*-
import sqlite3
import telebot
import shutil
import os
import pandas as pd
from time import sleep
from loguru import logger

# 1.22增加了日志功能，记录用户使用的指令和获取的订阅日志
logger.add('bot.log')

# 定义bot管理员的telegram userid
admin_id = ['管理员1的TG_ID', '管理员2的TG_ID', '管理员3的TG_ID']
super_admin = '超级管理员的TG_ID'

# 定义bot
bot = telebot.TeleBot('你的BOT_TOKEN')

# 定义数据库
conn = sqlite3.connect('My_sub.db', check_same_thread=False)
c = conn.cursor()

# 创建表
c.execute('''CREATE TABLE IF NOT EXISTS My_sub(URL text, comment text)''')


# 接收用户输入的指令
@bot.message_handler(commands=['add', 'del', 'search', 'update'])
def handle_command(message):
    if str(message.from_user.id) in admin_id:
        command = message.text.split()[0]
        logger.debug(f"用户{message.from_user.id}使用了{command}功能")
        if command == '/add':
            add_sub(message)
        elif command == '/del':
            delete_sub(message)
        elif command == '/search':
            search_sub(message)
        elif command == '/update':
            update_sub(message)
    else:
        bot.reply_to(message, "❌你没有操作权限，别瞎搞！")


# 添加数据
def add_sub(message):
    try:
        url_comment = message.text.split()[1:]
        url = url_comment[0]
        comment = url_comment[1]
        c.execute("SELECT * FROM My_sub WHERE URL=?", (url,))
        if c.fetchone():
            bot.reply_to(message, "😅订阅已存在！")
        else:
            c.execute("INSERT INTO My_sub VALUES(?,?)", (url, comment))
            conn.commit()
            bot.reply_to(message, "✅添加成功！")
    except Exception as t:
        print(t)
        bot.send_message(message.chat.id, "😵😵输入格式有误，请检查后重新输入")


# 删除数据
def delete_sub(message):
    try:
        row_num = message.text.split()[1]
        c.execute("DELETE FROM My_sub WHERE rowid=?", (row_num,))
        conn.commit()
        c.execute("VACUUM")
        conn.commit()
        bot.reply_to(message, "✅删除成功！")
    except Exception as t:
        print(t)
        bot.send_message(message.chat.id, "😵😵输入格式有误，请检查后重新输入")


# 查找数据
items_per_page = 10
result = None
callbacks = {}


def search_sub(message):
    global items_per_page, total, result, current_page
    try:
        search_str = message.text.split()[1]
        c.execute("SELECT rowid,URL,comment FROM My_sub WHERE URL LIKE ? OR comment LIKE ?",
                  ('%' + search_str + '%', '%' + search_str + '%'))
        result = c.fetchall()
        if result:
            pages = [result[i:i + items_per_page] for i in range(0, len(result), items_per_page)]
            total = len(pages)
            current_page = 1
            current_items = pages[current_page - 1]
            keyboard = []
            for item in current_items:
                button = telebot.types.InlineKeyboardButton(item[2], callback_data=item[0])
                keyboard.append([button])
            if total > 1:
                page_info = f'第 {current_page}/{total} 页'
                prev_button = telebot.types.InlineKeyboardButton('◀️上一页', callback_data='prev')
                next_button = telebot.types.InlineKeyboardButton('下一页▶️', callback_data='next')
                page_button = telebot.types.InlineKeyboardButton(page_info, callback_data='page_info')
                page_buttons = [prev_button, page_button, next_button]
                keyboard.append(page_buttons)
            keyboard.append([telebot.types.InlineKeyboardButton('❎结束搜索', callback_data='close')])
            reply_markup = telebot.types.InlineKeyboardMarkup(keyboard)
            sent_message = bot.reply_to(message, f'卧槽，天降订阅🎁发现了{str(len(result))}个目标，快点击查看⏬', reply_markup=reply_markup)
            global sent_message_id
            sent_message_id = sent_message.message_id
            user_id = message.from_user.id
            callbacks[user_id] = {'total': total, 'current_page': current_page, 'result': result, 'sent_message_id': sent_message_id}
        else:
            bot.reply_to(message, '😅没有查找到结果！')
    except Exception as t:
        print(t)
        bot.send_message(message.chat.id, "😵😵您输入的内容有误，请检查后重新输入")


def update_buttons(callback_query, user_id):
    global callbacks
    callback_data = callback_query.data
    message = callback_query.message
    message_id = message.message_id
    current_page = callbacks[user_id]['current_page']
    total = callbacks[user_id]['total']
    result = callbacks[user_id]['result']
    if callback_data == 'prev' and current_page > 1:
        current_page -= 1
    elif callback_data == 'next' and current_page < total:
        current_page += 1
    pages = [result[i:i + items_per_page] for i in range(0, len(result), items_per_page)]
    current_items = pages[current_page - 1]
    bot.edit_message_reply_markup(chat_id=message.chat.id, message_id=message_id, reply_markup=None)
    keyboard = []
    for item in current_items:
        button = telebot.types.InlineKeyboardButton(item[2], callback_data=item[0])
        keyboard.append([button])
    if total > 1:
        page_info = f'第 {current_page}/{total} 页'
        prev_button = telebot.types.InlineKeyboardButton('◀️上一页', callback_data='prev')
        next_button = telebot.types.InlineKeyboardButton('下一页▶️', callback_data='next')
        page_button = telebot.types.InlineKeyboardButton(page_info, callback_data='page_info')
        page_buttons = [prev_button, page_button, next_button]
        keyboard.append(page_buttons)
    keyboard.append([telebot.types.InlineKeyboardButton('❎结束搜索', callback_data='close')])
    reply_markup = telebot.types.InlineKeyboardMarkup(keyboard)
    bot.edit_message_reply_markup(chat_id=message.chat.id, message_id=message_id, reply_markup=reply_markup)
    callbacks[user_id]['current_page'] = current_page


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    global sent_message_id, current_page, callbacks
    user_id = call.from_user.id
    if str(user_id) in admin_id:
        if call.data == 'close':
            delete_result = bot.delete_message(call.message.chat.id, call.message.message_id)
            if delete_result is None:
                sent_message_id = None
        elif call.data == 'prev' or call.data == 'next':
            if user_id in callbacks:
                update_buttons(call, user_id)
        elif call.data == 'page_info':
            pass
        else:
            try:
                row_num = call.data
                c.execute("SELECT rowid,URL,comment FROM My_sub WHERE rowid=?", (row_num,))
                result = c.fetchone()
                bot.send_message(call.message.chat.id, '*行号：*`{}`\n*订阅*：{}\n\n*说明*： `{}`'.format(result[0], result[1].replace("_", "\_"), result[2]), parse_mode='Markdown')
                logger.debug(f"用户{call.from_user.id}从BOT获取了{result}")
            except TypeError as t:
                bot.send_message(call.message.chat.id, f"😵😵发生错误\n{t}")
    else:
        if call.from_user.username is not None:
            now_user = f" @{call.from_user.username} "
        else:
            now_user = f"<a href=\"tg://user?id={call.from_user.id}\">{call.from_user.id}</a>"
        bot.send_message(call.message.chat.id, f"{now_user}天地三清，道法无敌，邪魔退让！退！退！退！👮‍♂️", parse_mode='HTML')


# 更新数据
def update_sub(message):
    try:
        row_num = message.text.split()[1]
        url_comment = message.text.split()[2:]
        url = url_comment[0]
        comment = url_comment[1]
        c.execute("UPDATE My_sub SET URL=?, comment=? WHERE rowid=?", (url, comment, row_num))
        conn.commit()
        bot.reply_to(message, "✅更新成功！")
    except Exception as t:
        print(t)
        bot.send_message(message.chat.id, "😵😵输入格式有误，请检查后重新输入")


# 接收xlsx表格
@bot.message_handler(content_types=['document'], chat_types=['private'])
def handle_document(message):
    if str(message.from_user.id) in admin_id:
        file_id = message.document.file_id
        file_info = bot.get_file(file_id)
        try:
            file = bot.download_file(file_info.file_path)
            with open('sub.xlsx', 'wb') as f:
                f.write(file)
            df = pd.read_excel('sub.xlsx')
            for i in range(len(df)):
                c.execute("SELECT * FROM My_sub WHERE URL=?", (df.iloc[i, 0],))
                if not c.fetchone():
                    c.execute("INSERT INTO My_sub VALUES(?,?)", (df.iloc[i, 0], df.iloc[i, 1]))
                    conn.commit()
            bot.reply_to(message, "✅导入成功！")
        except Exception as t:
            print(t)
            bot.send_message(message.chat.id, "😵😵导入的文件格式错误，请检查文件后缀是否为xlsx后重新导入")
    else:
        bot.reply_to(message, "😡😡😡你不是管理员，禁止操作！")


# 使用帮助
@bot.message_handler(commands=['help'], chat_types=['private'])
def help_sub(message):
    doc = '''
    时间有限暂未做太多异常处理，请遵循使用说明的格式规则，否则程序可能出错，如果出现异常情况，联系 @KKAA2222 处理
🌈使用说明：
    1. 添加数据：/add url 备注
    2. 删除数据：/del 行数
    3. 查找数据：/search 内容
    4. 修改数据：/update 行数 订阅链接 备注
    5. 导入xlsx表格：发送xlsx表格（注意文件格式！A列为订阅地址，B列为对应的备注）
    '''
    bot.send_message(message.chat.id, doc)


@bot.message_handler(commands=['start'], chat_types=['private'])
def start(message):
    if message.from_user.username is not None:
        now_user = f" @{message.from_user.username} "
    else:
        now_user = f"<a href=\"tg://user?id={message.from_user.id}\">{message.from_user.id}</a>"
    if str(message.from_user.id) in admin_id:
        bot.send_message(message.chat.id, f"{now_user}同志您好，很高兴为您服务！")
    else:
        bot.send_message(message.chat.id, f"🈲{now_user}同志，您已闯入军事重地，请速速离开！")


# 2.19增加了数据库备份功能
@bot.message_handler(commands=['backup'], chat_types=['private'])
def backup_database(message):
    if str(message.from_user.id) == super_admin:
        try:
            backup_dir = 'backup'
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            backup_file = os.path.join(backup_dir, 'My_sub_backup.db')
            shutil.copyfile('My_sub.db', backup_file)
            with open(backup_file, 'rb') as file:
                bot.send_document(message.chat.id, file)
            for file in os.listdir(backup_dir):
                if file != 'My_sub_backup.db':
                    os.remove(os.path.join(backup_dir, file))
            bot.reply_to(message, '✅数据库备份完成')
            logger.debug(f"用户{message.from_user.id}备份了数据库")
        except Exception as t:
            bot.reply_to(message, f'⚠️出现问题了，报错内容为: {t}')
    else:
        bot.reply_to(message, '🈲仅限数据库的主人查看')


@bot.message_handler(commands=['log'], chat_types=['private'])
def backup_database(message):
    if str(message.from_user.id) == super_admin:
        try:
            with open('./bot.log', 'rb') as f:
                bot.send_document(message.chat.id, f)
                f.close()
        except Exception as t:
            bot.reply_to(message, f"⚠️出错了: {t}")
    else:
        bot.reply_to(message, '🈲仅限数据库的主人查看')


if __name__ == '__main__':
    print('=====程序已启动=====')
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            print(e)
            sleep(30)
