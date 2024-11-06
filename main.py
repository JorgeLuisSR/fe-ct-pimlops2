from fastapi import FastAPI
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
import pandas as pd
import ast

app = FastAPI()

movies = pd.read_csv("datasets/movies_final.csv", index_col = ["id"])
cast = pd.read_csv("datasets/cast.csv", index_col = ["id"])
directors = pd.read_csv("datasets/directors.csv", index_col = ["id"])
data_ml = pd.read_csv('datasets/ml_encoded_data.csv')

movies.shape
cast.shape
directors.shape

months = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"]
weekdays = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def get_movie_description(row):
    return f'{row["title"]} | {row["release_date"]} | retorno: {row["return"]} , costo: {row["budget"]} , ganancia: {row["revenue"]}'

@app.get("/")
async def read_root():
    return {"hello":"world"}

@app.get("/cantidad_filmaciones_mes")
async def cantidad_filmaciones_mes( Mes : str):  
    try:
        index = months.index(Mes.lower()) +1
    except ValueError:
        return f"{Mes} no es un mes valido"
    movies_in_month = movies[pd.to_datetime(movies["release_date"]).dt.month == index]
    return f"{len(movies_in_month)} películas fueron estrenadas en el mes de {Mes.lower().capitalize()}"

@app.get("/cantidad_filmaciones_dia")
async def cantidad_filmaciones_dia( Dia :str): 
    try:
        index = weekdays.index(Dia.lower())
    except ValueError:
        return f"{Dia} no es un dia valido"
    movies_in_day = movies[pd.to_datetime(movies["release_date"]).dt.weekday == index]
    return f"{len(movies_in_day)} películas fueron estrenadas en los días {Dia.lower().capitalize()}"

@app.get("/score_titulo")
async def score_titulo( titulo_de_la_filmación ): 
    movie_candidates = movies.loc[movies["title"].str.lower() == titulo_de_la_filmación.lower()]
    if len(movie_candidates) > 0:
        movie = movie_candidates.iloc[0]
    else:
        movie = None
    
    if movie is None:
        return f"La filmacion {titulo_de_la_filmación} no se encuestra en la base de datos"
    return f"La película {movie['title']} fue estrenada en el año {movie['release_year']} con un score/popularidad de {movie['popularity']:.6f}"

@app.get("/votos_titulo")
async def votos_titulo( titulo_de_la_filmación ): 
    movie_candidates = movies.loc[movies["title"].str.lower() == titulo_de_la_filmación.lower()]
    if len(movie_candidates) > 0:
        movie = movie_candidates.iloc[0]
    else:
        movie = None
    
    if movie is None:
        return f"La filmacion {titulo_de_la_filmación} no se encuestra en la base de datos"
    
    votes = movie["vote_count"]
    votes_avg = movie["vote_average"]
    msj = "Sin votos suficientes." if int(votes) < 2000 else f'La misma cuenta con un total de {int(movie["vote_count"])} valoraciones, con promedio de {votes_avg:.4f}.'
    return f'La película {movie["title"]} fue estrenada en el año {movie["release_year"]}. {str(msj)}'

@app.get("/get_actor")
async def get_actor( nombre_actor ): 
    actor = cast[cast["name"].str.lower() == nombre_actor.lower()]
    
    if actor.empty:
        return f'No se ha encontrado un actor llamado {nombre_actor}'
    
    actor = actor.iloc[0]
    movies_ids = ast.literal_eval(actor["performances"])
    
    ret = movies[movies.index.isin(movies_ids)]["return"].sum()
    
    perfs = len(movies_ids)
    
    return f'El actor {actor["name"]} ha participado de {perfs} cantidad de filmaciones, el mismo ha conseguido un retorno de {ret} con un promedio de {ret/perfs :.6f} por filmación'

@app.get("/get_director")
async def get_director( nombre_director ): 
    direc = directors[directors["name"].str.lower() == nombre_director.lower()]
    
    if direc.empty:
        return f'No se ha encontrado un director llamado {nombre_director}'
    direc = direc.iloc[0]
    
    movies_ids = ast.literal_eval(direc["directions"])
    directed_movies = movies[movies.index.isin(movies_ids)]
    
    ret = directed_movies["return"].sum()
    dirs = len(directed_movies)
    
    movies_desc = ""
    for _, m in directed_movies.iterrows():
        movies_desc += get_movie_description(m) + "\n"
    
    return f'El director {direc["name"]} ha participado de {dirs} cantidad de filmaciones, el mismo ha conseguido un retorno de {ret} con un promedio de {ret/dirs :.6f} por filmación.\n {movies_desc}'

scaler = StandardScaler()
features = data_ml[['popularity', 'return', 'vote_average', 'release_year', 'runtime']]
scaled_features = pd.DataFrame(scaler.fit_transform(features.values))

cols =data_ml[["id",'16','35','10751','12','14','10749','18','28','80','53','27','36','878','9648','10752','10402','99','37','10769','10770','en','fr','es','de','it','ja','ru','zh','pt','cn','other_lang']]

final_features= pd.concat([scaled_features, cols], axis=1)
final_features.fillna(0, inplace=True)


@app.get("/get_director")
async def recomendacion(titulo, num_recommendations=5):

    try:
        movie_data= movies[movies['title'].str.lower() == titulo.lower()].iloc[0]
    except IndexError:
        return f"Movie '{titulo}' not found in the dataset."
    
    movie_features = final_features[final_features["id"]==movie_data.name].drop(columns="id").values.reshape(1, -1)
    # Compute cosine similarity with the feature matrix
    
    similaryties = list(enumerate(cosine_similarity(movie_features,final_features.drop(columns="id"))[0]))
    
    sim = sorted(similaryties, reverse=True, key=lambda t: t[1])
    # Get indices of the most similar movies (skip the first one because it's the same movie)
    
    similar_indices =sim[1:num_recommendations + 1]
    idx = [final_features.loc[i[0], "id"] for i in similar_indices ]
    # Return recommended movie titles
    return movies.loc[idx]["title"].tolist()
