# api-helper

# How to run locally
- Install python3
- Open console and navigate to project folder
- Set up python virtual env:
  - py -m venv .venv or python3 -m venv .venv
- Activate python env:
  - cd .venv -> cd scripts -> activate 
- Install required packages:
  - pip install -r requirements.txt
- Create .env file to main folder with:
  - CLIENT_ID = 'client_id_here'
  - CLIENT_SECRET = 'client_secret_here'
- Run commands:
  - set flask_app=application.py (set flask_app on windows, export flask_app on others)
  - flask run
- App can be found on browser at localhost:5000
