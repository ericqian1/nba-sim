# -*- coding: utf-8 -*-
"""
Created on Tue May  4 20:46:43 2021

@author: tianz
"""
import pandas as pd
import requests
from bs4 import BeautifulSoup



headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '3600',
    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0'
    }

csv_path = "URL.csv"
df = pd.read_csv(csv_path)
urls = df["URL"]

dates = []

for i, url in enumerate(urls):
    req = requests.get(url[:-1], headers = headers)
    str_content = str(req.content)
    ts = str_content.split("date datet t")[1].split("-")[0]
    date = pd.to_datetime(ts, unit="s")
    print(date.strftime("%Y-%m-%d"))
    
    if i==67:
        break
