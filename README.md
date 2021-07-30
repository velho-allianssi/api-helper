# api-helper

# How to run locally

- Install python3
- Open console and navigate to project folder
- Set up python virtual env:
  - py -m venv .venv or python3 -m venv .venv


- Activate python env:
  - cd .venv -> cd scripts -> activate 
  - (cd back to main folder: cd .. -> cd ..)
- Install required packages:
  - pip install -r requirements.txt
- Create .env file to main folder that contains:
  - CLIENT_ID = 'client_id_here'
  - CLIENT_SECRET = 'client_secret_here'
- Run commands:
  - set flask_app=application.py (set flask_app on windows, export flask_app on others)
  - flask run
- App can be found on browser at localhost:5000

# Proxies
- If your device has restrictions, it is possible that application cant send requests to the API
- Fix: 
  - Once set flask_app=application.py is done
  - Depending on the proxy use one of the next: 
    - set http_proxy= __proxy address__
    - set https_proxy= __proxy address__
    - set ftp_proxy= __proxy address__
    - For example if proxy address starts with http -> use set http_proxy
