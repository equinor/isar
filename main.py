from isar import create_app

if __name__ == "__main__":
    app = create_app()

    host = app.config["HOST"]
    port = app.config["PORT"]

    app.run(host, port, use_reloader=False)
