import time
import requests
import json
import os
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import ddddocr

TELE_TOKEN = os.environ.get('TELE_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
IUH_USERNAME = os.environ.get('IUH_USERNAME')
IUH_PASS = os.environ.get('IUH_PASS')

HISTORY_FILE = 'sent_posts.json'
DELAY_TIME = 300 

def load_history():
    """Đọc các ID hoạt động đã gửi từ file JSON"""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    return []

def save_history(event_id):
    """Lưu ID hoạt động mới vào file JSON"""
    history = load_history()
    if event_id not in history:
        history.append(event_id)
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f)

def send_telegram(message_text):
    url = f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message_text,
        "parse_mode": "HTML"
    }
    try: 
        requests.post(url, json=payload)
        print(f"[+] Đã gửi Telegram thành công!")
    except Exception as e:
        print(f"[-] Lỗi gửi Telegram: {e}")

def solve_captcha(driver):
    captcha_img = driver.find_element(By.ID, "captcha")
    captcha_img.screenshot("captcha.png")
    
    ocr = ddddocr.DdddOcr(show_ad=False)
    with open("captcha.png", 'rb') as f:
        image_bytes = f.read()
        
    captcha_text = ocr.classification(image_bytes)
    print(f"✨ AI ddddocr đọc được Captcha là: '{captcha_text}'")
    return captcha_text

def main():
    """Hàm thực thi 1 chu kỳ cào dữ liệu"""
    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Bắt đầu phiên cào dữ liệu mới...")
    
    options = uc.ChromeOptions()
    options.add_argument('--headless') 
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    driver = uc.Chrome(options=options)
    
    try:
        driver.get("https://doantn.iuh.edu.vn/login.html")
        time.sleep(2)

        while ("doanvien.html" not in driver.current_url):
            driver.find_element(By.ID, "mssv").clear()
            driver.find_element(By.ID, "password").clear()
            driver.find_element(By.ID, "security_code").clear()

            driver.find_element(By.ID, "mssv").send_keys(IUH_USERNAME)
            driver.find_element(By.ID, "password").send_keys(IUH_PASS)
            
            captcha_text = solve_captcha(driver)
            driver.find_element(By.ID, "security_code").send_keys(captcha_text)
            driver.find_element(By.NAME, "btLogin").click()
            time.sleep(3)

        print("🔓 Đăng nhập thành công, đang đọc dữ liệu...")
        time.sleep(3)

        html_content = driver.page_source
        soup = BeautifulSoup(html_content, "html.parser")
        table = soup.find("table", class_="tblDoanvien")
        
        if table:
            sent_posts = load_history()
            new_events_found = False
            rows = table.find("tbody").find_all("tr")
            
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 6:
                    title_tag = cols[1].find("a")
                    title = title_tag.text.strip() if title_tag else "Không có tiêu đề"
                    event_id = title_tag.get("data-target", "") if title_tag else ""
                    date = cols[4].text.strip()
                    status = cols[5].text.strip()
                    
                    if event_id and (event_id not in sent_posts):
                        new_events_found = True
                        msg = (
                            f"📢 <b>HOẠT ĐỘNG MỚI</b>\n"
                            f"📌 <b>Tên:</b> {title}\n"
                            f"📅 <b>Thời gian:</b> {date}\n"
                            f"📊 <b>Trạng thái:</b> {status}"
                        )
                        send_telegram(msg)
                        save_history(event_id)
            
            if not new_events_found:
                print("💤 Không có hoạt động nào mới.")
        else: 
            print("❌ Không tìm thấy bảng dữ liệu class 'tblDoanvien'.")

    except Exception as e:
        print(f"❌ Có lỗi xảy ra: {e}")
    finally:
        driver.quit()
        print("🛑 Đóng trình duyệt.")



if __name__ == "__main__":
    main()