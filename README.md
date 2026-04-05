# Telegram Bidirectional Bridge / پل دوطرفه تلگرام

## English

### What does this app do?
This application provides a simple GUI for connecting to Telegram using **Telethon**.

Its main purpose is to create a **bidirectional message bridge** between two Telegram chats.

Features:
- Sign in using **API ID**, **API Hash**, and phone number
- Supports **login code** and **2FA password**
- Loads only the **first 20 chats**
- Lets you select two chats using a graphical interface
- Transfers messages **both ways** between the selected chats
- Supports text messages and optionally media
- Includes retry logic for this response:
  - `⚠️ از کیبورد ربات استفاده کنید`
  - When detected, the app sends `📨 انتقال پیام به بله`
  - Waits a few seconds
  - Sends the original message again

---

### Requirements
Before running the app, make sure you have:
- Windows
- Python 3.10 or newer
- Internet access
- Telegram API ID and API Hash

To get API credentials:
1. Open the Telegram developer portal.
2. Create an application.
3. Copy your `api_id` and `api_hash`.

---

### Installation
Run this command inside the project folder:

```bash
pip install telethon
```

If you are using the GUI version with tkinter, it is usually included with Python on Windows.

---

### Run the app
Start the script with:

```bash
python telegram-forwarder.py
```

---

### Step-by-step usage
#### 1) Launch the program
After running the script, the GUI window will open.

#### 2) Enter your account information
In the Authentication section, fill in:
- API ID
- API Hash
- Phone Number

Then click **Connect / Send Code**.

#### 3) Enter the login code
Telegram will send you a login code.
Enter it in the **Code** field and click **Verify Code**.

#### 4) If 2FA is enabled
If your account has two-step verification enabled, enter your password in the **2FA Password** field and click **Verify Password**.

#### 5) Load chats
After successful login, click **Load Top 20 Chats**.
The app loads the first 20 chats only once and keeps them cached.

#### 6) Select two chats
From the dropdown lists, select:
- one chat as **Chat A**
- another chat as **Chat B**

#### 7) Start the bridge
Click **Start Bridge**.
From that point on, new messages will be transferred in both directions between the selected chats.

#### 8) Stop the bridge
Click **Stop Bridge** to stop forwarding.

---

### credentials.txt
The program stores the following values in `credentials.txt`:
- API ID
- API Hash
- Phone Number

This makes future runs easier because you do not need to enter them again.

---

