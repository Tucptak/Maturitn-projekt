from flask import Flask, redirect, render_template, request, url_for

app = Flask(__name__, template_folder="templates")
app.config["SECRET_KEY"] = "tajny_klic"


KOMENTARE = [
    {"author": "Pavel Podrazký", "text": "Super stránka!"},
    {"author": "Pepa Vomáčka", "text": "Nudná stránka!"},
    {"author": "Jana Nováková", "text": "Krásná stránka!"},
]


@app.route("/")
def index():
    chyba = request.args.get("chyba")
    return render_template("index.html", komentare=KOMENTARE, chyba=chyba)


@app.route("/komentar", methods=["POST"])
def zpracuj_komentar():
    author = request.form.get("author")
    text = request.form.get("text")
    if not author or not text:
        return redirect(url_for("index", chyba="Vyplňte prosím obě pole."))
    KOMENTARE.append({"author": author, "text": text})
    return redirect(url_for("index", chyba=None))


if __name__ == "__main__":
    app.run(debug=True)
