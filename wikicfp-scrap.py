"""
a script which scrapes WikiCFP events and exports as a .ics file

requires:
    requests: https://pypi.org/project/requests/
    beautifulsoup: https://pypi.org/project/beautifulsoup4/

"""

from urllib.parse import urljoin

from bs4 import BeautifulSoup
from requests import Session
from argparse import ArgumentParser

import re

class WikiCFPSession(Session):
    DOMAIN = "http://www.wikicfp.com"

    def __init__(self, **kwargs):
        super(WikiCFPSession, self).__init__(**kwargs)

    def request(self, method, path, **kwargs):
        url = urljoin(self.DOMAIN, path)
        resp = super(WikiCFPSession, self).request(method, url, **kwargs)
        resp.raise_for_status()
        return resp


def login(session, username, password):
    """Login to WikiCFP using session object to store cookies"""

    session.post("/cfp/servlet/user.regin", data={
        "accountsel": username,
        "password": password,
        "keepin": "on",
        "mode": "login",
    }, allow_redirects=False)


def get_events(session, categories):
    """
    Get list of event ids by parsing HTML.
    Stop when row text == "Expired CFPs"

    Returns a list of ids
    """
    events = []
    last_page = 1
    for category in categories:

        resp = session.get("/cfp/call", params={"conference": category, "page": 1})
        soup = BeautifulSoup(resp.text, 'html.parser')
        rows = soup.select(".contsec table tr table td")


        for a in soup.findAll('a', href=re.compile(r'page=.+')):
            if a.contents[0]=="last":
                last_page = int(re.compile(r'(\d+)$').search(a["href"]).group(1))


        for i in range(1, last_page+1):
            resp = session.get("/cfp/call", params={"conference": category, "page": i})
            soup = BeautifulSoup(resp.text, 'html.parser')
            rows = soup.select(".contsec table tr table td")

            for row in rows:
                if row.get_text() == "Expired CFPs":
                    break

                for event in row.select('input[type="checkbox"]'):
                    if event["name"] != "checkall":
                        events.append(event["name"])
        print("# of event in {c} category = {e}".format(c=category, e=len(events)))
    return events


def save_events(session, events):
    """
    Takes a list of event ids and saves them to the users WikiCFP list
    """
    payload = {
        'getaddress': 'call',
    }
    for event in events:
        payload[event] = 'on'

    session.get("/cfp/servlet/event.copycfp",
                params=payload,
                allow_redirects=False)


def export_calender(session, path=None):
    """
    Export .ics format to stdout or filepath
    """
    cookies = session.cookies.get_dict()
    user_id = cookies["accountkey"].split("%")[0]
    resp = session.get("/cfp/servlet/event.showcal", params={"list": user_id})
    if not path:
        print(resp.text)
    else:
        with open(path, 'w') as ics:
            ics.write(resp.text)


if __name__ == "__main__":

    parser = ArgumentParser(description='WikiCFP scrapping.')

    parser.add_argument('-a',
                        '--account',
                        action='store',
                        dest='account',
                        type=str,
                        nargs='*',
                        help="WikiCFP account",
                        required=True)

    parser.add_argument('-p',
                        '--password',
                        action='store',
                        dest='password',
                        type=str,
                        nargs='*',
                        help="WikiCFP password",
                        required=True)

    parser.add_argument('-c',
                        '--category',
                        action='store',
                        dest='category',
                        type=str,
                        nargs='*',
                        default=['NLP', 'natural language processing', 'human computer interaction', 'human-computer interaction'],
                        help="list of categories from WikiCFP. Examples: -c category1 category2")


    args = parser.parse_args()


    with WikiCFPSession() as session:
        login(session, args.account, args.password)
        events = get_events(session, args.category)
        save_events(session, events)
        export_calender(session, "./events.ics")
