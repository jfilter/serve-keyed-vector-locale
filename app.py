import random
import re
from os import environ
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS
from gensim.models import KeyedVectors
from sklearn.decomposition import PCA
from sklearn.preprocessing import MinMaxScaler

app = Flask(__name__)
CORS(app)

DEBUG = not "FILTER_PRODUCTION" in environ

data_dir = "data" if DEBUG else "/data"

vecs = {}
for m in Path(data_dir).glob("*.model"):
    vecs[m.stem] = KeyedVectors.load(str(m), mmap="r")


@app.route("/typeahead/<vec_name>")
def typeahead(vec_name):
    q = request.args.get("q", type=str)

    if q == '':
        return jsonify({"tokens": []})

    v = vecs[vec_name]

    q = re.sub(r"\d+", "0", q)
    q = q.lower()

    tokens = [t for t in v.index2entity if t.startswith(q)]
    tokens = sorted(tokens, key=len)
    return jsonify({"tokens": tokens[:10]})


@app.route("/nearest/<vec_name>")
def nearest(vec_name):
    q, n = request.args.get("q"), request.args.get("n", 10, type=int)
    v = vecs[vec_name]
    results = v.most_similar(q, topn=n)
    tokens, _ = list(zip(*results))
    tokens = [q] + list(tokens)
    vectors = [v[t] for t in tokens]
    vectors = PCA(n_components=2).fit_transform(vectors)
    vectors = MinMaxScaler((-1, 1)).fit_transform(vectors)
    return jsonify({"tokens": tokens, "vectors": vectors.tolist()})


@app.route("/dist/<vec_name>")
def dist(vec_name):
    tokens = request.args.getlist("q")
    v = vecs[vec_name]
    vectors = [v[t] for t in tokens]
    vectors = PCA(n_components=2).fit_transform(vectors)
    vectors = MinMaxScaler((-1, 1)).fit_transform(vectors)
    return jsonify({"tokens": tokens, "vectors": vectors.tolist()})


@app.route("/sim/<vec_name>")
def sim(vec_name):
    """get similarities
    """
    q, n = request.args.get("q"), request.args.get("n", 10, type=int)
    v = vecs[vec_name]
    results = v.most_similar(q, topn=n)
    return jsonify({"tokens": [r[0] for r in results], "sims": [r[1] for r in results]})


@app.route("/sim_multiple/<vec_name>")
def sim_multiple(vec_name):
    """get similarities
    """
    qs = request.args.getlist("q")
    v = vecs[vec_name]
    return jsonify({"tokens": qs, "sims": [v.similarity(qs[0], x) for x in qs[1:]]})


@app.route("/sim_random/<vec_name>")
def sim_random(vec_name):
    """get similarities, n random tokens
    """
    q, n = request.args.get("q"), request.args.get("n", 10, type=int)
    v = vecs[vec_name]
    tokens = [q] + random.sample(v.index2entity, n)
    return jsonify({"tokens": tokens, "sims": [v.similarity(q, x) for x in tokens[1:]]})


@app.route("/token_random/<vec_name>")
def random_tokens(vec_name):
    n = request.args.get("n", 100, type=int)
    v = vecs[vec_name]
    tokens = random.sample(v.index2entity, n)
    return jsonify({"tokens": tokens})


if __name__ == "__main__":
    app.run(debug=DEBUG)
