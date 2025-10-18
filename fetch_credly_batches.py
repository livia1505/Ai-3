from playwright.sync_api import sync_playwright

def fetch_credly_badges(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # headless=False if you want to see the browser
        page = browser.new_page()
        page.goto(url)

        # Wait for badge container to load
        page.wait_for_selector("span.EarnedBadgeCardstyles__BadgeNameText-fredly__sc-gsqjwh-7", timeout=30000)

        badges = page.query_selector_all("div.EarnedBadgeCardstyles__Container-fredly__sc-gsqjwh-1")
        badge_data = []

        for badge in badges:
            title_el = badge.query_selector("span.EarnedBadgeCardstyles__BadgeNameText-fredly__sc-gsqjwh-7")
            date_el = badge.query_selector("span.EarnedBadgeCardstyles__ExpirationDateText-fredly__sc-gsqjwh-8")

            title = title_el.inner_text().strip() if title_el else "Unknown"
            date = date_el.inner_text().strip() if date_el else "No expiration"
            badge_data.append({"title": title, "date": date})

        browser.close()
        return badge_data

if __name__ == "__main__":
    url = input("Enter Credly profile URL: ").strip()
    badges = fetch_credly_badges(url)
    for idx, badge in enumerate(badges, 1):
        print(f"{idx}. {badge['title']} (Expires: {badge['date']})")
