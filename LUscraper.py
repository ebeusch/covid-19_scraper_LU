# -*- coding: utf-8 -*-
"""
Created on Sat Mar 21 15:53:06 2020

@author: ebeusch, based on covid-19 scrapers by @metaodi
"""

import requests
from bs4 import BeautifulSoup
import sqlite3
import re
import json
import dateparser
import traceback
import os

DATABASE_NAME = 'data.sqlite'
conn = sqlite3.connect(DATABASE_NAME)
c = conn.cursor()
c.execute(
    '''
    CREATE TABLE IF NOT EXISTS data (
        date text,
        time text,
        abbreviation_canton_and_fl text,
        ncumul_tested  integer,
        ncumul_conf integer,
        ncumul_hosp integer,
        ncumul_ICU integer,
        ncumul_vent integer,
        ncumul_released integer,
        ncumul_deceased integer,
        source text,
        UNIQUE(date, time, abbreviation_canton_and_fl)
    )
    '''
)
conn.commit()

def parse_page(soup, conn):
    data = {
        'date': None,
        'time': '',
        'area': 'LU',
        'tested': None,
        'confirmed': None,
        'hospitalized': None,
        'icu': None,
        'vent': None,
        'released': None,
        'deceased': None,
        'source': 'https://gesundheit.lu.ch/themen/Humanmedizin/Infektionskrankheiten/Coronavirus'
    }
    
    monthsDE = {'Januar':'01', 'Februar':'02', 'März':'03', 'April':'04', \
    'Mai':'05', 'Juni':'06', 'Juli':'07', 'August':'08', 'September':'09', \
    'Oktober':'10', 'November':'11', 'Dezember':'12'}
    
    
    # parse number of confirmed cases and deceased
    box = soup.find("h2", string=re.compile("Informationen Kanton")).parent.find("p")
    box_str = "".join([str(x) for x in box.contents])

    # ... gibt es 109 bestätige Fälle (Stand: 21. März 2020, 11:00 Uhr)
    case_str = re.search("(\d+).best.tig?e F.lle", box_str).group(1)
    data['confirmed'] = int(case_str)

    dd_str = re.search("Stand: ([\d]+).", box_str).group(1)
    mm_str = monthsDE[re.search("\d\d. ([\D]+) \d\d\d\d,", box_str).group(1)]
    yy_str = re.search(" ([\d]+), ", box_str).group(1)
    data['date'] = yy_str + "." + mm_str + "." + dd_str

    data['time'] = re.search(", ([\d\:]+) Uhr", box_str).group(1)

    c = conn.cursor()

    try:
        print(data)
        c.execute(
            '''
            INSERT INTO data (
                date,
                time,
                abbreviation_canton_and_fl,
                ncumul_tested,
                ncumul_conf,
                ncumul_hosp,
                ncumul_ICU,
                ncumul_vent,
                ncumul_released,
                ncumul_deceased,
                source
            )
            VALUES
            (?,?,?,?,?,?,?,?,?,?,?)
            ''',
            [
                data['date'],
                data['time'],
                data['area'],
                data['tested'],
                data['confirmed'],
                data['hospitalized'],
                data['icu'],
                data['vent'],
                data['released'],
                data['deceased'],
                data['source'],
            ]
        )
    except sqlite3.IntegrityError:
        print("Error: Data for this date + time has already been added")
    finally:
        conn.commit()

# canton lucern - start url
start_url = 'https://gesundheit.lu.ch/themen/Humanmedizin/Infektionskrankheiten/Coronavirus'

# get page with data on it
page = requests.get(start_url)
soup = BeautifulSoup(page.content, "html.parser")

try:
    parse_page(soup, conn)
except Exception as e:
    print("Error: %s" % e)
    print(traceback.format_exc())
    raise
finally:
    conn.close()


# trigger GitHub Action API
if 'MORPH_GH_USER' in os.environ:
    gh_user = os.environ['MORPH_GH_USER']
    gh_token = os.environ['MORPH_GH_TOKEN']
    gh_repo = os.environ['MORPH_GH_REPO']

    url = 'https://api.github.com/repos/%s/dispatches' % gh_repo
    payload = {"event_type": "update"}
    headers = {'content-type': 'application/json'}
    r = requests.post(url, data=json.dumps(payload), headers=headers, auth=(gh_user, gh_token))
    print(r)