### Build a standalone exe
To build an exe version:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --clean --name telegram-forwarder telegram-forwarder.py
```

The final file will be created here:

```bash
dist\telegram-forwarder.exe
```

---

### Important notes
- This tool works with your personal Telegram account.
- If Telegram detects unusual account behavior, usage responsibility is yours.
- It is best to test the app first with two test chats.
- If the destination requires actual bot keyboard interaction, the fallback logic only handles the text-based retry workflow.

---

### Quick troubleshooting
#### The login code does not work
- Make sure the phone number format is correct.
- Verify that your API ID and API Hash are correct.

#### Chats do not load
- Make sure login was completed successfully.
- Check your internet connection.

#### The exe does not run
- Build once without `--windowed` to inspect errors.
- Make sure all dependencies are installed.



---


## فارسی

### این برنامه چه کاری انجام می‌دهد؟
این برنامه یک رابط گرافیکی ساده برای اتصال به تلگرام با استفاده از **Telethon** فراهم می‌کند.

کار اصلی برنامه این است که بین دو چت تلگرام، **انتقال پیام دوطرفه** انجام دهد.

ویژگی‌ها:
- ورود به حساب تلگرام با **API ID**، **API Hash** و شماره موبایل
- پشتیبانی از **کد ورود** و **رمز دومرحله‌ای**
- بارگذاری فقط **۲۰ چت اول**
- انتخاب دو چت از طریق رابط گرافیکی
- انتقال **دوطرفه** پیام‌ها بین دو چت انتخاب‌شده
- پشتیبانی از پیام متنی و در صورت نیاز مدیا
- منطق مقاوم برای پیام:
  - `⚠️ از کیبورد ربات استفاده کنید`
  - در این حالت برنامه پیام `📨 انتقال پیام به بله` را می‌فرستد
  - چند ثانیه صبر می‌کند
  - سپس پیام اصلی را دوباره ارسال می‌کند

---

### پیش‌نیازها
قبل از اجرا، این موارد باید روی سیستم شما نصب باشند:
- Windows
- Python 3.10 یا بالاتر
- اینترنت فعال
- API ID و API Hash از سایت تلگرام

برای گرفتن API ID و API Hash:
1. وارد سایت توسعه‌دهندگان تلگرام شوید.
2. یک اپلیکیشن بسازید.
3. مقادیر `api_id` و `api_hash` را بردارید.

---

### نصب
در پوشه پروژه این دستور را اجرا کنید:

```bash
pip install telethon
```

اگر از نسخه GUI با tkinter استفاده می‌کنید، معمولاً `tkinter` روی ویندوز همراه پایتون نصب است.

---

### اجرای برنامه
فایل اسکریپت را اجرا کنید:

```bash
python telegram-forwarder.py
```

---

### راهنمای استفاده مرحله‌به‌مرحله
#### 1) اجرای برنامه
بعد از اجرا، پنجره گرافیکی برنامه باز می‌شود.

#### 2) وارد کردن اطلاعات حساب
در بخش Authentication این موارد را وارد کنید:
- API ID
- API Hash
- Phone Number

سپس روی **Connect / Send Code** بزنید.

#### 3) وارد کردن کد ورود
تلگرام یک کد برای شما می‌فرستد.
کد را در فیلد **Code** وارد کنید و روی **Verify Code** بزنید.

#### 4) اگر تایید دومرحله‌ای فعال بود
اگر رمز دومرحله‌ای فعال باشد، برنامه از شما رمز می‌خواهد.
آن را در فیلد **2FA Password** وارد کنید و روی **Verify Password** بزنید.

#### 5) بارگذاری چت‌ها
بعد از ورود موفق، روی **Load Top 20 Chats** بزنید.
برنامه فقط ۲۰ چت اول را یک‌بار لود می‌کند و در حافظه نگه می‌دارد.

#### 6) انتخاب دو چت
از لیست‌های کشویی:
- یک چت را به عنوان **Chat A**
- یک چت دیگر را به عنوان **Chat B**

انتخاب کنید.

#### 7) شروع پل دوطرفه
روی **Start Bridge** بزنید.
از این لحظه، پیام‌های جدید بین دو چت به‌صورت دوطرفه منتقل می‌شوند.

#### 8) توقف برنامه
برای توقف انتقال پیام، روی **Stop Bridge** بزنید.

---

### فایل credentials.txt
برنامه اطلاعات زیر را در فایل `credentials.txt` ذخیره می‌کند:
- API ID
- API Hash
- Phone Number

این کار باعث می‌شود دفعه بعد لازم نباشد دوباره آن‌ها را وارد کنید.

---

### ساخت فایل exe
برای ساخت نسخه مستقل exe:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --clean --name telegram-forwarder telegram-forwarder.py
```

فایل نهایی در این مسیر ساخته می‌شود:

```bash
dist\telegram-forwarder.exe
```

---

### نکات مهم
- این ابزار با حساب شخصی تلگرام شما کار می‌کند.
- اگر تلگرام محدودیت یا حساسیت روی رفتار اکانت تشخیص دهد، مسئولیت استفاده با خود شماست.
- بهتر است قبل از استفاده واقعی، برنامه را روی دو چت تستی امتحان کنید.
- اگر پیام مقصد نیاز به تعامل با دکمه‌های ربات داشته باشد، منطق fallback فقط در حد پیام متنی عمل می‌کند.

---

### عیب‌یابی سریع
#### برنامه کد ورود را قبول نمی‌کند
- شماره موبایل را با فرمت درست وارد کنید.
- مطمئن شوید API ID و API Hash صحیح هستند.

#### چت‌ها لود نمی‌شوند
- مطمئن شوید ورود با موفقیت انجام شده است.
- اتصال اینترنت را بررسی کنید.

#### exe اجرا نمی‌شود
- یک بار بدون `--windowed` build بگیرید تا خطا را ببینید.
- مطمئن شوید همه dependencyها نصب هستند.


