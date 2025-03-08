import config
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

from random import randint
import sqlite3

bot = telebot.TeleBot(config.API_TOKEN)

def send_info(bot, message, row):
    """Отправляет информацию о фильме."""
    info = f"""
📍Title of movie: {row["title"]}
📍Year: {row["year"]}
📍Genres: {row["genre"]}
📍Rating IMDB: {row["rating"]}

🔻🔻🔻🔻🔻🔻🔻🔻🔻🔻🔻
{row["overview"]}
"""
    bot.send_photo(message.chat.id, row["img"])
    bot.send_message(message.chat.id, info, reply_markup=add_to_favorite(row["id"]))


def add_to_favorite(id):
    """Создает InlineKeyboard для добавления фильма в избранное."""
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(InlineKeyboardButton("Добавить фильм в избранное 🌟", callback_data=f'favorite_{id}'))
    return markup


def main_markup():
    """Создает основную клавиатуру с кнопкой /random и /random_genre."""
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton('/random'))
    markup.add(KeyboardButton('/random_genre'))  # Добавлена кнопка /random_genre
    markup.add(KeyboardButton('/favorites'))
    return markup


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    """Обработчик нажатий на InlineKeyboard."""
    if call.data.startswith("favorite"):
        movie_id = call.data[call.data.find("_") + 1:]
        con = sqlite3.connect("movie_database.db")
        with con:
            cur = con.cursor()
            cur.execute("SELECT * FROM favorites WHERE user_id = ? AND movie_id = ?", (call.message.chat.id, movie_id))
            if cur.fetchone() is not None:
                bot.answer_callback_query(call.id, "Этот фильм уже добавлен в избранное!", show_alert=True)
                cur.close()
                return

            cur.execute("INSERT INTO favorites (user_id, movie_id) VALUES (?, ?)", (call.message.chat.id, movie_id))
            con.commit()
            cur.close()
            bot.answer_callback_query(call.id, "Фильм добавлен в избранное! 🎉")
        print(f"Movie {movie_id} added to favorites for user {call.message.chat.id}")


@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Отправляет приветственное сообщение и основную клавиатуру."""
    bot.send_message(message.chat.id,
                     """Hello! You're welcome to the best Movie-Chat-Bot🎥! 
Here you can find 1000 movies 🔥 
Click /random to get a random movie 
Or write the title of the movie and I will try to find it! 🎬""",
                     reply_markup=main_markup())


@bot.message_handler(commands=['random'])
def random_movie(message):
    """Отправляет случайный фильм из базы данных."""
    con = sqlite3.connect("movie_database.db")
    con.row_factory = sqlite3.Row
    with con:
        cur = con.cursor()
        cur.execute("SELECT * FROM movies ORDER BY RANDOM() LIMIT 1")
        row = cur.fetchone()

        if row:
            send_info(bot, message, row)
        else:
            bot.send_message(message.chat.id, "К сожалению, в базе данных нет фильмов.")
        cur.close()


@bot.message_handler(commands=['random_genre'])
def random_genre(message):
    """Запрашивает жанр и отправляет случайный фильм из этого жанра."""
    bot.send_message(message.chat.id, "Пожалуйста, введите жанр фильма:")
    bot.register_next_step_handler(message, send_random_movie_by_genre)


def send_random_movie_by_genre(message):
    """Отправляет случайный фильм по указанному жанру."""
    genre = message.text.strip().lower()  # Получаем жанр от пользователя
    con = sqlite3.connect("movie_database.db")
    con.row_factory = sqlite3.Row
    with con:
        cur = con.cursor()
        cur.execute("SELECT * FROM movies WHERE LOWER(genre) LIKE ?", ('%' + genre + '%',))  # Ищем фильмы по жанру
        rows = cur.fetchall()

        if rows:
            random_movie = rows[randint(0, len(rows) - 1)]  # Выбираем случайный фильм из найденных
            send_info(bot, message, random_movie)
        else:
            bot.send_message(message.chat.id, "К сожалению, нет фильмов в этом жанре.")
        cur.close()


@bot.message_handler(commands=['favorites'])
def show_favorites(message):
    """Показывает список избранных фильмов пользователя."""
    con = sqlite3.connect("movie_database.db")
    con.row_factory = sqlite3.Row
    with con:
        cur = con.cursor()
        cur.execute("SELECT movies.* FROM movies INNER JOIN favorites ON movies.id = favorites.movie_id WHERE favorites.user_id = ?", (message.chat.id,))
        favorites = cur.fetchall()
        cur.close()

        if favorites:
            for row in favorites:
                send_info(bot, message, row)
        else:
            bot.send_message(message.chat.id, "У вас пока нет избранных фильмов.")


@bot.message_handler(func=lambda message: True)
def echo_message(message):
    """Ищет фильм по названию и отправляет информацию."""
    con = sqlite3.connect("movie_database.db")
    con.row_factory = sqlite3.Row
    with con:
        cur = con.cursor()
        cur.execute(f"SELECT * FROM movies WHERE LOWER(title) LIKE '%{message.text.lower()}%'")
        row = cur.fetchall()

        if row:
            if len(row) > 5:
                bot.send_message(message.chat.id, f"Найдено слишком много фильмов ({len(row)}). Пожалуйста, уточните запрос.")
            else:
                bot.send_message(message.chat.id, "Of course! I know this movie😌")
                for movie in row:
                    send_info(bot, message, movie)
        else:
            bot.send_message(message.chat.id, "I don't know this movie 😔")
        cur.close()


if __name__ == '__main__':
    con = sqlite3.connect("movie_database.db")
    with con:
        cur = con.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS movies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                img TEXT,
                title TEXT,
                year INTEGER,
                genre TEXT,
                rating REAL,
                overview TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                movie_id INTEGER NOT NULL
            )
        """)
        con.commit()
        cur.close()

    print("Бот запущен...")
    bot.infinity_polling()