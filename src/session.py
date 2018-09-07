import requests, random, time, json
from URL import URL
import re

requests.packages.urllib3.disable_warnings()
WAIT_SERVER_RESPONSE_TIME = 30 # how long to wait for a server response // 10s a 30s

class Session(object):
    accept_language = 'en-US,en;q=0.8,pt-br,pt;q=0.6,'
    user_agent = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_1) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/48.0.2564.109 Safari/537.36')
# headers_list = [
#     "Mozilla/5.0 (Windows NT 5.1; rv:41.0) Gecko/20100101" \
#     " Firefox/41.0",
#     "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_2)" \
#     " AppleWebKit/601.3.9 (KHTML, like Gecko) Version/9.0.2" \
#     " Safari/601.3.9",
#     "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:15.0)" \
#     " Gecko/20100101 Firefox/15.0.1",
#     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
#     " (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36" \
#     " Edge/12.246"
# ]

    def __init__(self, username, password, logger=None):
        self.user_login = username.lower()
        self.user_password = password
        self.session = requests.Session()
        self.logger = logger
        self.login_status = False
        self.rollout_hash = None

    def __del__(self):
        if self.login_status:
            self.logout()

    def login(self):

        self.log('User: %s --> Login attempt...' % (self.user_login))
        self.session.cookies.update({'sessionid': '', 'mid': '', 'ig_pr': '1',
                                     'ig_vw': '1920', 'csrftoken': '',
                                     's_network': '', 'ds_user_id': ''})
        self.login_post = {'username': self.user_login,
                           'password': self.user_password}
        self.session.headers.update({'Accept-Encoding': 'gzip, deflate',
                                     'Accept-Language': self.accept_language,
                                     'Connection': 'keep-alive',
                                     'Content-Length': '0',
                                     'Host': 'www.instagram.com',
                                     'Origin': 'https://www.instagram.com',
                                     'Referer': 'https://www.instagram.com/',
                                     'User-Agent': self.user_agent,
                                     'X-Instagram-AJAX': '1',
                                     'X-Requested-With': 'XMLHttpRequest'})
        request = self.session.get(URL.root)
        self.session.headers.update({'X-CSRFToken': request.cookies['csrftoken']})
        data_login = self.get_data_from_html(request.text)
        rollout_hash = data_login['rollout_hash']
        csrf_token = re.search('(?<=\"csrf_token\":\")\w+', request.text).group(0)
#   self.s.headers.update({'X-CSRFToken': csrf_token})
        self.log("csrf_token from root page="+csrf_token)
        self.rollout_hash=rollout_hash
        self.log('Rollout Hash='+rollout_hash)
        self.session.headers.update({'X-Instagram-AJAX': rollout_hash})
        time.sleep(random.randint(2, 5))
        login = self.session.post(URL.login, data=self.login_post, allow_redirects=True)

        #json_login = json.loads(login.text)

        # self.log(data_login)
        self.session.headers.update({'X-CSRFToken': login.cookies['csrftoken']})
        self.log(login)
        self.session.cookies['ig_vw'] = '1536'
        self.session.cookies['ig_pr'] = '1.25'
        self.session.cookies['ig_vh'] = '772'
        self.session.cookies['ig_or'] = 'landscape-primary'
        self.log("csrf_token from cookie="+login.cookies['csrftoken'])
        self.session.headers.update({'X-Instagram-AJAX': rollout_hash})
        self.csrftoken = login.cookies['csrftoken']
        time.sleep(random.randint(2, 5))
        if login.status_code == 200:
            request = self.session.get(URL.root)
            finder = request.text.find(self.user_login)
            if finder != -1:
                self.login_status = True
                self.log('User: %s --> Successful login!' % (self.user_login))
            else:
                self.log('Wrong username or password.')
        else:
            self.log('Wrong username or password.')

    def logout(self):
        try:
            logout_post = {'csrfmiddlewaretoken': self.csrftoken}
            logout = self.session.post(URL.logout, data=logout_post)
            self.log("Successful logout!")
            self.login_status = False
        except:
            self.log("Error: Unsuccessful logout.")

    def get_data_from_html(self, html):
        try:
            finder_start = '<script type="text/javascript">window._sharedData = '
            finder_end = ';</script>'
            if html is None:
                return None
            data_start = html.find(finder_start)
            data_end = html.find(finder_end, data_start+1)
            json_str = html[data_start+len(finder_start):data_end]
            data = json.loads(json_str)
            return data
        except json.decoder.JSONDecodeError as e:
            self.logger.log('Error parsing json string: ' + str(e))
            pass

    def get(self, url):
        response = self.session.get(url)
        self.log("GET request to: " + url + " - Status: " + str(response.status_code))
        return response.status_code

    def get_html(self, url):
        time_between_requests = random.randint(7,12)
        self.logger.log('Fetching ' + url)
        response = requests.get(url, verify=False, timeout=WAIT_SERVER_RESPONSE_TIME)
        html = response.text
        time.sleep(time_between_requests)
        return html

    def get_response(self, url):
        response = self.session.get(url)
        self.log("GET request to: " + url + " - Status: " + str(response.status_code))
        return response


    def post(self, url):
        response = self.session.post(url)
        self.log("POST request to: " + url + " - Status: " + str(response.status_code))
        return response.status_code


    def log(self, text):
        if self.logger:
            self.logger.log(text)
        else:
            print(text)
