from main import app
from telegram.ext import Application

# Esta função é necessária para o Gunicorn
def create_app():
    return app

# Expor a aplicação
application = create_app()
