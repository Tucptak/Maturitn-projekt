from flask import Flask, render_template, request, redirect, url_for
import os
import json

app = Flask(__name__)

@app.route("/")
def index():
    aktivni_soubor = os.path.dirname(__file__)
    SITE_ROOT = os.path.realpath(aktivni_soubor)
    json_url = os.path.join(SITE_ROOT, "static/data", "uzivatele.json")
    UZIVATELE = json.load(open(json_url, "r", encoding="utf-8"))
    print(UZIVATELE)
    return render_template("index.html", uzivatle=UZIVATELE)

@app.route("/zapis")
def zapis_uzivatele():
    jmeno = "addmin"
    heslo = "admin"

    SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
    json_url = os.path.join(SITE_ROOT, "static/data", "uzivatele.json")
    UZIVATELE = json.load(open(json_url, "r", encoding="utf-8"))
    UZIVATELE.append({jmeno: heslo})
    with open(json_url, "w", encoding="utf-8") as outfile:
        json.dump(UZIVATELE, outfile)

    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
