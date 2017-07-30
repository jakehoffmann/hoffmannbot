import psycopg2
import time


# Have to pass the decorator some by-reference values to variables that maintain the database connection and identify
#  what url we're connecting to
def maintain_db_connection(conn, c, url):
    """
    A decorator that maintains the database connection of database related functions.
    :param conn: database connection
    :param c: cursor
    :param url: database url
    :return:
    """
    def inner_decorator(func):
        def wrapper(*args):
            try:
                func(*args)
            except psycopg2.Error as e:
                error_time = time.time()
                n = 1
                while True:
                    if time.time() - error_time > 2**n:
                        try:
                            print('Database Error:', e)
                            conn = psycopg2.connect(
                                database=url.path[1:],
                                user=url.username,
                                password=url.password,
                                host=url.hostname,
                                port=url.port
                            )
                            c = conn.cursor()
                            break
                        except:
                            print('Reconnect failed', n, 'times')
                            n += 1
                            pass
                func(*args)
        return wrapper
    return inner_decorator


# def maintain_db_connection2(func):
#     def wrapper(*args):
#         try:
#             func(*args)
#         except psycopg2.Error as e:
#             error_time = time.time()
#             n = 1
#             while True:
#                 if time.time() - error_time > 2**n:
#                     try:
#                         global conn, c, url
#                         # logging.error('Database Error:', e)
#                         conn = psycopg2.connect(
#                             database=url.path[1:],
#                             user=url.username,
#                             password=url.password,
#                             host=url.hostname,
#                             port=url.port
#                         )
#                         c = conn.cursor()
#                         break
#                     except:
#                         print('Reconnect failed', n, 'times')
#                         n += 1
#                         pass
#             func(*args)
#     return wrapper
