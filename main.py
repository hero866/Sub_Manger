import sqlite3
import telebot
import pandas as pd

#定义bot管理员的telegram userid
admin_id = 你的TG_ID

#定义bot
bot = telebot.TeleBot('你的BOT_TOKEN')

#定义数据库
conn = sqlite3.connect('My_sub.db', check_same_thread=False)
c = conn.cursor()

#创建表
c.execute('''CREATE TABLE IF NOT EXISTS My_sub(URL text, comment text)''')

#接收用户输入的指令
@bot.message_handler(commands=['add', 'delete', 'search', 'update', 'help'])
def handle_command(message):
    if message.from_user.id == admin_id:
        command = message.text.split()[0]
        if command == '/add':
            add_sub(message)
        elif command == '/delete':
            delete_sub(message)
        elif command == '/search':
            search_sub(message)
        elif command == '/update':
            update_sub(message)
        elif command == '/help':
            help_sub(message)
    else:
        bot.send_message(message.chat.id, "你没有权限操作，请勿浪费时间！")

#添加数据
def add_sub(message):
    url_comment = message.text.split()[1:]
    url = url_comment[0]
    comment = url_comment[1]
    c.execute("SELECT * FROM My_sub WHERE URL=?", (url,))
    if c.fetchone():
        bot.send_message(message.chat.id, "此订阅已存在！")
    else:
        c.execute("INSERT INTO My_sub VALUES(?,?)", (url,comment))
        conn.commit()
        bot.send_message(message.chat.id, "添加成功！")

#删除数据
def delete_sub(message):
    row_num = message.text.split()[1]
    c.execute("DELETE FROM My_sub WHERE rowid=?", (row_num,))
    conn.commit()
    bot.send_message(message.chat.id, "删除成功！")

#查找数据
def search_sub(message):
    search_str = message.text.split()[1]
    c.execute("SELECT rowid,URL,comment FROM My_sub WHERE URL LIKE ? OR comment LIKE ?", ('%'+search_str+'%','%'+search_str+'%'))
    result = c.fetchall()
    if result:
        if len(result) == 1:
            bot.send_message(message.chat.id, '行号：{}\nURL：{}\ncomment：{}'.format(result[0][0], result[0][1], result[0][2]))
        else:
            keyboard = []
            for row in result:
                keyboard.append([telebot.types.InlineKeyboardButton(row[2], callback_data=row[0])])
            reply_markup = telebot.types.InlineKeyboardMarkup(keyboard)
            bot.send_message(message.chat.id, '查找到以下结果，请点击查看：', reply_markup=reply_markup)
    else:
        bot.send_message(message.chat.id, '没有查找到结果！')

#更新数据
def update_sub(message):
    row_num = message.text.split()[1]
    url_comment = message.text.split()[2:]
    url = url_comment[0]
    comment = url_comment[1]
    c.execute("UPDATE My_sub SET URL=?, comment=? WHERE rowid=?", (url,comment,row_num))
    conn.commit()
    bot.send_message(message.chat.id, "更新成功！")

#接收xlsx表格
@bot.message_handler(content_types=['document'])
def handle_document(message):
    file_id = message.document.file_id
    file_info = bot.get_file(file_id)
    file = bot.download_file(file_info.file_path)
    with open('sub.xlsx', 'wb') as f:
        f.write(file)
    df = pd.read_excel('sub.xlsx')
    for i in range(len(df)):
        c.execute("SELECT * FROM My_sub WHERE URL=?", (df.iloc[i,0],))
        if not c.fetchone():
            c.execute("INSERT INTO My_sub VALUES(?,?)", (df.iloc[i,0],df.iloc[i,1]))
            conn.commit()
    bot.send_message(message.chat.id, "导入成功！")

#按钮点击事件
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.from_user.id == admin_id:
        row_num = call.data
        c.execute("SELECT rowid,URL,comment FROM My_sub WHERE rowid=?", (row_num,))
        result = c.fetchone()
        bot.send_message(call.message.chat.id, '行号：{}\nURL：{}\ncomment：{}'.format(result[0], result[1], result[2]))
    else:
        bot.send_message(call.message.chat.id, "你没有操作权限，沙雕别瞎点！💩💩💩")

#使用帮助
def help_sub(message):
    doc = '''
    使用说明：
    1. 添加数据：/add url 备注
    2. 删除数据：/delete 行数
    3. 查找数据：/search 内容
    4. 修改数据：/update 行数 订阅链接 备注
    5. 导入xlsx表格：发送xlsx表格(订阅备注的数字只能是整数！！！)
    '''
    bot.send_message(message.chat.id, doc)

bot.polling()
