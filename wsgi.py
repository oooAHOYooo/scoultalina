import os
from server.app import create_app

# Prefer explicit AIM_ENV, otherwise default "production".
env = os.getenv("AIM_ENV", "production")
app = create_app(env)


