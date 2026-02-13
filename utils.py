import random

# Reyting asosida eng ko‘p ko‘rilgan kinolarni chiqarish
def top_movies(movies_list, top_n=5):
    # movies_list = [(code, name, views)]
    movies_list.sort(key=lambda x: x[2], reverse=True)
    return movies_list[:top_n]

# Aralash / random kinolar
def random_movies(movies_list, n=5):
    return random.sample(movies_list, min(len(movies_list), n))
