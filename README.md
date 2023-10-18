# large-language-example-app
An example app using large language model (aleph alpha api + microsoft form recognizer) in python

### Getting started
1. Run `pipenv install`
2. Get an API key for the large language model API from Aleph Alpha (free credits provided upon signup) https://app.aleph-alpha.com/signup
3. Sign up to Microsoft Azure and create an API key for the form recognizer (12 months free + free plan with rate limits afterwards) https://azure.microsoft.com/en-us/free/ai/
4. Set `ALEPH_KEY` env variable
5. Set `AZURE_FORM_ENDPOINT` env variable
6. Set `AZURE_FORM_KEY` env variable
7. Run `pipenv run python run.py`
8. Open localhost on port 3000
   
### Usage
The repo contains example receipts but you can upload any of your own. The model was originally used for my previous startups sustainability analysis app and is optimized for German supermarkets. I've included an English version. Simply change line 13 in routes.py to `results = analyze_receipt_en(file)`. The English version contains capitalization mistakes and is based on a google translation of my German Dataset, use with caution. 
