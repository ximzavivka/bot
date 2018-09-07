import yaml, requests, random, time, datetime, json, sys, re
from logger import Logger
from session import Session
from URL import URL

requests.packages.urllib3.disable_warnings()
WAIT_SERVER_RESPONSE_TIME = 30  # how long to wait for a server response // 10s a 30s


class InstaBot(object):
    is_checked = False
    is_selebgram = False
    is_fake_account = False
    is_active_user = False
    is_following = False
    is_follower = False
    is_rejected = False
    is_self_checking = False
    is_by_tag = False

    def __init__(self, config_path, log_file_path=None):
        start_time = datetime.datetime.now()
        config = yaml.safe_load(open(config_path, "r"))
        username, password, tags, total_likes, total_follows, likes_per_user, total_unfollows = (
            config['CREDENTIALS']['USERNAME'], config['CREDENTIALS']['PASSWORD'],
            config['TAGS'], config['TOTAL_LIKES'], config['TOTAL_FOLLOWS'], config['LIKES_PER_USER'],
            config['TOTAL_UNFOLLOWS'])
        self.unwanted_username_list = list()
        self.keep_users = list()
        self.never_follow = list()
        self.unwanted_username_list = config['UNWANTED_USER_NAMES_LISTS']
        self.keep_users = config['USERS']['KEEP']
        self.never_follow = config['USERS']['NEVER_FOLLOW']
        self.logger = Logger(username, log_file_path)
        self.logger.log('InstaBot v1.0 started at: %s' % (start_time.strftime("%d.%m.%Y %H:%M")))
        self.total_likes = total_likes + self.iround(min(total_likes / 2, max(-total_likes / 2, random.gauss(0,
                                                                                                             100))))  # gaussian distribution: mu = 0, sig = 100, round to nearest int
        self.total_follows = total_follows + self.iround(min(total_follows / 2, max(-total_follows / 2, random.gauss(0,
                                                                                                                     100))))  # gaussian distribution: mu = 0, sig = 100, round to nearest int
        self.total_unfollows = total_unfollows + self.iround(
            min(total_unfollows / 2, max(-total_unfollows / 2, random.gauss(0, 100))))  # gaussian distribution: mu
        self.logger.log('InstaBot v1.0 will like ' + str(self.total_likes) + ' photos in total')
        self.logger.log('-------------------follow ' + str(self.total_follows) + ' users in total')
        self.logger.log('-------------------unfollow ' + str(self.total_unfollows) + ' users in total')
        self.likes_per_user = likes_per_user
        self.liked_photos = set()

        self.unfollowed_users = set()
        self.followed_users = set()
        self.session = Session(username, password, self.logger)
        # random.shuffle(tags)
        self.run(username, password, tags, False)

        # count = total_unfollows
        # while (count > 0):
        #    to_unfollow_counter = random.randint(22, 50)
        #    self.run_unfollow(username, password, to_unfollow_counter)
        #    count = count - to_unfollow_counter

        self.session.logout()
        end_time = datetime.datetime.now()
        self.logger.log('InstaBot v1.0 stopped at: %s' % (end_time.strftime("%d.%m.%Y %H:%M")))
        self.logger.log('InstaBot v1.0 took ' + str(end_time - start_time) + ' in total')

    def get_html(self, url):
        time_between_requests = random.randint(7, 12)
        self.logger.log('Fetching ' + url)
        response = requests.get(url, verify=False, timeout=WAIT_SERVER_RESPONSE_TIME)
        html = response.text
        time.sleep(time_between_requests)
        return html

    def get_json(self, url):
        if (self.session.login_status):
            try:
                time_between_requests = random.randint(7, 12)
                # self.logger.log('Fetching ' + url)
                # response = requests.get(url, verify=False, timeout=WAIT_SERVER_RESPONSE_TIME)
                response = self.session.get_response(url)
                json_ = json.loads(response.text)
                time.sleep(time_between_requests)
                return json_
            except json.decoder.JSONDecodeError as e:
                self.logger.log('Error parsing json string: ' + str(e))
                status = 0
                self.logger.log("Get followings operation failed: " + url)
                pass

    def get_data_from_html(self, html):
        try:
            finder_start = '<script type="text/javascript">window._sharedData = '
            finder_end = ';</script>'
            if html is None:
                return None
            data_start = html.find(finder_start)
            data_end = html.find(finder_end, data_start + 1)
            json_str = html[data_start + len(finder_start):data_end]
            data = json.loads(json_str)
            return data
        except json.decoder.JSONDecodeError as e:
            self.logger.log('Error parsing json string: ' + str(e))
            pass

    def write_log(self, log_text):
        """ Write log by print() or logger """
        try:
            now_time = datetime.datetime.now()
            print(now_time.strftime("%d.%m.%Y_%H:%M") + " " + log_text)
        except UnicodeEncodeError:
            print("Your text has unicode problem!")

    def get_recent_tag_photos(self, tag):
        url = URL.tag + tag
        photos = list()
        min_likes = 5
        max_likes = 500
        min_comments = 1
        max_comments = 50
        try:
            html = self.get_html(url)

            # self.write_log(current_user)

            data = self.get_data_from_html(html)
            if data is None:
                return None

                # get data from recent posts only
            photos_json = list(data['entry_data']['TagPage'][0]['graphql']['hashtag']['edge_hashtag_to_media']['edges'])
            for photo_json in photos_json:
                photo_id = photo_json['node']['shortcode']
                likes = photo_json['node']['edge_liked_by']['count']
                comments = photo_json['node']['edge_media_to_comment']['count']
                if photo_id not in self.liked_photos and ((likes >= min_likes and likes <= max_likes) or (
                        comments >= min_comments and comments <= max_comments)):
                    photos.append(photo_id)
                    if len(photos) == 10:
                        break
                # fill up rest of photos list with top posts, until list has 10 potential people to be liked
                if len(photos) < 10:
                    photos_json = list(
                        data['entry_data']['TagPage'][0]['graphql']['hashtag']['edge_hashtag_to_media']['edges'])
                    for photo_json in photos_json:
                        photo_id = photo_json['node']['shortcode']
                        likes = photo_json['node']['edge_liked_by']['count']
                        comments = photo_json['node']['edge_media_to_comment']['count']
                        if photo_id not in self.liked_photos and ((likes >= min_likes and likes <= max_likes) or (
                                comments >= min_comments and comments <= max_comments)):
                            photos.append(photo_id)
                            if len(photos) == 10:
                                break
        except (KeyError, IndexError, TypeError) as e:
            self.logger.log('Error parsing url: ' + url + ' - ' + str(e))
            time.sleep(10)
            pass
        return photos

    def get_users_to_unfollow(self, to_unfollows_counter):
        url = (URL.following % str(to_unfollows_counter))
        users_to_unfollow = list()
        try:
            data = self.get_json(url)
            # get id from user to unfollow
            users_to_unfollow_json = list(data['data']['user']['edge_follow']['edges'])
            for user_json in users_to_unfollow_json:
                user_id = user_json['node']['id']
                if user_id not in self.unfollowed_users and user_id not in self.keep_users:
                    users_to_unfollow.append(user_id)
        except (KeyError, IndexError, TypeError) as e:
            self.logger.log('Error parsing url: ' + url + ' - ' + str(e))
            time.sleep(10)
            pass
        return list(set(users_to_unfollow) - set(self.keep_users))

    def get_photo_owner(self, photo_id):
        try:
            photo_url = URL.photo + photo_id
            html = self.get_html(photo_url)
            data = self.get_data_from_html(html)
            if data is None:
                return None, None
            self.logger.log(
                '++++++++++++++++: ' + str('entry_data' in data) + ' - ' + str('PostPage' in data['entry_data']))
            if (('entry_data' in data) and ('PostPage' in data['entry_data'])):
                # owner_name = data['entry_data']['PostPage'][0]['media']['owner']['username'] # deprecated
                owner_name = data['entry_data']['PostPage'][0]['graphql']['shortcode_media']['owner'][
                    'username']  # new format
                owner_id = data['entry_data']['PostPage'][0]['graphql']['shortcode_media']['owner']['id']  # new format
                return owner_name, owner_id
            else:
                return None, None
        except (KeyError, IndexError, TypeError) as e:
            self.logger.log('Error parsing url: ' + photo_url + ' - ' + str(e))
            time.sleep(10)
            pass
            return None, None

    # get owner recent photos only if he/she meets requirements
    def get_owner_recent_photos(self, owner_name):
        photos = list()
        min_followed_by = 200
        max_followed_by = 2000
        min_follows = 200
        max_follows = 7500  # instagram limit
        min_follow_ratio = 0.05
        max_follow_ratio = 5.0
        owner_url = URL.root + owner_name
        html = self.get_html(owner_url)
        try:
            data = self.get_data_from_html(html)
            if data is None:
                return None
            user = data['entry_data']['ProfilePage'][0]['graphql']['user']
            follows = user['edge_follow']['count']
            followed_by = user['edge_followed_by']['count']
            if follows == 0:
                follows = 1
            follow_ratio = followed_by / follows
            if (follows >= min_follows and follows <= max_follows and
                    followed_by >= min_followed_by and followed_by <= max_followed_by and
                    follow_ratio >= min_follow_ratio and follow_ratio <= max_follow_ratio):
                # self.logger.log('Fetching user [' + owner_name + '] photo urls. (Follows: ' + str(follows) + ', Followed By: ' + str(followed_by) + ', Ratio: ' + str(follow_ratio) + ')')
                photos_json = user['edge_owner_to_timeline_media']['edges']
                log_str = 'Photo codes: '
                for i, photo_json in enumerate(photos_json):
                    if i == self.likes_per_user:
                        break
                    photo_node = photo_json['node']
                    photo_id = photo_node['id']
                    photo_code = photo_node['shortcode']
                    if photo_id not in self.liked_photos:
                        photos.append(photo_id)
                        log_str += photo_code + ' '
                # self.logger.log(log_str.strip())
                # self.logger.log('Photo IDs: ' + str(photos))
            else:
                self.logger.log('User [' + owner_name + '] doesn\'t meet requirements. (Follows: ' + str(
                    follows) + ', Followed By: ' + str(followed_by) + ')')
        except (KeyError, IndexError) as e:
            self.logger.log('Error parsing url: ' + url + ' - ' + str(e))
            time.sleep(10)
            pass
        return photos

    def get_photos_to_like_from_tag(self, tag):
        photos_to_like = list()
        owners = list()
        recent_photos = self.get_recent_tag_photos(tag)
        if recent_photos is None:
            return None, None
        # self.logger.log('recent_photos='+str(recent_photos))
        for recent_photo in recent_photos:
            owner_name, owner_id = self.get_photo_owner(recent_photo)

            for blacklisted_user_id in self.never_follow:
                if owner_id == blacklisted_user_id or self.username_checker(owner_name, owner_id) == 0:
                    self.write_log("Not liking media owned by blacklisted user: " + owner_id + " " + owner_name)
                else:
                    if (self.validate_owner(owner_name, owner_id) == True):
                        if owner_name is not None:
                            recent_photos_user = self.get_owner_recent_photos(owner_name)
                            if recent_photos_user is not None:
                                photos_to_like += recent_photos_user
                        if owner_id is not None:
                            owners.append(owner_id)
                            self.logger.log('owner_id=' + owner_id + '  name=' + owner_name)
        return photos_to_like, list(set(owners) - set(self.never_follow))

    def validate_owner(self, owner_name, owner_id):
        url = (URL.url_user_detail % owner_name)
        html = self.get_html(url)
        all_data = self.get_data_from_html(html)
        if all_data is None:
            return False
        all_data = all_data['entry_data']['ProfilePage'][0]
        user_info = all_data['graphql']['user']
        log_string = "Checking user info.."
        self.write_log(log_string)
        follows = user_info['edge_follow']['count']
        follower = user_info['edge_followed_by']['count']
        media = user_info['edge_owner_to_timeline_media']['count']
        follow_viewer = user_info['follows_viewer']
        followed_by_viewer = user_info[
            'followed_by_viewer']
        requested_by_viewer = user_info[
            'requested_by_viewer']
        has_requested_viewer = user_info[
            'has_requested_viewer']
        log_string = "Follower : %i" % (follower)
        self.write_log(log_string)
        log_string = "Following : %s" % (follows)
        self.write_log(log_string)
        log_string = "Media : %i" % (media)
        self.write_log(log_string)
        if follows == 0 or follower / follows > 2:
            self.is_selebgram = True
            self.is_fake_account = False
            print('   >>>This is probably Selebgram account')
        elif follower == 0 or follows / follower > 2:
            self.is_fake_account = True
            self.is_selebgram = False
            print('   >>>This is probably Fake account')
        else:
            self.is_selebgram = False
            self.is_fake_account = False
            print('   >>>This is a normal account')

        if media > 0 and follows / media < 25 and follower / media < 25:
            self.is_active_user = True
            print('   >>>This user is active')
        else:
            self.is_active_user = False
            print('   >>>This user is passive')

        if follow_viewer or has_requested_viewer:
            self.is_follower = True
            print("   >>>This account is following you")
        else:
            self.is_follower = False
            print('   >>>This account is NOT following you')

        if followed_by_viewer or requested_by_viewer:
            self.is_following = True
            print('   >>>You are following this account')
        else:
            self.is_following = False
            print('   >>>You are NOT following this account')
        if (self.is_selebgram is not False
                or self.is_fake_account is not False
                or self.is_active_user is not True
                or self.is_follower is not True):
            return False

        return True

    # def get_photos_to_like(self, tags):
    #     photos_to_like = list()
    #     for tag in tags:
    #         self.logger.log('Finding photos with tag: #' + tag)
    #         photos_to_like += self.get_photos_to_like_from_tag(tag)
    #         self.logger.log('There are ' + str(len(photos_to_like)) + ' photos in the like queue')
    #     return photos_to_like

    def like(self, photo_id):
        if (self.session.login_status):
            url = (URL.like % photo_id)
            try:
                status = self.session.post(url)
            except:
                status = 0
                self.logger.log("Like failed: " + url)
                pass
            return status

    def follow(self, owner):
        if (self.session.login_status):
            url = (URL.follow % owner)
            try:
                status = self.session.post(url)
            except:
                status = 0
                self.logger.log("Follow failed: " + url)
                pass
            return status

    def unfollow(self, user_to_unfollow):
        if (self.session.login_status):
            url = (URL.unfollow % user_to_unfollow)
            try:
                status = self.session.post(url)
            except:
                status = 0
                self.logger.log("UnFollow failed: " + url)
                pass
            return status

    def iround(self, x):
        return int(round(x) - .5) + (x > 0)  # round a number to the nearest integer

    def run(self, login, password, tags, ignoreFollowingTotal):
        likes = 0
        perseverance = 0
        patience = 4
        follows = 0
        flag = True
        while flag:
            for tag in tags:
                self.logger.log('Finding photos with tag: #' + tag)
                like_queue, owners = self.get_photos_to_like_from_tag(tag)
                if like_queue is None:
                    break
                # self.logger.log('owners: #' + str(owners))
                if not self.session.login_status:
                    self.session.login()
                while len(like_queue) > 0:
                    self.logger.log('There are ' + str(len(like_queue)) + ' photos in the like queue for tag:' + tag)
                    if len(like_queue) > 14:
                        likes_per_cycle = self.iround(min(20, max(0, random.gauss(10,
                                                                                  2))))  # gaussian distribution: mu = 10, sig = 2, round to nearest int
                    else:
                        likes_per_cycle = len(like_queue)
                    like_next, like_queue = like_queue[:likes_per_cycle], like_queue[likes_per_cycle:]
                    self.logger.log('Liking ' + str(likes_per_cycle) + ' photos now...')
                    for photo_id in like_next:
                        status = self.like(photo_id)
                        if status == 200:
                            self.liked_photos.add(photo_id)
                            likes += 1
                            if likes >= self.total_likes:
                                self.logger.log(
                                    '[%s] Success! Reached total number of likes. InstaBot is sleeping for 4hours...' % (
                                        datetime.datetime.now().strftime("%d.%m.%Y %H:%M")))
                                # self.logger.log('Success! Reached total number of likes. InstaBot is shutting down...')
                                flag = False
                                break
                            perseverance = 0
                            self.logger.log(
                                '[%s] Total likes: ' % (datetime.datetime.now().strftime("%d.%m.%Y %H:%M")) + str(
                                    likes) + ' / ' + str(self.total_likes))
                        elif status == 400:
                            perseverance += 1
                            if perseverance < patience - 1:  # the bot knows when patience is more important then perseverance
                                self.logger.log('Error 400 - # ' + str(perseverance))
                            else:
                                wait = random.randint(45, 75) * 60
                                self.logger.log(
                                    '[%s] Error 400 - # ' % (datetime.datetime.now().strftime("%d.%m.%Y %H:%M")) + str(
                                        perseverance) + '- You might have been banned. Who knows for sure? InstaBot will chill for ' + str(
                                        wait / 60) + ' minutes...')
                                time.sleep(wait)
                        # sleep after one like (from 10s to 15s)
                        wait = random.randint(10, 15)
                        time.sleep(wait)
                    # if flag:
                    #     if random.randint(1,100) > 5:
                    #         # sleep after liking cycle (from 3min to 7min)
                    #         wait = random.randint(3,7)*60
                    #         self.logger.log('[%s] Finished liking cycle. Sleeping for '% (datetime.datetime.now().strftime("%d.%m.%Y %H:%M")) + str(int(wait/60)) + ' minutes...')
                    #         time.sleep(wait)
                    #     else:
                    #         # sleep longer after 5% of cycles (from 7min to 15 min)
                    #         wait = random.randint(7,15)*60
                    #         self.logger.log('[%s] Coffee time! Will be back in ' % (datetime.datetime.now().strftime("%d.%m.%Y %H:%M")) + str(int(wait/60)) + ' minutes...')
                    #         time.sleep(wait)

                if owners is None or self.total_follows == 0:
                    break
                self.logger.log('There are ' + str(len(owners)) + ' people to follow')
                while len(owners) > 0:
                    if len(owners) > 14:
                        follow_per_cycle = self.iround(min(20, max(0, random.gauss(10,
                                                                                   2))))  # gaussian distribution: mu = 10, sig = 2, round to nearest int
                    else:
                        follow_per_cycle = len(owners)
                    owner_next, owners = owners[:follow_per_cycle], owners[follow_per_cycle:]
                    self.logger.log('Following ' + str(follow_per_cycle) + ' users now...')
                    for owner_id in owner_next:
                        status = self.follow(owner_id)
                        if status == 200:
                            self.followed_users.add(owner_id)
                            follows += 1
                            if follows > self.total_follows:
                                self.logger.log(
                                    '[%s] Success! Reached total number of follows. InstaBot is sleeping for 4 hours...' % (
                                        datetime.datetime.now().strftime("%d.%m.%Y %H:%M")))
                                if not ignoreFollowingTotal:
                                    flag = False
                                break
                            perseverance = 0
                            self.logger.log('Total follows: ' + str(follows) + ' / ' + str(self.total_follows))
                        elif status == 400:
                            perseverance += 1
                            if perseverance < patience - 1:  # the bot knows when patience is more important then perseverance
                                self.logger.log(
                                    '[%s] Error 400 - # ' % (datetime.datetime.now().strftime("%d.%m.%Y %H:%M")) + str(
                                        perseverance))
                            else:
                                wait = random.randint(45, 75) * 60
                                self.logger.log(
                                    '[%s] Error 400 - # ' % (datetime.datetime.now().strftime("%d.%m.%Y %H:%M")) + str(
                                        perseverance) + '- You might have been banned. Who knows for sure? InstaBot will chill for ' + str(
                                        wait / 60) + ' minutes...')
                                time.sleep(wait)
                        # sleep after one follow (from 10s to 15s)
                        wait = random.randint(6, 15)
                        time.sleep(wait)
                    if flag:
                        if random.randint(1, 100) > 5:
                            # sleep after liking cycle (from 1min to 3min)
                            wait = random.randint(1, 3) * 60
                            self.logger.log('[%s] Finished liking and following cycle. Sleeping for ' % (
                                datetime.datetime.now().strftime("%d.%m.%Y %H:%M")) + str(
                                int(wait / 60)) + ' minutes...')
                            time.sleep(wait)
                        else:
                            # sleep longer after 5% of cycles (from 3min to 7 min)
                            wait = random.randint(3, 7) * 60
                            self.logger.log('[%s] Coffee time! Will be back in ' % (
                                datetime.datetime.now().strftime("%d.%m.%Y %H:%M")) + str(
                                int(wait / 60)) + ' minutes...')
                            time.sleep(wait)
            if (not flag):
                wait = 4 * 60 * 60
                time.sleep(wait)
                flag = True
                likes = 0
                perseverance = 0
                patience = 4
                follows = 0

    def run_unfollow(self, login, password, to_unfollows_counter):
        unfollows = 0
        perseverance = 0
        patience = 4
        flag = True
        while flag:
            self.logger.log('Finding all followings ')
            if not self.session.login_status:
                self.session.login()
            users_to_unfollow_queue = self.get_users_to_unfollow(to_unfollows_counter)
            # self.logger.log('users_to_unfollow: #' + str(users_to_unfollow_queue))
            while len(users_to_unfollow_queue) > 0:
                self.logger.log('There are ' + str(len(users_to_unfollow_queue)) + ' users in the unfollow queue')
                if len(users_to_unfollow_queue) > 14:
                    unfollow_per_cycle = self.iround(min(20, max(0, random.gauss(10,
                                                                                 2))))  # gaussian distribution: mu = 10, sig = 2, round to nearest int
                else:
                    unfollow_per_cycle = len(users_to_unfollow_queue)
                unfollow_next, users_to_unfollow_queue = users_to_unfollow_queue[
                                                         :unfollow_per_cycle], users_to_unfollow_queue[
                                                                               unfollow_per_cycle:]
                self.logger.log('Unfollow ' + str(unfollow_per_cycle) + ' users now...')
                for user_id in unfollow_next:
                    status = self.unfollow(user_id)
                    if status == 200:
                        self.unfollowed_users.add(user_id)
                        unfollows += 1
                        if unfollows >= self.total_unfollows:
                            self.logger.log(
                                '[%s] Success! Reached total number of unfollows. InstaBot is sleeping for 4hours...' % (
                                    datetime.datetime.now().strftime("%d.%m.%Y %H:%M")))
                            flag = False
                        perseverance = 0
                        self.logger.log('Total unfollows: ' + str(unfollows) + ' / ' + str(self.total_unfollows))
                        if not flag:
                            wait = 4 * 60 * 60
                            time.sleep(wait)
                            flag = True
                            unfollows = 0
                            perseverance = 0
                            patience = 4

                    elif status == 400:
                        perseverance += 1
                        if perseverance < patience - 1:  # the bot knows when patience is more important then perseverance
                            self.logger.log('Error 400 - # ' + str(perseverance))
                        else:
                            wait = random.randint(45, 75) * 60
                            self.logger.log(
                                '[%s] Error 400 - # ' % (datetime.datetime.now().strftime("%d.%m.%Y %H:%M")) + str(
                                    perseverance) + '- You might have been banned. Who knows for sure? InstaBot will chill for ' + str(
                                    wait) + ' minutes...')
                            time.sleep(wait)
                    # sleep after one like (from 10s to 15s)
                    wait = random.randint(10, 20)
                    time.sleep(wait)
                if random.randint(1, 100) > 5:
                    # sleep after liking cycle (from 2min to 5min)
                    wait = random.randint(2, 5) * 60
                    self.logger.log('[%s] Finished unfollowing cycle. Sleeping for ' % (
                        datetime.datetime.now().strftime("%d.%m.%Y %H:%M")) + str(int(wait / 60)) + ' minutes... ')
                    time.sleep(wait)
                else:
                    # sleep longer after 5% of cycles (from 3min to 8 min)
                    wait = random.randint(3, 8) * 60
                    self.logger.log('[%s] Coffee time! Will be back in ' % (
                        datetime.datetime.now().strftime("%d.%m.%Y %H:%M")) + str(int(wait / 60)) + ' minutes...')
                    time.sleep(wait)

    def username_checker(self, user_name, user_id):
        for index in range(len(self.unwanted_username_list)):
            if self.unwanted_username_list[index] == user_name:
                print('Username = ' + user_name + '\n      ID = ' +
                      user_id + '      <<< rejected ' +
                      self.unwanted_username_list[index] + ' is found!!!')
                return 0
            else:
                return 1


if __name__ == "__main__":
    try:
        InstaBot('config/config.yml', sys.argv[1])
    except IndexError:
        InstaBot('config/config.yml')
