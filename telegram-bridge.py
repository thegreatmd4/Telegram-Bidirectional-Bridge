import asyncio
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from telethon import TelegramClient, events, errors


CREDENTIALS_FILE = "credentials.txt"
SESSION_PREFIX = "session_"
MAX_DIALOGS_TO_SHOW = 20

ROBOT_KEYBOARD_WARNING = "⚠️ از کیبورد ربات استفاده کنید"
FALLBACK_TEXT = "📨 انتقال پیام به بله"
RETRY_DELAY_SECONDS = 3


class TelethonBackend:
    def __init__(self, log_callback):
        self.log_callback = log_callback

        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

        self.client = None
        self.api_id = None
        self.api_hash = None
        self.phone_number = None

        self.dialogs_cache = []
        self.bridge_running = False

        self.handler_a = None
        self.handler_b = None
        self.chat_a = None
        self.chat_b = None

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def log(self, text: str):
        if self.log_callback:
            self.log_callback(text)

    def run_async_task(self, coro, on_success=None, on_error=None):
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)

        def waiter():
            try:
                result = future.result()
                if on_success:
                    on_success(result)
            except Exception as e:
                if on_error:
                    on_error(e)
                else:
                    self.log(f"ERROR: {e}")

        threading.Thread(target=waiter, daemon=True).start()

    async def _create_client(self, api_id: int, api_hash: str, phone_number: str):
        self.api_id = int(api_id)
        self.api_hash = api_hash
        self.phone_number = phone_number

        if self.client is not None:
            try:
                await self.client.disconnect()
            except Exception:
                pass

        self.client = TelegramClient(
            f"{SESSION_PREFIX}{self.phone_number}",
            self.api_id,
            self.api_hash,
            loop=self.loop,
        )

        await self.client.connect()

    async def connect_and_request_code(self, api_id: int, api_hash: str, phone_number: str):
        await self._create_client(api_id, api_hash, phone_number)

        if await self.client.is_user_authorized():
            self.log("Already authorized.")
            return {"status": "authorized"}

        await self.client.send_code_request(self.phone_number)
        self.log("Login code sent.")
        return {"status": "code_sent"}

    async def verify_code(self, code: str):
        try:
            await self.client.sign_in(self.phone_number, code)
            self.log("Logged in successfully with code.")
            return {"status": "authorized"}
        except errors.SessionPasswordNeededError:
            self.log("Two-step verification password required.")
            return {"status": "password_required"}

    async def verify_password(self, password: str):
        await self.client.sign_in(password=password)
        self.log("Logged in successfully with password.")
        return {"status": "authorized"}

    async def load_top_dialogs_once(self):
        if not self.client:
            raise RuntimeError("Client is not initialized.")

        if not await self.client.is_user_authorized():
            raise RuntimeError("You must authenticate first.")

        if self.dialogs_cache:
            self.log("Dialogs already loaded. Reusing cached list.")
            return self._serialize_dialogs()

        dialogs = await self.client.get_dialogs(limit=MAX_DIALOGS_TO_SHOW)
        self.dialogs_cache = list(dialogs)

        self.log(f"Loaded top {len(self.dialogs_cache)} dialogs.")
        return self._serialize_dialogs()

    def _serialize_dialogs(self):
        items = []
        for idx, dialog in enumerate(self.dialogs_cache):
            username = getattr(dialog.entity, "username", None)
            entity_type = type(dialog.entity).__name__
            label = f"{idx + 1}. {dialog.title} | {entity_type} | @{username if username else '-'}"
            items.append(label)
        return items

    def get_dialog_by_index(self, index: int):
        if index < 0 or index >= len(self.dialogs_cache):
            raise IndexError("Dialog index out of range.")
        return self.dialogs_cache[index]

    async def send_message_content(self, destination_entity, message):
        if message.media:
            await self.client.send_file(
                destination_entity,
                file=message.media,
                caption=message.text or ""
            )
        elif message.text:
            await self.client.send_message(destination_entity, message.text)

    async def transfer_with_retry_logic(
        self,
        source_name: str,
        destination_name: str,
        destination_entity,
        original_message
    ):
        original_text = original_message.text or ""

        try:
            if original_message.media:
                await self.client.send_file(
                    destination_entity,
                    file=original_message.media,
                    caption=original_text
                )
            elif original_text:
                await self.client.send_message(destination_entity, original_text)
            else:
                return

            self.log(
                f"Transferred: {source_name} -> {destination_name} | "
                f"message_id={original_message.id}"
            )
        except Exception as e:
            self.log(f"Initial transfer failed {source_name} -> {destination_name}: {e}")
            return

        await asyncio.sleep(RETRY_DELAY_SECONDS)

        try:
            replies = await self.client.get_messages(destination_entity, limit=3)
        except Exception as e:
            self.log(f"Could not inspect destination replies: {e}")
            return

        found_warning = False
        for msg in replies:
            if msg and msg.text and ROBOT_KEYBOARD_WARNING in msg.text:
                found_warning = True
                break

        if not found_warning:
            return

        self.log(f"Detected warning in {destination_name}: {ROBOT_KEYBOARD_WARNING}")

        try:
            await self.client.send_message(destination_entity, FALLBACK_TEXT)
            self.log(f"Sent fallback text to {destination_name}: {FALLBACK_TEXT}")
        except Exception as e:
            self.log(f"Failed to send fallback text to {destination_name}: {e}")
            return

        await asyncio.sleep(RETRY_DELAY_SECONDS)

        try:
            await self.send_message_content(destination_entity, original_message)
            self.log(
                f"Retried transfer: {source_name} -> {destination_name} | "
                f"message_id={original_message.id}"
            )
        except Exception as e:
            self.log(f"Retry transfer failed {source_name} -> {destination_name}: {e}")

    async def start_bridge(self, index_a: int, index_b: int):
        if not self.client:
            raise RuntimeError("Client is not initialized.")

        if self.bridge_running:
            raise RuntimeError("Bridge is already running.")

        self.chat_a = self.get_dialog_by_index(index_a)
        self.chat_b = self.get_dialog_by_index(index_b)

        if self.chat_a.id == self.chat_b.id:
            raise RuntimeError("Please choose two different chats.")

        entity_a = self.chat_a.entity
        entity_b = self.chat_b.entity

        async def from_a_to_b(event):
            if event.out:
                return
            await self.transfer_with_retry_logic(
                source_name=self.chat_a.title,
                destination_name=self.chat_b.title,
                destination_entity=entity_b,
                original_message=event.message
            )

        async def from_b_to_a(event):
            if event.out:
                return
            await self.transfer_with_retry_logic(
                source_name=self.chat_b.title,
                destination_name=self.chat_a.title,
                destination_entity=entity_a,
                original_message=event.message
            )

        self.handler_a = from_a_to_b
        self.handler_b = from_b_to_a

        self.client.add_event_handler(self.handler_a, events.NewMessage(chats=entity_a))
        self.client.add_event_handler(self.handler_b, events.NewMessage(chats=entity_b))

        self.bridge_running = True
        self.log(f"Bridge started: '{self.chat_a.title}' <-> '{self.chat_b.title}'")

        return {"status": "started"}

    async def stop_bridge(self):
        if not self.client or not self.bridge_running:
            return {"status": "stopped"}

        try:
            if self.handler_a is not None:
                self.client.remove_event_handler(self.handler_a)
            if self.handler_b is not None:
                self.client.remove_event_handler(self.handler_b)
        finally:
            self.handler_a = None
            self.handler_b = None
            self.bridge_running = False

        self.log("Bridge stopped.")
        return {"status": "stopped"}

    async def shutdown(self):
        try:
            await self.stop_bridge()
        except Exception:
            pass

        if self.client:
            try:
                await self.client.disconnect()
            except Exception:
                pass


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Telegram Bidirectional Bridge")
        self.root.geometry("900x700")

        self.backend = TelethonBackend(self.thread_safe_log)

        self.api_id_var = tk.StringVar()
        self.api_hash_var = tk.StringVar()
        self.phone_var = tk.StringVar()

        self.code_var = tk.StringVar()
        self.password_var = tk.StringVar()

        self.chat_a_var = tk.StringVar()
        self.chat_b_var = tk.StringVar()

        self.dialog_labels = []

        self._build_ui()
        self._load_saved_credentials()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill="both", expand=True)

        auth_frame = ttk.LabelFrame(main, text="Authentication", padding=12)
        auth_frame.pack(fill="x", pady=6)

        ttk.Label(auth_frame, text="API ID").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(auth_frame, textvariable=self.api_id_var, width=30).grid(row=0, column=1, sticky="ew", padx=4, pady=4)

        ttk.Label(auth_frame, text="API Hash").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(auth_frame, textvariable=self.api_hash_var, width=50).grid(row=1, column=1, sticky="ew", padx=4, pady=4)

        ttk.Label(auth_frame, text="Phone").grid(row=2, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(auth_frame, textvariable=self.phone_var, width=30).grid(row=2, column=1, sticky="ew", padx=4, pady=4)

        self.connect_btn = ttk.Button(auth_frame, text="Connect / Send Code", command=self.connect_clicked)
        self.connect_btn.grid(row=0, column=2, rowspan=1, padx=8, pady=4, sticky="ew")

        ttk.Label(auth_frame, text="Code").grid(row=3, column=0, sticky="w", padx=4, pady=4)
        self.code_entry = ttk.Entry(auth_frame, textvariable=self.code_var, width=30)
        self.code_entry.grid(row=3, column=1, sticky="ew", padx=4, pady=4)

        self.verify_code_btn = ttk.Button(auth_frame, text="Verify Code", command=self.verify_code_clicked)
        self.verify_code_btn.grid(row=3, column=2, padx=8, pady=4, sticky="ew")

        ttk.Label(auth_frame, text="2FA Password").grid(row=4, column=0, sticky="w", padx=4, pady=4)
        self.password_entry = ttk.Entry(auth_frame, textvariable=self.password_var, width=30, show="*")
        self.password_entry.grid(row=4, column=1, sticky="ew", padx=4, pady=4)

        self.verify_password_btn = ttk.Button(auth_frame, text="Verify Password", command=self.verify_password_clicked)
        self.verify_password_btn.grid(row=4, column=2, padx=8, pady=4, sticky="ew")

        auth_frame.columnconfigure(1, weight=1)

        chats_frame = ttk.LabelFrame(main, text="Chats", padding=12)
        chats_frame.pack(fill="x", pady=6)

        self.load_chats_btn = ttk.Button(chats_frame, text="Load Top 20 Chats", command=self.load_chats_clicked)
        self.load_chats_btn.grid(row=0, column=0, padx=4, pady=4, sticky="w")

        ttk.Label(chats_frame, text="Chat A").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        self.chat_a_combo = ttk.Combobox(
            chats_frame,
            textvariable=self.chat_a_var,
            state="readonly",
            width=90
        )
        self.chat_a_combo.grid(row=1, column=1, sticky="ew", padx=4, pady=4)

        ttk.Label(chats_frame, text="Chat B").grid(row=2, column=0, sticky="w", padx=4, pady=4)
        self.chat_b_combo = ttk.Combobox(
            chats_frame,
            textvariable=self.chat_b_var,
            state="readonly",
            width=90
        )
        self.chat_b_combo.grid(row=2, column=1, sticky="ew", padx=4, pady=4)

        chats_frame.columnconfigure(1, weight=1)

        control_frame = ttk.LabelFrame(main, text="Bridge Control", padding=12)
        control_frame.pack(fill="x", pady=6)

        self.start_btn = ttk.Button(control_frame, text="Start Bridge", command=self.start_bridge_clicked)
        self.start_btn.pack(side="left", padx=4)

        self.stop_btn = ttk.Button(control_frame, text="Stop Bridge", command=self.stop_bridge_clicked)
        self.stop_btn.pack(side="left", padx=4)

        log_frame = ttk.LabelFrame(main, text="Logs", padding=12)
        log_frame.pack(fill="both", expand=True, pady=6)

        self.log_text = tk.Text(log_frame, height=20, wrap="word")
        self.log_text.pack(fill="both", expand=True)

    def _load_saved_credentials(self):
        try:
            with open(CREDENTIALS_FILE, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f.readlines()]
            if len(lines) >= 3:
                self.api_id_var.set(lines[0])
                self.api_hash_var.set(lines[1])
                self.phone_var.set(lines[2])
                self.thread_safe_log("Loaded saved credentials.")
        except FileNotFoundError:
            self.thread_safe_log("No credentials.txt found yet.")

    def save_credentials(self):
        with open(CREDENTIALS_FILE, "w", encoding="utf-8") as f:
            f.write(self.api_id_var.get().strip() + "\n")
            f.write(self.api_hash_var.get().strip() + "\n")
            f.write(self.phone_var.get().strip() + "\n")

    def thread_safe_log(self, text: str):
        self.root.after(0, lambda: self._append_log(text))

    def _append_log(self, text: str):
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")

    def connect_clicked(self):
        api_id = self.api_id_var.get().strip()
        api_hash = self.api_hash_var.get().strip()
        phone = self.phone_var.get().strip()

        if not api_id or not api_hash or not phone:
            messagebox.showerror("Error", "API ID, API Hash, and Phone are required.")
            return

        self.save_credentials()
        self.thread_safe_log("Connecting...")

        def on_success(result):
            status = result.get("status")
            if status == "authorized":
                self.thread_safe_log("Authorized successfully.")
                self.load_chats_clicked()
            elif status == "code_sent":
                self.thread_safe_log("Code sent. Enter it in the Code field.")

        def on_error(e):
            self.thread_safe_log(f"Connect error: {e}")
            messagebox.showerror("Connect Error", str(e))

        self.backend.run_async_task(
            self.backend.connect_and_request_code(api_id, api_hash, phone),
            on_success=on_success,
            on_error=on_error,
        )

    def verify_code_clicked(self):
        code = self.code_var.get().strip()
        if not code:
            messagebox.showerror("Error", "Please enter the login code.")
            return

        self.thread_safe_log("Verifying code...")

        def on_success(result):
            status = result.get("status")
            if status == "authorized":
                self.thread_safe_log("Authorized successfully.")
                self.load_chats_clicked()
            elif status == "password_required":
                self.thread_safe_log("Please enter your 2FA password.")

        def on_error(e):
            self.thread_safe_log(f"Verify code error: {e}")
            messagebox.showerror("Verify Code Error", str(e))

        self.backend.run_async_task(
            self.backend.verify_code(code),
            on_success=on_success,
            on_error=on_error,
        )

    def verify_password_clicked(self):
        password = self.password_var.get().strip()
        if not password:
            messagebox.showerror("Error", "Please enter the 2FA password.")
            return

        self.thread_safe_log("Verifying password...")

        def on_success(result):
            status = result.get("status")
            if status == "authorized":
                self.thread_safe_log("Authorized successfully.")
                self.load_chats_clicked()

        def on_error(e):
            self.thread_safe_log(f"Verify password error: {e}")
            messagebox.showerror("Verify Password Error", str(e))

        self.backend.run_async_task(
            self.backend.verify_password(password),
            on_success=on_success,
            on_error=on_error,
        )

    def load_chats_clicked(self):
        self.thread_safe_log("Loading top 20 chats...")

        def on_success(items):
            self.dialog_labels = items
            self.chat_a_combo["values"] = items
            self.chat_b_combo["values"] = items

            if items:
                self.chat_a_combo.current(0)
                if len(items) > 1:
                    self.chat_b_combo.current(1)

            self.thread_safe_log("Chats loaded into dropdowns.")

        def on_error(e):
            self.thread_safe_log(f"Load chats error: {e}")
            messagebox.showerror("Load Chats Error", str(e))

        self.backend.run_async_task(
            self.backend.load_top_dialogs_once(),
            on_success=on_success,
            on_error=on_error,
        )

    def start_bridge_clicked(self):
        index_a = self.chat_a_combo.current()
        index_b = self.chat_b_combo.current()

        if index_a < 0 or index_b < 0:
            messagebox.showerror("Error", "Please choose two chats.")
            return

        if index_a == index_b:
            messagebox.showerror("Error", "Please choose two different chats.")
            return

        self.thread_safe_log("Starting bridge...")

        def on_success(_):
            self.thread_safe_log("Bridge is running.")

        def on_error(e):
            self.thread_safe_log(f"Start bridge error: {e}")
            messagebox.showerror("Start Bridge Error", str(e))

        self.backend.run_async_task(
            self.backend.start_bridge(index_a, index_b),
            on_success=on_success,
            on_error=on_error,
        )

    def stop_bridge_clicked(self):
        self.thread_safe_log("Stopping bridge...")

        def on_success(_):
            self.thread_safe_log("Bridge stopped.")

        def on_error(e):
            self.thread_safe_log(f"Stop bridge error: {e}")
            messagebox.showerror("Stop Bridge Error", str(e))

        self.backend.run_async_task(
            self.backend.stop_bridge(),
            on_success=on_success,
            on_error=on_error,
        )

    def on_close(self):
        def closer():
            future = asyncio.run_coroutine_threadsafe(self.backend.shutdown(), self.backend.loop)
            try:
                future.result(timeout=5)
            except Exception:
                pass
            self.backend.loop.call_soon_threadsafe(self.backend.loop.stop)

        threading.Thread(target=closer, daemon=True).start()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = App(root)
    root.mainloop()


if __name__ == "__main__":
    main()