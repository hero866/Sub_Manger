# 表格文件导入应该用pandas的，但我没有需求，懒得改
import xlrd
import sqlite3
import telebot

# 初始化bot
bot = telebot.TeleBot('<YOUR BOT TOKEN>')

# 初始化数据库
conn = sqlite3.connect('My_sub.db', check_same_thread=False)
cursor = conn.cursor()

# 创建表
cursor.execute("create table if not exists My_sub (url text, comment text)")

# 权限检查
def auth_check(message):
    if message.from_user.id == <YOUR TG ID>:
        return True
    else:
        bot.send_message(message.chat.id, '你无操作权限，私人bot，不支持非管理员的任何操作，沙雕别瞎点！')
        return False

# 增加数据
@bot.message_handler(commands=['add'])
def add_data(message):
    if auth_check(message) == False:
        return
    data = message.text.split(' ')
    if len(data) == 3:
        url = data[1]
        comment = data[2]
        cursor.execute("select * from My_sub where url=?", (url,))
        if len(cursor.fetchall()) == 0:
            cursor.execute("insert into My_sub (url, comment) values (?, ?)", (url, comment))
            conn.commit()
            bot.send_message(message.chat.id, '添加成功！')
        else:
            bot.send_message(message.chat.id, '订阅已存在！')
    else:
        bot.send_message(message.chat.id, '输入格式有误！')

# 删除数据
@bot.message_handler(commands=['del'])
def del_data(message):
    if auth_check(message) == False:
        return
    data = message.text.split(' ')
    if len(data) == 2:
        line = data[1]
        cursor.execute("delete from My_sub where rowid=?", (line,))
        conn.commit()
        bot.send_message(message.chat.id, '删除成功！')
    else:
        bot.send_message(message.chat.id, '输入格式有误！')

# 查找数据
@bot.message_handler(commands=['search'])
def search_data(message):
    if auth_check(message) == False:
        return
    data = message.text.split(' ')
    if len(data) == 2:
        content = data[1]
        cursor.execute("select rowid, url, comment from My_sub where url like ? or comment like ?", ('%' + content + '%', '%' + content + '%'))
        results = cursor.fetchall()
        if len(results) == 0:
            bot.send_message(message.chat.id, '没有查找到结果！')
        elif len(results) == 1:
            bot.send_message(message.chat.id, '行号：' + str(results[0][0]) + '\nURL：' + results[0][1] + '\n备注：' + results[0][2])
        else:
            keyboard = telebot.types.InlineKeyboardMarkup()
            for result in results:
                keyboard.add(telebot.types.InlineKeyboardButton(text=result[2], callback_data=str(result[0])))
            bot.send_message(message.chat.id, '请选择查询结果：', reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, '输入格式有误！')

# 修改数据
@bot.message_handler(commands=['update'])
def modify_data(message):
    if auth_check(message) == False:
        return
    data = message.text.split(' ')
    if len(data) == 4:
        line = int(data[1])
        url = data[2]
        comment = data[3]
        cursor.execute("update My_sub set url=?, comment=? where rowid=?", (url, comment, line))
        conn.commit()
        bot.send_message(message.chat.id, '修改成功！')
    else:
        bot.send_message(message.chat.id, '输入格式有误！')

# 从excel导入数据
@bot.message_handler(content_types=['document'])
def import_data(message):
    if auth_check(message) == False:
        return
    if message.document.file_name.endswith('.xlsx'):
        file_id = message.document.file_id
        file_info = bot.get_file(file_id)
        file = bot.download_file(file_info.file_path)
        with open('tmp.xlsx', 'wb') as f:
            f.write(file)
        workbook = xlrd.open_workbook('tmp.xlsx')
        sheet = workbook.sheet_by_index(0)
        for row in range(1, sheet.nrows):
            url = sheet.cell(row, 0).value
            comment = sheet.cell(row, 1).value
            cursor.execute("insert into My_sub (url, comment) values (?, ?)", (url, comment))
            conn.commit()
        bot.send_message(message.chat.id, '导入成功！')
    else:
        bot.send_message(message.chat.id, '文件格式有误！')

# 打印结果
@bot.callback_query_handler(func=lambda query: True)
def print_result(query):
    line = int(query.data)
    cursor.execute("select rowid, url, comment from My_sub where rowid=?", (line,))
    result = cursor.fetchone()
    bot.send_message(query.message.chat.id, '行号：' + str(result[0]) + '\nURL：' + result[1] + '\n备注：' + result[2])

# 使用文档
@bot.message_handler(commands=['help'])
def help_doc(message):
    if auth_check(message) == False:
        return
    else:
        bot.send_message(message.chat.id, '''
使用文档：

/add url 备注：添加数据
/del 行号：删除数据
/search 内容：查找数据
/update 行号 url 备注：修改数据
/help：查看使用文档
    ''')

# 运行bot
if __name__ == '__main__':
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            time.sleep(15)
