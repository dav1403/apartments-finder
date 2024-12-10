import asyncio
import telegram
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

from apartments_finder.apartment_post_enricher import ApartmentPostEnricher
from apartments_finder.apartment_post_filter import ApartmentPostFilterer
from apartments_finder.apartments_scraper import FacebookGroupsScraper, ApartmentsScraper
from apartments_finder.config import config
from apartments_finder.exceptions import EnrichApartmentPostError
from apartments_finder.logger import logger

# Setup Telegram bot
bot = telegram.Bot(config.TELEGRAM_BOT_API_KEY)

# Handle Facebook login with Selenium
def facebook_login():
    """
    Log into Facebook using Selenium with 2FA backup codes.
    """
    print("Setting up WebDriver...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run headless for GitHub Actions
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    service = Service("/usr/local/bin/chromedriver")  # Explicit path to ChromeDriver
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        print("Navigating to Facebook login page...")
        driver.get("https://www.facebook.com/login")

        # Enter username
        print("Entering username...")
        email_field = driver.find_element(By.ID, "email")
        email_field.send_keys(config.FACEBOOK_USERNAME)

        # Enter password
        print("Entering password...")
        password_field = driver.find_element(By.ID, "pass")
        password_field.send_keys(config.FACEBOOK_PASSWORD)
        password_field.send_keys(Keys.RETURN)

        # Handle 2FA using backup codes
        try:
            print("Waiting for 2FA prompt...")
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//input[@id='approvals_code']"))
            )
            print("2FA prompt detected. Using backup code...")

            # Enter the first available backup code
            backup_codes = config.FACEBOOK_BACKUP_CODES.split(',')
            code_field = driver.find_element(By.ID, "approvals_code")
            code_field.send_keys(backup_codes[0])  # Use the first backup code
            code_field.send_keys(Keys.RETURN)
            print("Backup code submitted.")
        except Exception as e:
            print("Error during 2FA handling:", e)
            raise

        # Wait for Facebook homepage to load
        WebDriverWait(driver, 20).until(
            EC.url_contains("https://www.facebook.com/")
        )
        print("Login successful!")

    except Exception as e:
        print("Error during Facebook login:", e)
        driver.quit()
        raise

    return driver


# Initialize the apartments scraper with Facebook credentials
apartment_scraper: ApartmentsScraper = FacebookGroupsScraper(
    config.FACEBOOK_USERNAME,
    config.FACEBOOK_PASSWORD,
    config.FACEBOOK_GROUPS,
    config.POSTS_PER_GROUP_LIMIT,
    config.TOTAL_POSTS_LIMIT
)
apartment_post_parser = ApartmentPostEnricher()
apartment_post_filterer = ApartmentPostFilterer()


async def main():
    enriched_posts = 0

    # Perform Facebook login
    facebook_login()

    try:
        apartment_posts_iter = apartment_scraper.get_apartments()

        async for apartment_post in apartment_posts_iter:
            if enriched_posts >= config.MAX_POSTS_TO_ENRICH_IN_RUN:
                logger.info("Enriched posts limit has been exceeded. Stopping run...")
                break

            if await apartment_post_filterer.should_ignore_post(apartment_post, config.POST_FILTERS):
                logger.info("Post should be ignored. Skipping it...")
                continue

            try:
                apartment_post = await apartment_post_parser.enrich(apartment_post)
                enriched_posts += 1

                logger.info("Successfully enriched this apartment with more data.")
            except EnrichApartmentPostError:
                logger.info("Could not enrich data from post. Skipping post...")
                continue

            if not await apartment_post_filterer.is_match(apartment_post, config.APARTMENT_FILTERS):
                logger.info("Apartment post did not match any filter. Skipping it.")
                continue

            logger.info("Successfully matched this apartment with one of the filters.")

            apartment_post_text = await apartment_post.to_telegram_msg()
            await bot.send_message(
                text=apartment_post_text,
                chat_id=config.TELEGRAM_BOT_APARTMENTS_GROUP_CHAT_ID,
            )

            logger.info("Successfully sent this apartment to the telegram bot.")

    except Exception:  # pylint: disable=W0718
        logger.exception("Unexpected error - stopping execution...")

    if config.TELEGRAM_BOT_APARTMENTS_LOGS_GROUP_CHAT_ID:
        with open("../app.log", 'rb') as f:
            await bot.send_document(
                chat_id=config.TELEGRAM_BOT_APARTMENTS_LOGS_GROUP_CHAT_ID,
                document=f
            )


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
