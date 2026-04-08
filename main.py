from kindling import Application

app = Application(template_dir="templates")
app.static("/static", "static")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)
