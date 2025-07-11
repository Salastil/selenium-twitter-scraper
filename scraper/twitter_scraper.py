import os
import sys
import pandas as pd
from progress import Progress
from scroller import Scroller
from tweet import Tweet

from datetime import datetime
from fake_headers import Headers
from time import sleep

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
	NoSuchElementException,
	StaleElementReferenceException,
	WebDriverException,
)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService

from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService

from selenium.webdriver.support.ui import WebDriverWait

from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager

TWITTER_LOGIN_URL = "https://twitter.com/i/flow/login"


class Twitter_Scraper:
	def __init__(
		self,
		mail,
		username,
		password,
		headlessState,
		max_tweets=50,
		scrape_username=None,
		scrape_hashtag=None,
		scrape_query=None,
		scrape_bookmarks=False,
		scrape_poster_details=False,
		scrape_latest=True,
		scrape_top=False,
		proxy=None,
	):
		print("Initializing Twitter Scraper...")
		self.mail = mail
		self.username = username
		self.password = password
		self.headlessState = headlessState
		self.interrupted = False
		self.tweet_ids = set()
		self.data = []
		self.tweet_cards = []
		self.scraper_details = {
			"type": None,
			"username": None,
			"hashtag": None,
			"bookmarks": False,
			"query": None,
			"tab": None,
			"poster_details": False,
		}
		self.max_tweets = max_tweets
		self.progress = Progress(0, max_tweets)
		self.router = self.go_to_home
		self.driver = self._get_driver(proxy)
		self.actions = ActionChains(self.driver)
		self.scroller = Scroller(self.driver)
		self._config_scraper(
			max_tweets,
			scrape_username,
			scrape_hashtag,
			scrape_bookmarks,
			scrape_query,
			scrape_latest,
			scrape_top,
			scrape_poster_details,
		)

	def _config_scraper(
		self,
		max_tweets=50,
		scrape_username=None,
		scrape_hashtag=None,
		scrape_bookmarks=False,
		scrape_query=None,
		scrape_list=None,
		scrape_latest=True,
		scrape_top=False,
		scrape_poster_details=False,
	):
		self.tweet_ids = set()
		self.data = []
		self.tweet_cards = []
		self.max_tweets = max_tweets
		self.progress = Progress(0, max_tweets)
		self.scraper_details = {
			"type": None,
			"username": scrape_username,
			"hashtag": str(scrape_hashtag).replace("#", "")
			if scrape_hashtag is not None
			else None,
			"bookmarks": scrape_bookmarks,
			"query": scrape_query,
			"list": scrape_list,
			"tab": "Latest" if scrape_latest else "Top" if scrape_top else "Latest",
			"poster_details": scrape_poster_details,
		}
		self.router = self.go_to_home
		self.scroller = Scroller(self.driver)

		if scrape_username is not None:
			self.scraper_details["type"] = "Username"
			self.router = self.go_to_profile
		elif scrape_hashtag is not None:
			self.scraper_details["type"] = "Hashtag"
			self.router = self.go_to_hashtag
		elif scrape_bookmarks is not False:
			self.scraper_details["type"] = "Bookmarks"
			self.router = self.go_to_bookmarks
		elif scrape_query is not None:
			self.scraper_details["type"] = "Query"
			self.router = self.go_to_search
		elif scrape_list is not None:
			self.scraper_details["type"] = "List"
			self.router = self.go_to_list
		else:
			self.scraper_details["type"] = "Home"
			self.router = self.go_to_home
		pass
	
	def _get_driver(self, proxy=None):
		print("Setup WebDriver...")

		header = (
			"Mozilla/5.0 (Linux; Android 11; SM-G998B) "
			"AppleWebKit/537.36 (KHTML, like Gecko) "
			"Chrome/109.0.5414.87 Mobile Safari/537.36"
		)

		def create_firefox_driver():
			firefox_options = FirefoxOptions()
			firefox_options.add_argument("--no-sandbox")
			firefox_options.add_argument("--disable-dev-shm-usage")
			firefox_options.add_argument("--ignore-certificate-errors")
			firefox_options.add_argument("--disable-gpu")
			firefox_options.add_argument("--log-level=3")
			firefox_options.add_argument("--disable-notifications")
			firefox_options.add_argument("--disable-popup-blocking")
			firefox_options.add_argument(f"--user-agent={header}")
			if proxy:
				firefox_options.add_argument(f"--proxy-server={proxy}")
			if self.headlessState in ["yes", "true"]:
				firefox_options.add_argument("--headless")

			# Fix Invalid Host header: force IPv4
			firefox_options.set_preference("network.dns.disableIPv6", True)

			print("Initializing FirefoxDriver with system binary...")
			firefoxdriver_path = "/usr/bin/geckodriver"  # Native geckodriver
			firefox_service = FirefoxService(executable_path=firefoxdriver_path)

			driver = webdriver.Firefox(service=firefox_service, options=firefox_options)
			print("Firefox WebDriver Setup Complete")
			return driver

		def create_chrome_driver():
			chrome_options = ChromeOptions()
			chrome_options.add_argument("--no-sandbox")
			chrome_options.add_argument("--disable-dev-shm-usage")
			chrome_options.add_argument("--ignore-certificate-errors")
			chrome_options.add_argument("--disable-gpu")
			chrome_options.add_argument("--log-level=3")
			chrome_options.add_argument("--disable-notifications")
			chrome_options.add_argument("--disable-popup-blocking")
			chrome_options.add_argument(f"--user-agent={header}")

			# Use Arch Chromium binary
			chrome_options.binary_location = "/usr/sbin/chromium"

			if proxy:
				chrome_options.add_argument(f"--proxy-server={proxy}")
			if self.headlessState in ["yes", "true"]:
				chrome_options.add_argument("--headless")

			print("Initializing ChromeDriver with system binary...")
			chromedriver_path = "/usr/bin/chromedriver" # Native chromedriver
			chrome_service = ChromeService(executable_path=chromedriver_path)

			driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
			print("Chrome WebDriver Setup Complete")
			return driver

		try:
			driver = create_firefox_driver()
			return driver
		except Exception as firefox_error:
			print(f"Firefox WebDriver failed: {firefox_error}")
			print("Attempting Chromium fallback...")
			try:
				driver = create_chrome_driver()
				return driver
			except Exception as chrome_error:
				print(f"Error setting up Chrome WebDriver: {chrome_error}")
				sys.exit(1)
	
	def login(self):
		print()
		print("Logging in to Twitter...")

		try:
			self.driver.maximize_window()
			self.driver.execute_script("document.body.style.zoom='150%'") #set zoom to 150%
			self.driver.get(TWITTER_LOGIN_URL)
			sleep(3)

			self._input_username()
			self._input_password()
			self._input_unusual_activity()

			cookies = self.driver.get_cookies()

			auth_token = None

			for cookie in cookies:
				if cookie["name"] == "auth_token":
					auth_token = cookie["value"]
					break

			if auth_token is None:
				raise ValueError(
					"""This may be due to the following:

- Internet connection is unstable
- Username is incorrect
- Password is incorrect
"""
				)

			print()
			print("Login Successful")
			print()
		except Exception as e:
			print()
			print(f"Login Failed: {e}")
			sys.exit(1)

		pass

	def _input_username(self):
		input_attempt = 0

		while True:
			try:
				username = self.driver.find_element(
					"xpath", "//input[@autocomplete='username']"
				)

				username.send_keys(self.username)
				username.send_keys(Keys.RETURN)
				sleep(3)
				break
			except NoSuchElementException:
				input_attempt += 1
				if input_attempt >= 3:
					print()
					print(
						"""There was an error inputting the username.

It may be due to the following:
- Internet connection is unstable
- Username is incorrect
- Twitter is experiencing unusual activity"""
					)
					self.driver.quit()
					sys.exit(1)
				else:
					print("Re-attempting to input username...")
					sleep(2)

	def _input_unusual_activity(self):
		input_attempt = 0

		while True:
			try:
				unusual_activity = self.driver.find_element(
					"xpath", "//input[@data-testid='ocfEnterTextTextInput']"
				)            
				# Prompt for 2FA code input
				two_fa_code = input("Enter 2FA code: ").strip()            
				unusual_activity.send_keys(two_fa_code)
				unusual_activity.send_keys(Keys.RETURN)
				sleep(3)
				break
			except NoSuchElementException:
				input_attempt += 1
				if input_attempt >= 3:
					break

	def _input_password(self):
		input_attempt = 0

		while True:
			try:
				password = self.driver.find_element(
					"xpath", "//input[@autocomplete='current-password']"
				)

				password.send_keys(self.password)
				password.send_keys(Keys.RETURN)
				sleep(3)
				break
			except NoSuchElementException:
				input_attempt += 1
				if input_attempt >= 3:
					print()
					print(
						"""There was an error inputting the password.

It may be due to the following:
- Internet connection is unstable
- Password is incorrect
- Twitter is experiencing unusual activity"""
					)
					self.driver.quit()
					sys.exit(1)
				else:
					print("Re-attempting to input password...")
					sleep(2)

	def go_to_home(self):
		self.driver.get("https://twitter.com/home")
		sleep(3)
		pass

	def go_to_profile(self):
		if (
			self.scraper_details["username"] is None
			or self.scraper_details["username"] == ""
		):
			print("Username is not set.")
			sys.exit(1)
		else:
			self.driver.get(f"https://twitter.com/{self.scraper_details['username']}")
			sleep(3)
		pass

	def go_to_hashtag(self):
		if (
			self.scraper_details["hashtag"] is None
			or self.scraper_details["hashtag"] == ""
		):
			print("Hashtag is not set.")
			sys.exit(1)
		else:
			url = f"https://twitter.com/hashtag/{self.scraper_details['hashtag']}?src=hashtag_click"
			if self.scraper_details["tab"] == "Latest":
				url += "&f=live"

			self.driver.get(url)
			sleep(3)
		pass

	def go_to_bookmarks(self):
		if (
			self.scraper_details["bookmarks"] is False
			or self.scraper_details["bookmarks"] == ""
		):
			print("Bookmarks is not set.")
			sys.exit(1)
		else:
			url = f"https://twitter..com/i/bookmarks"

			self.driver.get(url)
			sleep(3)
		pass

	def go_to_search(self):
		if self.scraper_details["query"] is None or self.scraper_details["query"] == "":
			print("Query is not set.")
			sys.exit(1)
		else:
			url = f"https://twitter.com/search?q={self.scraper_details['query']}&src=typed_query"
			if self.scraper_details["tab"] == "Latest":
				url += "&f=live"

			self.driver.get(url)
			sleep(3)
		pass

	def go_to_list(self):
		if self.scraper_details["list"] is None or self.scraper_details["list"] == "":
			print("List is not set.")
			sys.exit(1)
		else:
			url = f"https://x.com/i/lists/{self.scraper_details['list']}"
			self.driver.get(url)
			sleep(3)
		pass

	def get_tweet_cards(self):
		self.tweet_cards = self.driver.find_elements(
			"xpath", '//article[@data-testid="tweet" and not(@disabled)]'
		)
		pass

	def remove_hidden_cards(self):
		try:
			hidden_cards = self.driver.find_elements(
				"xpath", '//article[@data-testid="tweet" and @disabled]'
			)

			for card in hidden_cards[1:-2]:
				self.driver.execute_script(
					"arguments[0].parentNode.parentNode.parentNode.remove();", card
				)
		except Exception as e:
			return
		pass

	def scrape_tweets(
		self,
		max_tweets=50,
		no_tweets_limit=False,
		scrape_username=None,
		scrape_hashtag=None,
		scrape_bookmarks=False,
		scrape_query=None,
		scrape_list=None,
		scrape_latest=True,
		scrape_top=False,
		scrape_poster_details=False,
		router=None,
	):
		self._config_scraper(
			max_tweets,
			scrape_username,
			scrape_hashtag,
			scrape_bookmarks,
			scrape_query,
			scrape_list,
			scrape_latest,
			scrape_top,
			scrape_poster_details,
		)

		if router is None:
			router = self.router

		router()

		if self.scraper_details["type"] == "Username":
			print(
				"Scraping Tweets from @{}...".format(self.scraper_details["username"])
			)
		elif self.scraper_details["type"] == "Hashtag":
			print(
				"Scraping {} Tweets from #{}...".format(
					self.scraper_details["tab"], self.scraper_details["hashtag"]
				)
			)
		elif self.scraper_details["type"] == "Bookmarks":
			print(
				"Scraping Tweets from bookmarks...".format(self.scraper_details["username"]))
		elif self.scraper_details["type"] == "Query":
			print(
				"Scraping {} Tweets from {} search...".format(
					self.scraper_details["tab"], self.scraper_details["query"]
				)
			)
		elif self.scraper_details["type"] == "Home":
			print("Scraping Tweets from Home...")

		# Accept cookies to make the banner disappear
		try:
			accept_cookies_btn = self.driver.find_element(
			"xpath", "//span[text()='Refuse non-essential cookies']/../../..")
			accept_cookies_btn.click()
		except NoSuchElementException:
			pass

		self.progress.print_progress(0, False, 0, no_tweets_limit)

		refresh_count = 0
		added_tweets = 0
		empty_count = 0
		retry_cnt = 0

		while self.scroller.scrolling:
			try:
				self.get_tweet_cards()
				added_tweets = 0

				for card in self.tweet_cards[-15:]:
					try:
						tweet_id = str(card)

						if tweet_id not in self.tweet_ids:
							self.tweet_ids.add(tweet_id)

							if not self.scraper_details["poster_details"]:
								self.driver.execute_script(
									"arguments[0].scrollIntoView();", card
								)

							tweet = Tweet(
								card=card,
								driver=self.driver,
								actions=self.actions,
								scrape_poster_details=self.scraper_details[
									"poster_details"
								],
							)

							if tweet:
								if not tweet.error and tweet.tweet is not None:
									if not tweet.is_ad:
										self.data.append(tweet.tweet)
										added_tweets += 1
										self.progress.print_progress(len(self.data), False, 0, no_tweets_limit)

										if len(self.data) >= self.max_tweets and not no_tweets_limit:
											self.scroller.scrolling = False
											break
									else:
										continue
								else:
									continue
							else:
								continue
						else:
							continue
					except NoSuchElementException:
						continue

				if len(self.data) >= self.max_tweets and not no_tweets_limit:
					break

				if added_tweets == 0:
					# Check if there is a button "Retry" and click on it with a regular basis until a certain amount of tries
					try:
						while retry_cnt < 15:
							retry_button = self.driver.find_element(
							"xpath", "//span[text()='Retry']/../../..")
							self.progress.print_progress(len(self.data), True, retry_cnt, no_tweets_limit)
							sleep(600)
							retry_button.click()
							retry_cnt += 1
							sleep(2)
					# There is no Retry button so the counter is reseted
					except NoSuchElementException:
						retry_cnt = 0
						self.progress.print_progress(len(self.data), False, 0, no_tweets_limit)

					if empty_count >= 5:
						if refresh_count >= 3:
							print()
							print("No more tweets to scrape")
							break
						refresh_count += 1
					empty_count += 1
					sleep(1)
				else:
					empty_count = 0
					refresh_count = 0
			except StaleElementReferenceException:
				sleep(2)
				continue
			except KeyboardInterrupt:
				print("\n")
				print("Keyboard Interrupt")
				self.interrupted = True
				break
			except Exception as e:
				print("\n")
				print(f"Error scraping tweets: {e}")
				break

		print("")

		if len(self.data) >= self.max_tweets or no_tweets_limit:
			print("Scraping Complete")
		else:
			print("Scraping Incomplete")

		if not no_tweets_limit:
			print("Tweets: {} out of {}\n".format(len(self.data), self.max_tweets))

		pass

	def save_to_csv(self):
		print("Saving Tweets to CSV...")
		now = datetime.now()
		folder_path = "./tweets/"

		if not os.path.exists(folder_path):
			os.makedirs(folder_path)
			print("Created Folder: {}".format(folder_path))

		data = {
			"Name": [tweet[0] for tweet in self.data],
			"Handle": [tweet[1] for tweet in self.data],
			"Timestamp": [tweet[2] for tweet in self.data],
			"Verified": [tweet[3] for tweet in self.data],
			"Content": [tweet[4] for tweet in self.data],
			"Comments": [tweet[5] for tweet in self.data],
			"Retweets": [tweet[6] for tweet in self.data],
			"Likes": [tweet[7] for tweet in self.data],
			"Analytics": [tweet[8] for tweet in self.data],
			"Tags": [tweet[9] for tweet in self.data],
			"Mentions": [tweet[10] for tweet in self.data],
			"Emojis": [tweet[11] for tweet in self.data],
			"Profile Image": [tweet[12] for tweet in self.data],
			"Tweet Link": [tweet[13] for tweet in self.data],
			"Tweet ID": [f"tweet_id:{tweet[14]}" for tweet in self.data],
		}

		if self.scraper_details["poster_details"]:
			data["Tweeter ID"] = [f"user_id:{tweet[15]}" for tweet in self.data]
			data["Following"] = [tweet[16] for tweet in self.data]
			data["Followers"] = [tweet[17] for tweet in self.data]

		df = pd.DataFrame(data)

		current_time = now.strftime("%Y-%m-%d_%H-%M-%S")
		file_path = f"{folder_path}{current_time}_tweets_1-{len(self.data)}.csv"
		pd.set_option("display.max_colwidth", None)
		df.to_csv(file_path, index=False, encoding="utf-8")

		print("CSV Saved: {}".format(file_path))

		pass

	def get_tweets(self):
		return self.data
