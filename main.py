import sqlite3
import telebot
import pandas as pd
from time import sleep

# 定义bot管理员的telegram userid
super_admin_id = ['超级管理员的TG_ID']
admin_id = ['普通管理员1的TG_ID', '普通管理员2的TG_ID']  # 如果没有普通管理员，留空[]

# 定义bot
bot = telebot.TeleBot('你的BOT_TOKEN')

# 定义数据库
conn = sqlite3.connect('My_sub.db', check_same_thread=False)
c = conn.cursor()

# 创建表
c.execute('''CREATE TABLE IF NOT EXISTS My_sub(URL text, comment text)''')


# 接收用户输入的指令
@bot.message_handler(commands=['add', 'del', 'search', 'update', 'help'])
def handle_command(message):
    if str(message.from_user.id) in admin_id or super_admin_id:
        command = message.text.split()[0]
        if command == '/add':
            add_sub(message)
        elif command == '/del':
            delete_sub(message)
        elif command == '/search':
            search_sub(message)
        elif command == '/update':
            update_sub(message)
        elif command == '/help':
            help_sub(message)
    else:
        # bot.send_message(message.chat.id, "❌你没有操作权限，别瞎搞！")
        bot.reply_to(message, "❌你没有操作权限，别瞎搞！", timeout=30)


# 添加数据
def add_sub(message):
    url_comment = message.text.split()[1:]
    url = url_comment[0]
    comment = url_comment[1]
    c.execute("SELECT * FROM My_sub WHERE URL=?", (url,))
    if c.fetchone():
        bot.reply_to(message, "😅订阅已存在！", timeout=30)
    else:
        c.execute("INSERT INTO My_sub VALUES(?,?)", (url, comment))
        conn.commit()
        bot.reply_to(message, "✅添加成功！", timeout=30)


# 删除数据
def delete_sub(message):
    if str(message.from_user.id) in super_admin_id:
        row_num = message.text.split()[1]
        c.execute("DELETE FROM My_sub WHERE rowid=?", (row_num,))
        conn.commit()
        bot.reply_to(message, "✅删除成功！")
    else:
        bot.reply_to(message, "🔐该操作仅限超级管理员！", timeout=30)


# 查找数据
def search_sub(message):
    search_str = message.text.split()[1]
    c.execute("SELECT rowid,URL,comment FROM My_sub WHERE URL LIKE ? OR comment LIKE ?",
              ('%' + search_str + '%', '%' + search_str + '%'))
    result = c.fetchall()
    if result:
        keyboard = []
        for row in result:
            keyboard.append([telebot.types.InlineKeyboardButton(row[2], callback_data=row[0])])
        total = len(keyboard)
        keyboard.append([telebot.types.InlineKeyboardButton('❎结束搜索', callback_data='close')])
        reply_markup = telebot.types.InlineKeyboardMarkup(keyboard)
        bot.reply_to(message, '卧槽，天降订阅！！！发现了【' + str(total) + '】条订阅' + '快点击查看⏬', reply_markup=reply_markup, timeout=30)
    else:
        bot.reply_to(message, '😅没有查找到结果！', timeout=30)


# 更新数据
def update_sub(message):
    if str(message.from_user.id) in super_admin_id:
        row_num = message.text.split()[1]
        url_comment = message.text.split()[2:]
        url = url_comment[0]
        comment = url_comment[1]
        c.execute("UPDATE My_sub SET URL=?, comment=? WHERE rowid=?", (url, comment, row_num))
        conn.commit()
        bot.reply_to(message, "✅更新成功！", timeout=30)
    else:
        bot.reply_to(message, "🔐该操作仅限超级管理员！", timeout=30)


# 接收xlsx表格
@bot.message_handler(content_types=['document'])
def handle_document(message):
    if str(message.from_user.id) in super_admin_id:
        file_id = message.document.file_id
        file_info = bot.get_file(file_id)
        file = bot.download_file(file_info.file_path)
        with open('sub.xlsx', 'wb') as f:
            f.write(file)
        df = pd.read_excel('sub.xlsx')
        for i in range(len(df)):
            c.execute("SELECT * FROM My_sub WHERE URL=?", (df.iloc[i, 0],))
            if not c.fetchone():
                c.execute("INSERT INTO My_sub VALUES(?,?)", (df.iloc[i, 0], df.iloc[i, 1]))
                conn.commit()
        bot.reply_to(message, "✅导入成功！", timeout=30)
    else:
        bot.reply_to(message, "🔐该操作仅限超级管理员！", timeout=30)


# 按钮点击事件
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if str(call.from_user.id) in admin_id or super_admin_id:
        if call.data == 'close':
            bot.delete_message(call.message.chat.id, call.message.message_id)
        else:
            row_num = call.data
            c.execute("SELECT rowid,URL,comment FROM My_sub WHERE rowid=?", (row_num,))
            result = c.fetchone()
            bot.send_message(call.message.chat.id, '行号：{}\n订阅地址：{}\n说明：{}'.format(result[0], result[1], result[2]), timeout=30)
    else:
        if call.from_user.username is not None:
            now_user = f" @{call.from_user.username} "
        else:
            now_user = f" tg://user?id={call.from_user.id} "
        bot.send_message(call.message.chat.id, now_user + "你没有管理权限！天地三清，道法无敌，邪魔退让！退！退！退！👮‍♂️", timeout=30)


# 使用帮助
def help_sub(message):
    doc = '''
    使用说明：
    1. 添加数据：/add url 备注
    2. 删除数据：/del 行数
    3. 查找数据：/search 内容
    4. 修改数据：/update 行数 订阅链接 备注
    5. 导入xlsx表格：发送xlsx表格（注意文件格式！A列为订阅地址，B列为备注说明）
    '''
    bot.send_message(message.chat.id, doc, timeout=30)


if __name__ == '__main__':
    print('程序已启动')
    while True:
        try:
            bot.polling(none_stop=True)
        except RuntimeError as e:
            sleep(30)
